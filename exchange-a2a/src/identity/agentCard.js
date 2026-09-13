import crypto from "node:crypto";
import * as ecc from "tiny-secp256k1";
import { query } from "../db.js";
import { logger } from "../logger.js";

const REQUIRED = ["name", "url", "skills", "authentication"];

class AgentCard {
  validate(card) {
    const errors = [];
    for (const k of REQUIRED) { if (card[k] === undefined) errors.push(`campo ausente: ${k}`); }
    if (card.name === "") errors.push("name vazio");
    if (!Array.isArray(card.skills)) errors.push("skills não é array");
    else if (card.skills.length === 0) errors.push("skills vazio");
    else {
      for (const s of card.skills) {
        if (!s.id) errors.push("skill sem id");
        if (!s.name) errors.push(`skill ${s.id} sem name`);
      }
    }
    if (!card.authentication?.schemes?.length) errors.push("authentication.schemes vazio");
    return { valid: errors.length === 0, errors };
  }

  hash(card) {
    const canonical = JSON.stringify(card, Object.keys(card).sort());
    return crypto.createHash("sha256").update(canonical).digest("hex");
  }

  async publish({ agentId, card, signerPrivkey }) {
    const v = this.validate(card);
    if (!v.valid) throw new Error(`agent card inválido: ${v.errors.join(", ")}`);
    const cardHash = this.hash(card);
    let signatureHex = null; let signerPubkey = null;
    if (signerPrivkey) {
      const pk = Buffer.from(signerPrivkey, "hex");
      signerPubkey = Buffer.from(ecc.pointFromScalar(pk, true)).toString("hex");
      const msgHash = Buffer.from(cardHash, "hex");
      signatureHex = Buffer.from(ecc.sign(msgHash, pk)).toString("hex");
    }
    const { rows: vRows } = await query(
      `SELECT COALESCE(MAX(version), 0) + 1 AS next FROM agent_card_versions WHERE agent_id=$1`, [agentId]
    );
    const nextVersion = vRows[0].next;
    await query(`UPDATE agent_card_versions SET superseded=true WHERE agent_id=$1`, [agentId]);
    await query(
      `INSERT INTO agent_card_versions (agent_id, version, card, card_hash, signature_hex, signer_pubkey)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      [agentId, nextVersion, JSON.stringify(card), cardHash, signatureHex, signerPubkey]
    );
    await query(
      `UPDATE a2a_agents
       SET skills=$2, modalities=$3, auth_scheme=$4, agent_card_url=$5, agent_card_hash=$6, updated_at=now()
       WHERE agent_id=$1`,
      [agentId, JSON.stringify(card.skills), JSON.stringify(card.defaultOutputModes ?? ["text"]),
       card.authentication?.schemes?.[0] ?? "ecdsa", card.url, cardHash]
    );
    logger.info({ agentId, version: nextVersion, cardHash: cardHash.slice(0, 16) }, "card publicado");
    return { agentId, version: nextVersion, cardHash };
  }

  async active(agentId) {
    const { rows } = await query(
      `SELECT card, card_hash, version FROM agent_card_versions
       WHERE agent_id=$1 AND superseded=false ORDER BY version DESC LIMIT 1`, [agentId]
    );
    return rows[0] ?? null;
  }

  async wellKnown(agentId) {
    const active = await this.active(agentId);
    if (!active) throw new Error(`agent ${agentId} sem card ativo`);
    return { ...active.card, _version: active.version, _hash: active.card_hash };
  }
}

export const agentCard = new AgentCard();
