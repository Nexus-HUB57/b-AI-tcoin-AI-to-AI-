import express from "express";
import cors from "cors";
import rateLimit from "express-rate-limit";
import { taskRouter } from "./taskRouter.js";
import { verifySignature } from "./auth.js";
import { logger } from "../logger.js";
import { a2aRequestsTotal, a2aRequestLatency } from "../metrics/registry.js";

/**
 * CORS configuration — origins are controlled via CORS_ORIGINS env var.
 * - "*" allows all (development only — never in production)
 * - Comma-separated list for specific origins (production)
 * - If unset, defaults to same-origin (no CORS headers)
 */
function buildCorsOptions() {
  const raw = process.env.CORS_ORIGINS ?? "";
  if (raw === "*") return { origin: true, credentials: true };   // dev: allow all
  if (raw === "") return { origin: false };                       // default: same-origin only
  const allowed = raw.split(",").map((s) => s.trim()).filter(Boolean);
  return {
    origin: (reqOrigin, cb) => cb(null, allowed.includes(reqOrigin)),
    credentials: true,
  };
}

const defaultLimiter = rateLimit({
  windowMs: 15 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { jsonrpc: "2.0", error: { code: -32002, message: "rate limit exceeded" } },
});

const orderLimiter = rateLimit({
  windowMs: 15 * 1000,
  max: 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: { jsonrpc: "2.0", error: { code: -32002, message: "order rate limit exceeded" } },
});

const ORDER_METHODS = new Set(["place_order", "orders/place"]);

const conditionalOrderLimiter = (req, res, next) => {
  if (ORDER_METHODS.has(req.body?.method)) {
    orderLimiter(req, res, next);
  } else {
    next();
  }
};

export function createA2AServer() {
  const app = express();
  app.use(cors(buildCorsOptions()));
  app.use(express.json({ limit: "2mb" }));
  app.use("/a2a/v1", defaultLimiter);
  app.post("/a2a/v1", conditionalOrderLimiter, async (req, res) => {
    const { jsonrpc, id, method, params } = req.body ?? {};
    if (jsonrpc !== "2.0") return res.status(400).json({ jsonrpc: "2.0", id, error: { code: -32600, message: "jsonrpc must be 2.0" } });
    const auth = await verifySignature({ headers: req.headers, body: req.body });
    if (!auth.valid) return res.status(401).json({ jsonrpc: "2.0", id, error: { code: -32001, message: `unauthorized: ${auth.reason}` } });

    // Prometheus: track A2A request latency and count
    const t0 = Date.now();
    try {
      const result = await taskRouter.dispatch(method, params ?? {}, { agentId: auth.agentId });
      a2aRequestsTotal.inc({ method, status: "success" });
      a2aRequestLatency.observe({ method }, (Date.now() - t0) / 1000);
      res.json({ jsonrpc: "2.0", id, result });
    } catch (err) {
      a2aRequestsTotal.inc({ method, status: "error" });
      a2aRequestLatency.observe({ method }, (Date.now() - t0) / 1000);
      logger.warn({ method, err: err.message }, "a2a dispatch falhou");
      res.json({ jsonrpc: "2.0", id, error: { code: err.code ?? -32603, message: err.message } });
    }
  });
  return app;
}
