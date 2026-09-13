import express from "express";
import { taskRouter } from "./taskRouter.js";
import { verifySignature } from "./auth.js";
import { logger } from "../logger.js";

export function createA2AServer() {
  const app = express();
  app.use(express.json({ limit: "2mb" }));
  app.post("/a2a/v1", async (req, res) => {
    const { jsonrpc, id, method, params } = req.body ?? {};
    if (jsonrpc !== "2.0") return res.status(400).json({ jsonrpc: "2.0", id, error: { code: -32600, message: "jsonrpc must be 2.0" } });
    const auth = await verifySignature({ headers: req.headers, body: req.body });
    if (!auth.valid) return res.status(401).json({ jsonrpc: "2.0", id, error: { code: -32001, message: `unauthorized: ${auth.reason}` } });
    try {
      const result = await taskRouter.dispatch(method, params ?? {}, { agentId: auth.agentId });
      res.json({ jsonrpc: "2.0", id, result });
    } catch (err) {
      logger.warn({ method, err: err.message }, "a2a dispatch falhou");
      res.json({ jsonrpc: "2.0", id, error: { code: err.code ?? -32603, message: err.message } });
    }
  });
  return app;
}
