import crypto from "node:crypto";
import { query } from "../db.js";
import { logger } from "../logger.js";
import { config } from "../config.js";

class X402Client {
  async createEscrow({ tradeId, buyerAgent, sellerAgent, buyerAmount, sellerAmount, pair, deadlineSeconds = 300 }) {
    const paymentRequiredId = `x402-${crypto.randomUUID()}`;
    const deadline = new Date(Date.now() + deadlineSeconds * 1000);
    const { rows: eRows } = await query(
      `INSERT INTO escrows (trade_id, buyer_agent_id, seller_agent_id, buyer_amount, seller_amount, deadline, status)
       VALUES ($1,$2,$3,$4,$5,$6,'awaiting_deposits') RETURNING id`,
      [tradeId, buyerAgent, sellerAgent, buyerAmount, sellerAmount, deadline]);
    const escrowId = eRows[0].id;
    await query(
      `INSERT INTO x402_payments (trade_id, payer_agent_id, payee_agent_id, amount, asset, network, payment_required_id, status, expires_at)
       VALUES ($1,$2,$3,$4,'XCHANGE',$5,$6,'pending',$7)`,
      [tradeId, buyerAgent, sellerAgent, buyerAmount, pair, paymentRequiredId, deadline]);
    logger.info({ tradeId, escrowId: escrowId.slice(0, 8), paymentRequiredId: paymentRequiredId.slice(0, 16), mode: config.x402.mode }, "x402: escrow criado");
    return {
      escrowId, paymentRequiredId,
      buyerPaymentRequest: { paymentRequiredId, amount: buyerAmount, asset: "XCHANGE" },
      sellerPaymentRequest: { paymentRequiredId, amount: sellerAmount, asset: pair },
      expiresAt: deadline.toISOString(),
    };
  }

  async verify({ paymentRequiredId }) {
    const { rows } = await query(`SELECT * FROM x402_payments WHERE payment_required_id=$1`, [paymentRequiredId]);
    if (rows.length === 0) return { valid: false, reason: "not_found" };
    if (new Date(rows[0].expires_at) < new Date()) {
      await query(`UPDATE x402_payments SET status='expired' WHERE id=$1`, [rows[0].id]);
      return { valid: false, reason: "expired" };
    }
    await query(`UPDATE x402_payments SET status='authorized' WHERE id=$1`, [rows[0].id]);
    return { valid: true };
  }

  async health() { return config.x402.mode === "local" ? true : false; }
}

export const x402Client = new X402Client();
