import crypto from "node:crypto";
import * as ecc from "tiny-secp256k1";
import { query } from "../db.js";
import { authAttempts } from "../metrics/registry.js";

const REPLAY_WINDOW_MS = 30_000;

export async function verifySignature({ headers, body }) {
  const agentId = headers["x-agent-id"];
  const ts = parseInt(headers["x-timestamp"] ?? "0", 10);
  const sigHex = headers["x-signature"];
  if (!agentId || !ts || !sigHex) { authAttempts.inc({ result: "missing_headers" }); return { valid: false, reason: "headers ausentes" }; }
  if (Math.abs(Date.now() - ts) > REPLAY_WINDOW_MS) { authAttempts.inc({ result: "stale_timestamp" }); return { valid: false, reason: "timestamp fora da janela" }; }
  const { rows } = await query(`SELECT owner_address FROM a2a_agents WHERE agent_id=$1 AND status='active'`, [agentId]);
  if (rows.length === 0) { authAttempts.inc({ result: "unknown_agent" }); return { valid: false, reason: "agente não registrado" }; }
  const pk = Buffer.from(rows[0].owner_address, "hex");
  if (pk.length !== 33) { authAttempts.inc({ result: "invalid_pubkey" }); return { valid: false, reason: "pubkey inválida" }; }
  const msg = JSON.stringify({ body, ts });
  const msgHash = crypto.createHash("sha256").update(msg).digest();
  const sig = Buffer.from(sigHex, "hex");
  const compact = sig.length === 65 ? sig.subarray(0, 64) : sig;
  try {
    if (!ecc.verify(msgHash, pk, compact)) { authAttempts.inc({ result: "bad_signature" }); return { valid: false, reason: "assinatura inválida" }; }
  } catch (err) { authAttempts.inc({ result: "verify_error" }); return { valid: false, reason: `verify erro: ${err.message}` }; }
  authAttempts.inc({ result: "success" });
  return { valid: true, agentId };
}
