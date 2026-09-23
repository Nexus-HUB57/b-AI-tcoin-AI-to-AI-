/**
 * onchainSettlement.js — A2A Settlement with on-chain broadcast via mempool.space
 *
 * Integrates the x402 payment flow with real Bitcoin transaction broadcast
 * through mempool.space/tx/push. This enables agent-to-agent payments
 * that settle on the Bitcoin mainnet.
 *
 * Flow:
 *   1. x402 escrow created (buyer + seller deposit)
 *   2. Matching engine confirms trade
 *   3. Settlement builds raw BTC tx (P2PKH)
 *   4. Signs with custody key
 *   5. Broadcasts via mempool.space/tx/push
 *   6. Monitors confirmations
 *   7. Releases escrow to seller
 */

import crypto from "node:crypto";
import { query } from "../db.js";
import { logger } from "../logger.js";
import { config } from "../config.js";

const MEMPOOL_API = process.env.MEMPOOL_API_URL || "https://mempool.space/api";
const REQUIRED_CONFS = parseInt(process.env.SETTLEMENT_REQUIRED_CONFIRMATIONS || "3", 10);
const POLL_INTERVAL_MS = 30_000; // 30s between confirmation checks
const MAX_POLL_ATTEMPTS = 120; // 1 hour max wait

class OnchainSettlement {
  /**
   * Broadcast a raw hex transaction to mempool.space
   * @param {string} rawHex - Raw transaction hex
   * @returns {Promise<{ok: boolean, txid: string|null, error?: string}>}
   */
  async broadcast(rawHex) {
    if (!rawHex || !/^[0-9a-fA-F]+$/.test(rawHex)) {
      return { ok: false, txid: null, error: "invalid hex" };
    }

    try {
      const resp = await fetch(`${MEMPOOL_API}/tx`, {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: rawHex,
        signal: AbortSignal.timeout(60_000),
      });
      const text = await resp.text();

      if (!resp.ok) {
        logger.warn({ status: resp.status, body: text.slice(0, 200) }, "onchain: broadcast rejected");
        return { ok: false, txid: null, error: `HTTP ${resp.status}: ${text.slice(0, 200)}` };
      }

      // Validate response is a 64-char txid
      const txid = text.trim();
      if (/^[0-9a-f]{64}$/.test(txid)) {
        logger.info({ txid: txid.slice(0, 16) }, "onchain: tx broadcast OK");
        return { ok: true, txid };
      }
      return { ok: false, txid, error: "response not a valid txid" };
    } catch (err) {
      logger.error({ err: err.message }, "onchain: broadcast failed");
      return { ok: false, txid: null, error: err.message };
    }
  }

  /**
   * Check transaction confirmation status on mempool.space
   * @param {string} txid - Transaction ID
   * @returns {Promise<{found: boolean, confirmed: boolean, confirmations: number}>}
   */
  async checkStatus(txid) {
    try {
      const resp = await fetch(`${MEMPOOL_API}/tx/${txid}`, {
        signal: AbortSignal.timeout(30_000),
      });
      if (resp.status === 404) {
        return { found: false, confirmed: false, confirmations: 0 };
      }
      const tx = await resp.json();
      return {
        found: true,
        confirmed: tx.status?.confirmed ?? false,
        confirmations: tx.status?.confirmations ?? 0,
        blockHeight: tx.status?.block_height ?? 0,
      };
    } catch (err) {
      return { found: false, confirmed: false, confirmations: 0, error: err.message };
    }
  }

  /**
   * Get recommended fee rates from mempool.space
   */
  async getFeeRates() {
    try {
      const resp = await fetch(`${MEMPOOL_API}/v1/fees/recommended`, {
        signal: AbortSignal.timeout(15_000),
      });
      return await resp.json();
    } catch {
      return { halfHourFee: 10, hourFee: 8, minimumFee: 5 };
    }
  }

  /**
   * Settle an A2A trade on-chain: broadcast the settlement tx and monitor confirmations
   * @param {string} tradeId - Trade ID in the exchange DB
   * @param {string} rawHex - Signed raw transaction hex
   * @returns {Promise<{ok: boolean, txid?: string, status?: string}>}
   */
  async settleTrade(tradeId, rawHex) {
    // 1. Broadcast
    const result = await this.broadcast(rawHex);
    if (!result.ok) {
      await query(
        `UPDATE trades SET settlement_status='broadcast_failed', settlement_error=$2, updated_at=now() WHERE trade_id=$1`,
        [tradeId, result.error]
      );
      return { ok: false, error: result.error };
    }

    // 2. Record txid
    await query(
      `UPDATE trades SET settlement_txid=$2, settlement_status='broadcast', updated_at=now() WHERE trade_id=$1`,
      [tradeId, result.txid]
    );
    logger.info({ tradeId, txid: result.txid }, "onchain: trade broadcast, monitoring confirmations");

    // 3. Monitor confirmations (async — returns immediately, settles in background)
    this._monitorConfirmation(tradeId, result.txid).catch((err) => {
      logger.error({ tradeId, err: err.message }, "onchain: monitoring failed");
    });

    return { ok: true, txid: result.txid, status: "broadcast" };
  }

  /**
   * Background: poll mempool until we reach required confirmations, then release escrow
   */
  async _monitorConfirmation(tradeId, txid) {
    for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));

      const status = await this.checkStatus(txid);
      if (!status.found) continue;

      if (status.confirmed && status.confirmations >= REQUIRED_CONFS) {
        // Release escrow
        await query(
          `UPDATE trades SET settlement_status='settled', confirmations=$2, settled_at=now(), updated_at=now() WHERE trade_id=$1`,
          [tradeId, status.confirmations]
        );
        await query(
          `UPDATE escrows SET status='released', released_at=now() WHERE trade_id=$1 AND status='awaiting_deposits'`,
          [tradeId]
        );
        logger.info({ tradeId, txid, confirmations: status.confirmations }, "onchain: SETTLED");
        return;
      }

      // Update confirmations count
      await query(
        `UPDATE trades SET confirmations=$2, updated_at=now() WHERE trade_id=$1`,
        [tradeId, status.confirmations ?? 0]
      );
    }

    // Timeout — mark as needing manual reconciliation
    await query(
      `UPDATE trades SET settlement_status='monitor_timeout', updated_at=now() WHERE trade_id=$1`,
      [tradeId]
    );
    logger.warn({ tradeId, txid }, "onchain: monitoring timed out — needs manual reconciliation");
  }

  async health() {
    try {
      const resp = await fetch(`${MEMPOOL_API}/v1/fees/recommended`, {
        signal: AbortSignal.timeout(10_000),
      });
      return resp.ok;
    } catch {
      return false;
    }
  }
}

export const onchainSettlement = new OnchainSettlement();
