import client from "prom-client";

export const registry = new client.Registry();
client.collectDefaultMetrics({ register: registry, prefix: "exchange_" });

export const ordersTotal = new client.Counter({
  name: "exchange_orders_total", help: "Orders placed",
  labelNames: ["pair", "side", "status"], registers: [registry],
});
export const tradesTotal = new client.Counter({
  name: "exchange_trades_total", help: "Trades matched",
  labelNames: ["pair", "status"], registers: [registry],
});
export const orderLatency = new client.Histogram({
  name: "exchange_order_latency_seconds", help: "Latency placing orders",
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5], registers: [registry],
});
export const epochHeight = new client.Gauge({
  name: "exchange_epoch_height", help: "Current epoch-chain height", registers: [registry],
});
export const openOrders = new client.Gauge({
  name: "exchange_open_orders", help: "Open orders",
  labelNames: ["pair", "side"], registers: [registry],
});
// ── Gateway metrics ──
export const a2aRequestsTotal = new client.Counter({
  name: "exchange_a2a_requests_total", help: "A2A JSON-RPC requests",
  labelNames: ["method", "status"], registers: [registry],
});
export const a2aRequestLatency = new client.Histogram({
  name: "exchange_a2a_request_latency_seconds", help: "A2A request latency",
  labelNames: ["method"], buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1], registers: [registry],
});
export const wsConnections = new client.Gauge({
  name: "exchange_ws_connections", help: "Active WebSocket connections", registers: [registry],
});
// ── Auth metrics ──
export const authAttempts = new client.Counter({
  name: "exchange_auth_attempts_total", help: "Authentication attempts",
  labelNames: ["result"], registers: [registry],
});
// ── Reputation metrics ──
export const reputationUpdates = new client.Counter({
  name: "exchange_reputation_updates_total", help: "Reputation events processed",
  labelNames: ["event"], registers: [registry],
});
// ── Settlement (x402) metrics ──
export const escrowCreated = new client.Counter({
  name: "exchange_escrow_created_total", help: "Escrows created",
  labelNames: ["pair"], registers: [registry],
});
export const escrowSettled = new client.Counter({
  name: "exchange_escrow_settled_total", help: "Escrows settled",
  labelNames: ["pair", "status"], registers: [registry],
});
