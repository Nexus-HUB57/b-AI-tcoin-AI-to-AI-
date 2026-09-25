import crypto from "node:crypto";
import { query, withTx } from "../db.js";
import { logger } from "../logger.js";
import { reputation } from "../reputation/engine.js";
import { matchingEngine } from "./matchingEngine.js";
import { ordersTotal, orderLatency } from "../metrics/registry.js";

const TIER_LIMITS = { new: 100, bronze: 1000, silver: 10000, gold: 100000, platinum: 1000000 };

/**
 * Trading pair whitelist — loaded from TRADING_PAIRS env var.
 * Format: "BAIT/USDC,BAIT/ETH" (comma-separated).
 * If empty, all pairs are accepted (backward compatible).
 */
const TRADING_PAIRS = new Set(
  (process.env.TRADING_PAIRS ?? "").split(",").map((s) => s.trim()).filter(Boolean)
);

function validatePair(pair) {
  if (!pair || typeof pair !== "string") throw new Error("pair obrigatório");
  if (TRADING_PAIRS.size > 0 && !TRADING_PAIRS.has(pair)) {
    throw new Error(`pair não permitido: ${pair}. Pares válidos: ${[...TRADING_PAIRS].join(", ")}`);
  }
}

/**
 * Replay nonce table — ensures each (agent_id, nonce) pair is used at most once.
 * The nonce is derived from clientOrderId if provided, or from a hash of the order params.
 * Migration adds: CREATE TABLE IF NOT EXISTS order_nonces (agent_id TEXT, nonce TEXT, created_at TIMESTAMPTZ DEFAULT now(), PRIMARY KEY (agent_id, nonce));
 */
async function checkAndRecordNonce(agentId, clientOrderId, params) {
  const nonce = clientOrderId ?? crypto.createHash("sha256")
    .update(`${agentId}:${params.pair}:${params.side}:${params.type}:${params.price}:${params.quantity}:${Math.floor(Date.now() / 30_000)}`)
    .digest("hex").slice(0, 32);

  try {
    await query(
      `INSERT INTO order_nonces (agent_id, nonce) VALUES ($1, $2) ON CONFLICT DO NOTHING`,
      [agentId, nonce]
    );
  } catch (err) {
    // If table doesn't exist yet (pre-migration), skip silently
    if (!err.message.includes("order_nonces")) throw err;
    logger.warn("order_nonces table not found — skipping replay check (run migration)");
  }
  return nonce;
}

class OrderBook {
  async place({ agentId, pair, side, type = "limit", price = null, quantity,
    clientOrderId = null, timeInForce = "GTC", a2aTaskId = null }) {
    const t0 = Date.now();

    // Validate inputs
    validatePair(pair);
    if (!["buy", "sell"].includes(side)) throw new Error("side inválido");
    if (!["limit", "market", "ioc", "fok"].includes(type)) throw new Error("type inválido");
    if (type === "limit" && (price == null || Number(price) <= 0)) throw new Error("limit requer price > 0");
    if (!(Number(quantity) > 0)) throw new Error("quantity deve ser > 0");

    // Anti-replay: check nonce
    await checkAndRecordNonce(agentId, clientOrderId, { pair, side, type, price, quantity });

    // Tier-based quantity limit
    const rep = await reputation.get(agentId);
    if (!rep) throw new Error("agente sem reputação registrada");
    const limit = TIER_LIMITS[rep.trust_tier] ?? 100;
    if (Number(quantity) > limit) throw new Error(`quantidade limitada a ${limit} para tier '${rep.trust_tier}'`);

    // Insert order and match atomically within a single transaction
    const orderId = crypto.randomUUID();
    const { order, matches } = await withTx(async (c) => {
      const { rows } = await c.query(
        `INSERT INTO orders (id, agent_id, pair, side, type, price, quantity, client_order_id, time_in_force, a2a_task_id, status)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'open') RETURNING *`,
        [orderId, agentId, pair, side, type, price ?? null, quantity, clientOrderId, timeInForce, a2aTaskId]
      );
      const insertedOrder = rows[0];

      // matchingEngine.match() now runs inside this same transaction (uses c from withTx)
      const matchResults = await matchingEngine.match(insertedOrder);

      // Update incoming order status after matching (within same tx)
      await c.query(
        `UPDATE orders SET status = CASE WHEN filled >= quantity THEN 'filled' WHEN filled > 0 THEN 'partial' ELSE status END, updated_at = now() WHERE id = $1`,
        [orderId]
      );

      return { order: insertedOrder, matches: matchResults };
    });

    // Post-transaction: handle IOC/FOK cancellation
    const { rows: final } = await query(`SELECT status, filled FROM orders WHERE id=$1`, [orderId]);

    // IOC: cancel any unfilled remainder
    if (type === "ioc" && Number(final[0].filled) < Number(order.quantity)) {
      await query(`UPDATE orders SET status='cancelled', updated_at=now() WHERE id=$1`, [orderId]);
      final[0].status = "cancelled";
    }

    // FOK: if not fully filled, rollback all fills and cancel
    if (type === "fok" && Number(final[0].filled) < Number(order.quantity)) {
      // Reverse fills on resting orders and delete trades
      for (const trade of matches) {
        const restingId = trade.buy_order_id === orderId ? trade.sell_order_id : trade.buy_order_id;
        await withTx(async (c) => {
          await c.query(`UPDATE orders SET filled = filled - $2, status = CASE WHEN filled - $2 >= quantity THEN 'filled' WHEN filled - $2 > 0 THEN 'partial' ELSE 'open' END, updated_at=now() WHERE id=$1`, [restingId, trade.quantity]);
          await c.query(`DELETE FROM trades WHERE id=$1`, [trade.id]);
        });
      }
      // Reset incoming order and cancel
      await query(`UPDATE orders SET filled=0, status='cancelled', updated_at=now() WHERE id=$1`, [orderId]);
      final[0].status = "cancelled";
      final[0].filled = 0;
    }

    ordersTotal.inc({ pair, side, status: final[0].status });
    orderLatency.observe((Date.now() - t0) / 1000);
    logger.info({ orderId: orderId.slice(0, 8), agentId, pair, side, type, matches: matches.length, status: final[0].status }, "order: colocada");
    return { orderId, status: final[0].status, filled: Number(final[0].filled), matches };
  }

  async cancel({ agentId, orderId }) {
    const { rowCount } = await query(
      `UPDATE orders SET status='cancelled', updated_at=now() WHERE id=$1 AND agent_id=$2 AND status IN ('open','partial')`,
      [orderId, agentId]
    );
    if (rowCount === 0) throw new Error("ordem não cancelável");
    return { orderId, status: "cancelled" };
  }

  async depth(pair, { levels = 20 } = {}) {
    validatePair(pair);
    const { rows: bids } = await query(
      `SELECT price, SUM(remaining)::numeric AS size, COUNT(*)::int AS orders
       FROM orders WHERE pair=$1 AND side='buy' AND status IN ('open','partial') GROUP BY price ORDER BY price DESC LIMIT $2`, [pair, levels]);
    const { rows: asks } = await query(
      `SELECT price, SUM(remaining)::numeric AS size, COUNT(*)::int AS orders
       FROM orders WHERE pair=$1 AND side='sell' AND status IN ('open','partial') GROUP BY price ORDER BY price ASC LIMIT $2`, [pair, levels]);
    return { pair, bids, asks };
  }

  async ticker(pair) {
    validatePair(pair);
    const { rows: last } = await query(
      `SELECT price, quantity, matched_at FROM trades WHERE pair=$1 ORDER BY matched_at DESC LIMIT 1`, [pair]);
    const { rows: best } = await query(
      `SELECT (SELECT MIN(price) FROM orders WHERE pair=$1 AND side='sell' AND status IN ('open','partial')) AS ask,
              (SELECT MAX(price) FROM orders WHERE pair=$1 AND side='buy' AND status IN ('open','partial')) AS bid`, [pair]);
    return { pair, lastPrice: last[0]?.price ?? null, lastQty: last[0]?.quantity ?? null,
             lastTradeAt: last[0]?.matched_at ?? null, ask: best[0]?.ask ?? null, bid: best[0]?.bid ?? null };
  }

  async recentTrades(pair, limit = 50) {
    validatePair(pair);
    const { rows } = await query(
      `SELECT id, price, quantity, matched_at FROM trades WHERE pair=$1 ORDER BY matched_at DESC LIMIT $2`, [pair, limit]);
    return rows;
  }
}

export const orderBook = new OrderBook();
