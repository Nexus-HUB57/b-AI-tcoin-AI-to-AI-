import crypto from "node:crypto";
import * as ecc from "tiny-secp256k1";
import { query, pool } from "../src/db.js";
import { agentCard } from "../src/identity/agentCard.js";
import { orderBook } from "../src/matching/orderBook.js";
import { settlement } from "../src/matching/settlement.js";
import { reputation } from "../src/reputation/engine.js";
import { taskRouter } from "../src/gateway/taskRouter.js";
import { epochChain } from "../src/epoch/chain.js";
import { logger } from "../src/logger.js";

const results = [];
function check(name, ok, detail = {}) { results.push({ name, ok, detail }); console.log(`${ok ? "✅" : "❌"} [${name}] ${JSON.stringify(detail).slice(0, 140)}`); }

async function main() {
  console.log("SMOKE TEST — Exchange A2A\n");
  await query(`DELETE FROM x402_payments WHERE trade_id IN (SELECT id FROM trades WHERE pair LIKE 'SMOKE/%')`).catch(() => {});
  await query(`DELETE FROM escrows WHERE trade_id IN (SELECT id FROM trades WHERE pair LIKE 'SMOKE/%')`).catch(() => {});
  await query(`DELETE FROM trades WHERE pair LIKE 'SMOKE/%'`).catch(() => {});
  await query(`DELETE FROM orders WHERE pair LIKE 'SMOKE/%'`).catch(() => {});
  await query(`DELETE FROM a2a_tasks WHERE agent_id LIKE 'smoke-%'`).catch(() => {});
  await query(`DELETE FROM agent_card_versions WHERE agent_id LIKE 'smoke-%'`).catch(() => {});
  await query(`DELETE FROM reputation_events WHERE agent_id LIKE 'smoke-%'`).catch(() => {});
  await query(`DELETE FROM agent_reputation WHERE agent_id LIKE 'smoke-%'`).catch(() => {});
  await query(`DELETE FROM a2a_agents WHERE agent_id LIKE 'smoke-%'`).catch(() => {});

  const agents = [];
  for (let i = 0; i < 3; i++) {
    const agentId = `smoke-${i}-${crypto.randomBytes(3).toString("hex")}`;
    const pk = crypto.randomBytes(32);
    const pubkey = Buffer.from(ecc.pointFromScalar(pk, true)).toString("hex");
    await query(`INSERT INTO a2a_agents (agent_id, erc721_contract, chain_id, owner_address, status) VALUES ($1, '0x0000000000000000000000000000000000000000', 31337, $2, 'active')`, [agentId, pubkey]);
    await query(`INSERT INTO agent_reputation (agent_id, trust_tier, trades_settled) VALUES ($1, 'silver', 100)`, [agentId]);
    agents.push({ agentId, pk, pubkey });
  }
  check("setup.agents", agents.length === 3, { count: agents.length });
  const { rows: persisted } = await query(`SELECT COUNT(*)::int AS n FROM a2a_agents WHERE agent_id LIKE 'smoke-%'`);
  check("setup.persisted", persisted[0].n === 3, persisted[0]);

  for (const a of agents) {
    const card = { name: `Smoke Agent ${a.agentId.slice(-4)}`, description: "Smoke test agent", url: `https://smoke.local/${a.agentId}`, version: "1.0.0", capabilities: { streaming: true, pushNotifications: false }, defaultInputModes: ["text"], defaultOutputModes: ["text"], skills: [{ id: "trade", name: "Trading", description: "Places orders" }], authentication: { schemes: ["ecdsa"] } };
    await agentCard.publish({ agentId: a.agentId, card });
  }
  check("cards.published", true, { count: agents.length });
  let rejected = false;
  try { await agentCard.publish({ agentId: agents[0].agentId, card: { name: "" } }); } catch { rejected = true; }
  check("cards.rejects-invalid", rejected);

  const buy = await orderBook.place({ agentId: agents[0].agentId, pair: "SMOKE/BTC", side: "buy", type: "limit", price: 100000, quantity: 0.5 });
  check("direct.buy-placed", buy.status === "open", { orderId: buy.orderId.slice(0, 8), status: buy.status });
  const sell = await orderBook.place({ agentId: agents[1].agentId, pair: "SMOKE/BTC", side: "sell", type: "limit", price: 100000, quantity: 0.3 });
  check("direct.sell-matched", sell.matches.length === 1, { matches: sell.matches.length, status: sell.status });

  const ctx = { agentId: agents[2].agentId };
  const r1 = await taskRouter.dispatch("message/send", { message: { intent: "place_order", payload: { pair: "SMOKE/ETH", side: "buy", type: "limit", price: 5000, quantity: 2 } }, contextId: "smoke-ctx" }, ctx);
  check("rpc.place-order", r1.state === "completed" && r1.result.orderId, { taskId: r1.taskId.slice(0, 12), orderId: r1.result.orderId.slice(0, 8) });
  const r2 = await taskRouter.dispatch("message/send", { message: { intent: "get_depth", payload: { pair: "SMOKE/ETH" } } }, ctx);
  check("rpc.get-depth", r2.result.bids.length === 1, { bids: r2.result.bids.length });
  const r3 = await taskRouter.dispatch("tasks/get", { taskId: r1.taskId }, ctx);
  check("rpc.tasks-get", r3.state === "completed");
  const r4 = await taskRouter.dispatch("message/send", { message: { intent: "cancel_order", payload: { orderId: r1.result.orderId } } }, ctx);
  check("rpc.cancel", r4.result.status === "cancelled");

  const { rows: trades } = await query(`SELECT * FROM trades WHERE pair='SMOKE/BTC' ORDER BY matched_at DESC LIMIT 1`);
  check("matching.trade-created", trades.length === 1, { tradeId: trades[0]?.id?.slice(0, 8), price: trades[0]?.price, qty: trades[0]?.quantity, status: trades[0]?.status });
  const depth = await orderBook.depth("SMOKE/BTC");
  check("matching.depth", Array.isArray(depth.bids) && Array.isArray(depth.asks), { bids: depth.bids.length, asks: depth.asks.length });
  const ticker = await orderBook.ticker("SMOKE/BTC");
  check("matching.ticker", ticker.pair === "SMOKE/BTC", { lastPrice: ticker.lastPrice });

  const trade = trades[0];
  const { rows: escrowRows } = await query(`SELECT * FROM escrows WHERE trade_id=$1`, [trade.id]);
  check("settlement.escrow-created", escrowRows.length === 1, { escrowId: escrowRows[0]?.id?.slice(0, 8), status: escrowRows[0]?.status });
  const rel = await settlement.confirmRelease({ tradeId: trade.id, buyerDepositTx: "0xbuyer-deposit-smoke", sellerDepositTx: "0xseller-deposit-smoke" });
  check("settlement.released", rel.released === true, rel);
  const { rows: settled } = await query(`SELECT status FROM trades WHERE id=$1`, [trade.id]);
  check("settlement.trade-settled", settled[0].status === "settled", { status: settled[0].status });
  const rep = await reputation.get(trade.buyer_agent_id);
  check("settlement.reputation-updated", rep.trades_settled >= 1, { settled: rep.trades_settled, tier: rep.trust_tier });

  const m = await orderBook.place({ agentId: agents[0].agentId, pair: "SMOKE/XYZ", side: "buy", type: "market", quantity: 1 });
  check("edge.market-no-liquidity", m.status === "cancelled", { status: m.status });
  let qtyRejected = false;
  try { await orderBook.place({ agentId: agents[0].agentId, pair: "SMOKE/BTC", side: "buy", type: "limit", price: 100, quantity: -1 }); } catch { qtyRejected = true; }
  check("edge.negative-qty", qtyRejected);
  let agentRejected = false;
  try { await orderBook.place({ agentId: "nonexistent-agent-xyz", pair: "SMOKE/BTC", side: "buy", type: "limit", price: 100, quantity: 1 }); } catch { agentRejected = true; }
  check("edge.unknown-agent", agentRejected);
  let cancelFailed = false;
  try { await orderBook.cancel({ agentId: agents[0].agentId, orderId: crypto.randomUUID() }); } catch { cancelFailed = true; }
  check("edge.cancel-nonexistent", cancelFailed);

  await epochChain.append({ payload: { kind: "smoke-test", at: new Date().toISOString() } });
  const ev = await epochChain.verify();
  check("epoch.verify", ev.valid, { valid: ev.valid, length: ev.length, head: ev.head?.slice(0, 16) });

  const passed = results.filter((r) => r.ok).length;
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\nRESULTADO: passed ${passed} / failed ${failed}`);
  await pool.end();
  process.exit(failed > 0 ? 1 : 0);
}

main().catch(async (err) => { logger.fatal({ err: err.message, stack: err.stack }, "smoke falhou"); await pool.end().catch(() => {}); process.exit(1); });
