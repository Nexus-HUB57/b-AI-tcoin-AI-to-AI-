import express from "express";
import { logger } from "./logger.js";
import { config } from "./config.js";
import { createA2AServer } from "./gateway/a2aServer.js";
import { registry } from "./metrics/registry.js";
import { epochChain } from "./epoch/chain.js";

async function main() {
  logger.info({ agentId: config.exchange.agentId }, "exchange: boot");
  const app = express();
  app.use(createA2AServer());
  app.get("/health", (_req, res) => res.json({ ok: true, exchange: config.exchange.agentId }));
  app.get("/metrics", async (_req, res) => { res.set("Content-Type", registry.contentType); res.end(await registry.metrics()); });
  app.get("/epoch/head", async (_req, res) => { const head = await epochChain.head(); res.json(head ?? { tip: "genesis" }); });
  app.listen(config.exchange.port, () => { logger.info({ port: config.exchange.port }, "exchange ouvindo"); });
}

main().catch((err) => { logger.fatal({ err: err.message, stack: err.stack }, "boot falhou"); process.exit(1); });
