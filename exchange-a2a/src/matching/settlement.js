import { query, withTx } from "../db.js";
import { logger } from "../logger.js";
import { x402Client } from "../settlement/x402Client.js";
import { reputation } from "../reputation/engine.js";
import { tradesTotal } from "../metrics/registry.js";

/**
 * Minimum on-chain confirmations required before marking a trade as settled.
 * Configurable via MIN_SETTLEMENT_CONFIRMATIONS env var (default: 3).
 * This mitigates chain reorganizations that could invalidate deposit txs.
 */
const MIN_CONFIRMATIONS = parseInt(process.env.MIN_SETTLEMENT_CONFIRMATIONS ?? "3", 10);

class Settlement {
  async settleTrade(trade) {
    await query(`UPDATE trades SET status='settling' WHERE id=$1`, [trade.id]);
    try {
      const escrow = await x402Client.createEscrow({
        tradeId: trade.id, buyerAgent: trade.buyer_agent_id, sellerAgent: trade.seller_agent_id,
        buyerAmount: Number(trade.quantity) * Number(trade.price), sellerAmount: Number(trade.quantity),
        pair: trade.pair, deadlineSeconds: 300,
      });
      await query(`UPDATE trades SET settlement_id=$2 WHERE id=$1`, [trade.id, escrow.escrowId]);
      return escrow;
    } catch (err) {
      await query(`UPDATE trades SET status='failed' WHERE id=$1`, [trade.id]);
      tradesTotal.inc({ pair: trade.pair, status: "failed" });
      await reputation.record({ agentId: trade.buyer_agent_id, event: "dispute_lost", detail: { tradeId: trade.id, reason: err.message } });
      throw err;
    }
  }

  /**
   * Confirm release of escrowed funds.
   *
   * IMPORTANT: Before marking as 'settled', we verify that BOTH deposit
   * transactions have at least MIN_CONFIRMATIONS on-chain confirmations.
   * This is checked via the confirmations column in the escrows table,
   * which should be updated by the bridge/chain monitor when new blocks arrive.
   *
   * If confirmations are insufficient, the escrow stays in 'both_deposited'
   * state and the caller should retry after more blocks are mined.
   */
  async confirmRelease({ tradeId, buyerDepositTx, sellerDepositTx, buyerConfirmations, sellerConfirmations }) {
    await withTx(async (c) => {
      await c.query(
        `UPDATE escrows SET
           buyer_deposit_tx = COALESCE($2, buyer_deposit_tx),
           seller_deposit_tx = COALESCE($3, seller_deposit_tx),
           buyer_confirmations = COALESCE($4, buyer_confirmations),
           seller_confirmations = COALESCE($5, seller_confirmations),
           status = CASE WHEN COALESCE($2, buyer_deposit_tx) IS NOT NULL AND COALESCE($3, seller_deposit_tx) IS NOT NULL THEN 'both_deposited' ELSE status END
         WHERE trade_id=$1`,
        [tradeId, buyerDepositTx, sellerDepositTx, buyerConfirmations ?? null, sellerConfirmations ?? null]);
    });
    const { rows } = await query(`SELECT * FROM escrows WHERE trade_id=$1`, [tradeId]);
    const escrow = rows[0];
    if (!escrow || escrow.status !== "both_deposited") return { released: false, status: escrow?.status ?? "not_found" };

    // Confirmation gate: require MIN_CONFIRMATIONS on both deposit txs
    const buyerConfs = escrow.buyer_confirmations ?? 0;
    const sellerConfs = escrow.seller_confirmations ?? 0;
    if (buyerConfs < MIN_CONFIRMATIONS || sellerConfs < MIN_CONFIRMATIONS) {
      logger.info({ tradeId, buyerConfs, sellerConfs, required: MIN_CONFIRMATIONS }, "settlement: aguardando confirmações");
      return { released: false, status: "awaiting_confirmations", buyerConfs, sellerConfs, required: MIN_CONFIRMATIONS };
    }

    await query(`UPDATE escrows SET status='released', released_at=now() WHERE id=$1`, [escrow.id]);
    await query(`UPDATE trades SET status='settled', settled_at=now() WHERE id=$1`, [tradeId]);
    const { rows: tradeRows } = await query(`SELECT * FROM trades WHERE id=$1`, [tradeId]);
    const trade = tradeRows[0];
    const volume = Number(trade.quantity) * Number(trade.price);
    for (const agentId of [trade.buyer_agent_id, trade.seller_agent_id]) {
      await reputation.record({ agentId, event: "trade_settled", detail: { tradeId, pair: trade.pair, volume: String(volume) } });
    }
    tradesTotal.inc({ pair: trade.pair, status: "settled" });
    logger.info({ tradeId, pair: trade.pair, buyerConfs, sellerConfs }, "settlement: liberada (confirmada)");
    return { released: true, status: "released" };
  }
}

export const settlement = new Settlement();
