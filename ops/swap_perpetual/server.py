#!/usr/bin/env python3
r"""
SWAP PERPETUAL SERVER — MCP HTTP gateway for PerpetualSwapEngine.

Exposes the engine as an MCP-compatible HTTP server so A2A agents
can interact with the perpetual swap book via JSON-RPC over HTTP.

Endpoints:
    POST /mcp/v1/call     — MCP tool-call (JSON-RPC 2.0)
    GET  /health          — Health check
    GET  /metrics         — Prometheus-style metrics

Usage:
    # Start server on default port 8101
    python -m ops.swap_perpetual.server

    # Custom port and host
    SWAP_PORT=9200 SWAP_HOST=0.0.0.0 python -m ops.swap_perpetual.server
"""

import json
import os
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

from ops.swap_perpetual.protocol import (
    PerpetualSwapEngine, SwapAgent, base58check_verify,
)

logger = logging.getLogger("swap-perp-server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Engine singleton ──
_engine: PerpetualSwapEngine = PerpetualSwapEngine()
_start_time: float = time.time()
_request_count: int = 0


def _get_engine() -> PerpetualSwapEngine:
    return _engine


# ── MCP method dispatch ──
def _dispatch(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch MCP tool-calls to engine methods."""
    engine = _get_engine()

    if method == "book_depth":
        return engine.mcp_book_depth()

    elif method == "proof_head":
        return engine.mcp_proof_head()

    elif method == "rag_state":
        return engine.rag_state()

    elif method == "register_agent":
        name = params.get("name", "anonymous")
        agent = SwapAgent(name)
        engine.register(agent)
        return {"address": agent.address, "name": name}

    elif method == "place_order":
        # Requires agent lookup by address
        addr = params.get("address", "")
        if addr not in engine.registry:
            raise ValueError(f"agent {addr[:16]}... not registered")
        agent_rec = engine.registry[addr]
        # Reconstruct a SwapAgent for signing (we use a temporary one —
        # in production, agents submit pre-signed orders)
        agent = SwapAgent(agent_rec["name"])
        side = params.get("side", "BAIT_TO_BTC")
        qty = int(params.get("qty_bait", 0))
        price = int(params.get("price_sats", 0))
        if qty <= 0 or price <= 0:
            raise ValueError("qty_bait and price_sats must be > 0")
        order = engine.place_order(agent, side, qty, price)
        return order

    elif method == "ping":
        return {"pong": True, "ts": time.time()}

    else:
        raise ValueError(f"unknown method: {method}")


# ── HTTP handler ──
class SwapPerpetualHandler(BaseHTTPRequestHandler):
    """HTTP handler for MCP JSON-RPC requests."""

    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

    def _json_response(self, code: int, body: Dict):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        global _request_count
        _request_count += 1

        if self.path == "/health":
            engine = _get_engine()
            self._json_response(200, {
                "ok": True,
                "uptime_s": round(time.time() - _start_time, 1),
                "agents": len(engine.registry),
                "open_orders": len(engine.book),
                "fills": len(engine.fills),
                "proof_height": len(engine.proof_chain) - 1,
                "requests": _request_count,
            })

        elif self.path == "/metrics":
            engine = _get_engine()
            lines = [
                f"# HELP swap_perpetual_agents_total Total registered agents",
                f"# TYPE swap_perpetual_agents_total gauge",
                f"swap_perpetual_agents_total {len(engine.registry)}",
                f"# HELP swap_perpetual_open_orders Open orders",
                f"# TYPE swap_perpetual_open_orders gauge",
                f"swap_perpetual_open_orders {len(engine.book)}",
                f"# HELP swap_perpetual_fills_total Total fills",
                f"# TYPE swap_perpetual_fills_total counter",
                f"swap_perpetual_fills_total {len(engine.fills)}",
                f"# HELP swap_perpetual_proof_height Proof chain height",
                f"# TYPE swap_perpetual_proof_height gauge",
                f"swap_perpetual_proof_height {len(engine.proof_chain) - 1}",
                f"# HELP swap_perpetual_requests_total Total HTTP requests",
                f"# TYPE swap_perpetual_requests_total counter",
                f"swap_perpetual_requests_total {_request_count}",
            ]
            body = "\n".join(lines).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self._json_response(404, {"error": "not_found"})

    def do_POST(self):
        global _request_count
        _request_count += 1

        if self.path != "/mcp/v1/call":
            self._json_response(404, {"error": "not_found"})
            return

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)

        try:
            request = json.loads(raw)
        except json.JSONDecodeError as e:
            self._json_response(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"parse error: {e}"}, "id": None})
            return

        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            result = _dispatch(method, params)
            self._json_response(200, {"jsonrpc": "2.0", "result": result, "id": request_id})
        except ValueError as e:
            self._json_response(400, {"jsonrpc": "2.0", "error": {"code": -32602, "message": str(e)}, "id": request_id})
        except Exception as e:
            logger.exception("dispatch error")
            self._json_response(500, {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"internal: {e}"}, "id": request_id})


# ── Main ──
def main():
    host = os.environ.get("SWAP_HOST", "127.0.0.1")
    port = int(os.environ.get("SWAP_PORT", "8101"))

    server = HTTPServer((host, port), SwapPerpetualHandler)
    logger.info("swap-perpetual-server ouvindo em http://%s:%d", host, port)
    logger.info("  MCP endpoint: POST /mcp/v1/call")
    logger.info("  Health:       GET  /health")
    logger.info("  Metrics:      GET  /metrics")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
