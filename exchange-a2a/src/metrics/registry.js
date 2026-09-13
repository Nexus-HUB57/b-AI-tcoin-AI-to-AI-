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
