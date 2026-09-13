import { query, withTx } from "../db.js";
import { logger } from "../logger.js";
import { settlement } from "./settlement.js";
import { tradesTotal } from "../metrics/registry.js";

class MatchingEngine {
  async match(newOrder) {
    const opposite = newOrder.side === "buy" ? "sell" : "buy";
    const priceFilter = newOrder.type === "market" ? "" : newOrder.side === "buy" ? "AND price <= $4" : "AND price >= $4";
    const params = [newOrder.pair, opposite, newOrder.id];
    if (newOrder.type !== "market") params.push(newOrder.price);
    const { rows: resting } = await query(
      `SELECT * FROM orders WHERE pair=$1 AND side=$2 AND status IN ('open','partial') AND id <> $3 ${priceFilter}
       ORDER BY price ${newOrder.side === "buy" ? "ASC" : "DESC"}, created_at ASC LIMIT 20`, params);
    if (resting.length === 0) return [];
    const matches = [];
    let remaining = Number(newOrder.quantity) - Number(newOrder.filled);
    for (const book of resting) {
      if (remaining <= 0) break;
      const bookRemaining = Number(book.remaining);
      const fillQty = Math.min(remaining, bookRemaining);
      const fillPrice = Number(book.price);
      const trade = await withTx(async (c) => {
        await c.query(`UPDATE orders SET filled = filled + $2, updated_at=now() WHERE id=$1`, [newOrder.id, fillQty]);
        await c.query(`UPDATE orders SET filled = filled + $2, updated_at=now() WHERE id=$1`, [book.id, fillQty]);
        const notional = fillQty * fillPrice;
        const buyerFee = newOrder.side === "buy" ? notional * 0.001 : notional * 0.0005;
        const sellerFee = newOrder.side === "sell" ? notional * 0.001 : notional * 0.0005;
        const buyerAgent = newOrder.side === "buy" ? newOrder.agent_id : book.agent_id;
        const sellerAgent = newOrder.side === "sell" ? newOrder.agent_id : book.agent_id;
        const buyOrderId = newOrder.side === "buy" ? newOrder.id : book.id;
        const sellOrderId = newOrder.side === "sell" ? newOrder.id : book.id;
        const { rows } = await c.query(
          `INSERT INTO trades (pair, buy_order_id, sell_order_id, buyer_agent_id, seller_agent_id, price, quantity, buyer_fee, seller_fee, status)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'matched') RETURNING *`,
          [newOrder.pair, buyOrderId, sellOrderId, buyerAgent, sellerAgent, fillPrice, fillQty, buyerFee, sellerFee]);
        await c.query(`UPDATE orders SET status = CASE WHEN filled >= quantity THEN 'filled' ELSE 'partial' END WHERE id IN ($1,$2)`, [newOrder.id, book.id]);
        return rows[0];
      });
      matches.push(trade);
      tradesTotal.inc({ pair: newOrder.pair, status: "matched" });
      remaining -= fillQty;
      settlement.settleTrade(trade).catch((err) => logger.error({ tradeId: trade.id, err: err.message }, "settlement falhou"));
    }
    logger.info({ orderId: newOrder.id.slice(0, 8), matches: matches.length }, "matching: concluído");
    return matches;
  }
}

export const matchingEngine = new MatchingEngine();
