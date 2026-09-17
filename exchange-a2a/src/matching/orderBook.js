import crypto from "node:crypto";
import { query, withTx } from "../db.js";
import { logger } from "../logger.js";
import { reputation } from "../reputation/engine.js";
import { matchingEngine } from "./matchingEngine.js";
import { ordersTotal, orderLatency } from "../metrics/registry.js";

const TIER_LIMITS = { new: 100, bronze: 1000, silver: 10000, gold: 100000, platinum: 1000000 };

class OrderBook {
  async place({ agentId, pair, side, type = "limit", price = null, quantity,
    clientOrderId = null, timeInForce = "GTC", a2aTaskId = null }) {
    const t0 = Date.now();
    if (!["buy", "sell"].includes(side)) throw new Error("side inválido");
    if (!["limit", "market", "ioc", "fok"].includes(type)) throw new Error("type inválido");
    if (type === "limit" && (price == null || Number(price) <= 0)) throw new Error("limit requer price > 0");
    if (!(Number(quantity) > 0)) throw new Error("quantity deve ser > 0");
    const rep = await reputation.get(agentId);
    if (!rep) throw new Error("agente sem reputação registrada");
    const limit = TIER_LIMITS[rep.trust_tier] ?? 100;
    if (Number(quantity) > limit) throw new Error(`quantidade limitada a ${limit} para tier '${rep.trust_tier}'`);
    const orderId = crypto.randomUUID();
    const { rows } = await withTx(async (c) => {
      return c.query(
        `INSERT INTO orders (id, agent_id, pair, side, type, price, quantity, client_order_id, time_in_force, a2a_task_id, status)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'open') RETURNING *`,
        [orderId, agentId, pair, side, type, price ?? null, quantity, clientOrderId, timeInForce, a2aTaskId]
      );
    });
    const order = rows[0];
    const matches = await matchingEngine.match(order);
    await query(
      `UPDATE orders SET status = CASE WHEN filled >= quantity THEN 'filled' WHEN filled > 0 THEN 'partial' ELSE status END, updated_at = now() WHERE id = $1`,
      [orderId]
    );
    const { rows: final } = await query(`SELECT status, filled FROM orders WHERE id=$1`, [orderId]);
    if ((type === "ioc" || type === "fok") && matches.length === 0) {
      await query(`UPDATE orders SET status='cancelled' WHERE id=$1`, [orderId]);
      final[0].status = "cancelled";
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
    const { rows: bids } = await query(
      `SELECT price, SUM(remaining)::numeric AS size, COUNT(*)::int AS orders
       FROM orders WHERE pair=$1 AND side='buy' AND status IN ('open','partial') GROUP BY price ORDER BY price DESC LIMIT $2`, [pair, levels]);
    const { rows: asks } = await query(
      `SELECT price, SUM(remaining)::numeric AS size, COUNT(*)::int AS orders
       FROM orders WHERE pair=$1 AND side='sell' AND status IN ('open','partial') GROUP BY price ORDER BY price ASC LIMIT $2`, [pair, levels]);
    return { pair, bids, asks };
  }

  async ticker(pair) {
    const { rows: last } = await query(
      `SELECT price, quantity, matched_at FROM trades WHERE pair=$1 ORDER BY matched_at DESC LIMIT 1`, [pair]);
    const { rows: best } = await query(
      `SELECT (SELECT MIN(price) FROM orders WHERE pair=$1 AND side='sell' AND status IN ('open','partial')) AS ask,
              (SELECT MAX(price) FROM orders WHERE pair=$1 AND side='buy' AND status IN ('open','partial')) AS bid`, [pair]);
    return { pair, lastPrice: last[0]?.price ?? null, lastQty: last[0]?.quantity ?? null,
             lastTradeAt: last[0]?.matched_at ?? null, ask: best[0]?.ask ?? null, bid: best[0]?.bid ?? null };
  }

  async recentTrades(pair, limit = 50) {
    const { rows } = await query(
      `SELECT id, price, quantity, matched_at FROM trades WHERE pair=$1 ORDER BY matched_at DESC LIMIT $2`, [pair, limit]);
    return rows;
  }
}

export const orderBook = new OrderBook();
