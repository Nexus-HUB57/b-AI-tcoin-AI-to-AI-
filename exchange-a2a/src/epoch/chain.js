import crypto from "node:crypto";
import { query, withTx } from "../db.js";
import { logger } from "../logger.js";
import { config } from "../config.js";
import { EcdsaHybridSigner } from "./ecdsaHybrid.js";
import { epochHeight } from "../metrics/registry.js";

const NODE_ID = process.env.NODE_ID ?? `node-${process.pid}`;

class EpochChain {
  #signer = null;

  async #getSigner() {
    if (!this.#signer) {
      this.#signer = new EcdsaHybridSigner({
        localPrivkeyHex: config.epoch.localPrivkeyHex,
        kmsKeyId: config.epoch.kmsKeyId,
      });
      await this.#signer.init();
    }
    return this.#signer;
  }

  computeHash({ prevHash, payload, timestamp }) {
    const body = JSON.stringify(
      { prev_hash: prevHash ?? "genesis", payload, timestamp },
      ["prev_hash", "payload", "timestamp"]
    );
    return crypto.createHash("sha256").update(body).digest("hex");
  }

  async head() {
    const { rows } = await query(
      `SELECT epoch, epoch_hash, prev_hash, payload, created_at
       FROM epoch_chain WHERE status='canonical' ORDER BY epoch DESC LIMIT 1`
    );
    return rows[0] ?? null;
  }

  async append({ payload, epoch = null }) {
    const ep = epoch ?? Math.floor(Date.now() / 1000) + Math.floor(Math.random() * 1000);
    const signer = await this.#getSigner();
    const { rows: prevRows } = await query(
      `SELECT epoch_hash FROM epoch_chain WHERE status='canonical' ORDER BY epoch DESC LIMIT 1`
    );
    const prevHash = prevRows[0]?.epoch_hash ?? null;
    const timestamp = Date.now();
    const epochHash = this.computeHash({ prevHash, payload, timestamp });
    const sig = await signer.sign(epochHash);

    await withTx(async (c) => {
      await c.query(
        `INSERT INTO epoch_chain
           (epoch, prev_hash, epoch_hash, payload, signature_ecdsa, signer_pubkey, kms_key_id, node_id, status)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'canonical')
         ON CONFLICT (epoch) DO NOTHING`,
        [ep, prevHash, epochHash, JSON.stringify(payload), sig.signatureHex, sig.pubkeyHex, sig.kmsKeyId, NODE_ID]
      );
      await c.query(
        `UPDATE chain_state SET tip_height=$1, tip_hash=$2, updated_at=now() WHERE id=1`,
        [ep, epochHash]
      );
    });

    epochHeight.set(ep);
    logger.info({ epoch: ep, hash: epochHash.slice(0, 16), kind: payload.kind }, "epoch anexado");
    return { epoch: ep, epochHash, prevHash, signature: sig };
  }

  async verify({ limit = 5000 } = {}) {
    const { rows } = await query(
      `SELECT epoch, prev_hash, epoch_hash, payload, signature_ecdsa, signer_pubkey
       FROM epoch_chain WHERE status='canonical'
       ORDER BY epoch ASC LIMIT $1`, [limit]
    );
    const issues = [];
    let expectedPrev = null;
    const signer = await this.#getSigner();
    for (const r of rows) {
      if (expectedPrev !== null && r.prev_hash !== expectedPrev) {
        issues.push({ epoch: r.epoch, type: "prev_hash_mismatch" });
      }
      const okSig = signer.verify(r.epoch_hash, r.signature_ecdsa, r.signer_pubkey);
      if (!okSig) issues.push({ epoch: r.epoch, type: "signature_invalid" });
      expectedPrev = r.epoch_hash;
    }
    return { valid: issues.length === 0, length: rows.length,
             head: rows[rows.length - 1]?.epoch_hash ?? null, issues };
  }
}

export const epochChain = new EpochChain();
