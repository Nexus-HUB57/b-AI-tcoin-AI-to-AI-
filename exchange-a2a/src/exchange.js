import express from "express";
import http from "node:http";
import { logger } from "./logger.js";
import { config } from "./config.js";
import { createA2AServer } from "./gateway/a2aServer.js";
import { createWSGateway } from "./gateway/wsGateway.js";
import { verifySignature } from "./gateway/auth.js";
import { registry } from "./metrics/registry.js";
import { epochChain } from "./epoch/chain.js";

/**
 * Optional auth middleware for sensitive GET routes.
 * If ENABLE_READ_AUTH=true, requires the same x-agent-id/x-timestamp/x-signature headers.
 * Otherwise passes through (backward compatible).
 */
const requireAuth = process.env.ENABLE_READ_AUTH === "true"
  ? async (req, res, next) => {
      const auth = await verifySignature({ headers: req.headers, body: {} });
      if (!auth.valid) return res.status(401).json({ error: `unauthorized: ${auth.reason}` });
      req.agentId = auth.agentId;
      next();
    }
  : (_req, _res, next) => next();

async function main() {
  logger.info({ agentId: config.exchange.agentId }, "exchange: boot");
  const app = express();
  app.use(createA2AServer());

  // Public routes (no auth required)
  app.get("/health", (_req, res) => res.json({ ok: true, exchange: config.exchange.agentId }));

  // Protected routes (auth optional via ENABLE_READ_AUTH env)
  app.get("/metrics", requireAuth, async (_req, res) => { res.set("Content-Type", registry.contentType); res.end(await registry.metrics()); });
  app.get("/epoch/head", requireAuth, async (_req, res) => { const head = await epochChain.head(); res.json(head ?? { tip: "genesis" }); });

  // Create HTTP server (shared with WebSocket)
  const server = http.createServer(app);

  // Attach WebSocket gateway (auth enforced on every WS connection)
  createWSGateway(server);

  server.listen(config.exchange.port, () => { logger.info({ port: config.exchange.port }, "exchange ouvindo (HTTP + WS)"); });
}

main().catch((err) => { logger.fatal({ err: err.message, stack: err.stack }, "boot falhou"); process.exit(1); });
