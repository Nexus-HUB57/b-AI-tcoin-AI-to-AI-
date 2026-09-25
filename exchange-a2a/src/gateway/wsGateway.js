import { WebSocketServer } from "ws";
import { verifySignature } from "./auth.js";
import { logger } from "../logger.js";
import { taskRouter } from "./taskRouter.js";
import { wsConnections, a2aRequestsTotal, a2aRequestLatency } from "../metrics/registry.js";

/**
 * A2A WebSocket Gateway — real-time streaming with per-connection auth.
 *
 * Protocol:
 *   1. Client connects
 *   2. Client sends { type: "auth", agentId, timestamp, signature } within 5s
 *   3. Server verifies signature → responds { type: "auth_ok" } or closes with 4001
 *   4. After auth, client sends JSON-RPC messages: { jsonrpc: "2.0", id, method, params }
 *   5. Server dispatches and responds with JSON-RPC results
 *
 * Security:
 *   - Unauthenticated connections are closed after AUTH_TIMEOUT_MS
 *   - Auth is validated using the same verifySignature as HTTP
 *   - Per-connection rate limiting (max 50 msgs / 15s)
 */

const AUTH_TIMEOUT_MS = 5_000;
const MAX_MESSAGES_PER_WINDOW = 50;
const RATE_WINDOW_MS = 15_000;

export function createWSGateway(server) {
  const wss = new WebSocketServer({ server, path: "/a2a/v1/ws" });

  wss.on("connection", (ws, req) => {
    const ip = req.socket.remoteAddress;
    wsConnections.inc();
    let authenticated = false;
    let agentId = null;
    let authTimer = null;
    let msgCount = 0;
    let windowStart = Date.now();

    // Close unauthenticated connections after timeout
    authTimer = setTimeout(() => {
      if (!authenticated) {
        ws.close(4001, "auth timeout");
        logger.warn({ ip }, "ws: conexão fechada — auth timeout");
      }
    }, AUTH_TIMEOUT_MS);

    ws.on("message", async (raw) => {
      // Rate limit even before auth
      const now = Date.now();
      if (now - windowStart > RATE_WINDOW_MS) {
        msgCount = 0;
        windowStart = now;
      }
      if (++msgCount > MAX_MESSAGES_PER_WINDOW) {
        ws.close(4003, "rate limit exceeded");
        return;
      }

      let msg;
      try { msg = JSON.parse(raw); } catch { ws.close(4002, "invalid json"); return; }

      // Handle auth message
      if (msg.type === "auth") {
        if (authenticated) return; // already authed
        const auth = await verifySignature({
          headers: {
            "x-agent-id": msg.agentId,
            "x-timestamp": String(msg.timestamp),
            "x-signature": msg.signature,
          },
          body: {},
        });
        if (!auth.valid) {
          ws.close(4001, `auth failed: ${auth.reason}`);
          logger.warn({ ip, reason: auth.reason }, "ws: auth falhou");
          return;
        }
        authenticated = true;
        agentId = auth.agentId;
        clearTimeout(authTimer);
        ws.send(JSON.stringify({ type: "auth_ok", agentId }));
        logger.info({ agentId, ip }, "ws: autenticado");
        return;
      }

      // Reject non-auth messages before authentication
      if (!authenticated) {
        ws.close(4001, "not authenticated");
        return;
      }

      // Dispatch JSON-RPC
      const { jsonrpc, id, method, params } = msg;
      if (jsonrpc !== "2.0") {
        ws.send(JSON.stringify({ jsonrpc: "2.0", id, error: { code: -32600, message: "jsonrpc must be 2.0" } }));
        return;
      }
      const t0 = Date.now();
      try {
        const result = await taskRouter.dispatch(method, params ?? {}, { agentId });
        a2aRequestsTotal.inc({ method, status: "success" });
        a2aRequestLatency.observe({ method }, (Date.now() - t0) / 1000);
        ws.send(JSON.stringify({ jsonrpc: "2.0", id, result }));
      } catch (err) {
        a2aRequestsTotal.inc({ method, status: "error" });
        a2aRequestLatency.observe({ method }, (Date.now() - t0) / 1000);
        ws.send(JSON.stringify({ jsonrpc: "2.0", id, error: { code: err.code ?? -32603, message: err.message } }));
      }
    });

    ws.on("close", (code, reason) => {
      clearTimeout(authTimer);
      wsConnections.dec();
      if (authenticated) logger.info({ agentId, code }, "ws: desconectado");
    });

    ws.on("error", (err) => {
      logger.warn({ ip, err: err.message }, "ws: erro");
    });
  });

  logger.info("ws: gateway pronto em /a2a/v1/ws");
  return wss;
}
