r"""
mcp-observability — Prometheus / Loki / OTEL bridge.

Tools:
  query_prom(query, time_range)
  query_loki(query, lines)
  list_metrics()
  alert_state(alert_name)
  create_alert(name, expr, severity)
  trace_search(service, min_duration_ms)
  service_health(service)
  otel_ingest(service, traces)
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


ALERTS: dict = {}


def _hash(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:16]


server = Server(name="mcp-observability", version="1.0.0", title="Observability Bridge", description="Prometheus / Loki / OpenTelemetry bridge for monitoring.")


@server.tool(description="Query Prometheus")
def query_prom(query: str, time_range: str = "5m") -> dict:
    h = hashlib.sha256(query.encode()).hexdigest()[:8]
    return {"ok": True, "query": query, "time_range": time_range, "result": {"metric": h, "values": [[int(time.time()), 42.0]]}}


@server.tool(description="Query Loki for logs")
def query_loki(query: str, lines: int = 100) -> dict:
    return {"ok": True, "query": query, "lines": lines, "entries": [{"ts": time.time(), "line": f"mock log entry for {query}"} for _ in range(min(lines, 5))]}


@server.tool(description="List common metrics")
def list_metrics() -> dict:
    return {"ok": True, "metrics": [
        "http_requests_total", "mcp_calls_total", "mcp_tool_duration_seconds",
        "rag_invocations_total", "agent_active_sessions", "memory_bytes",
    ]}


@server.tool(description="Get state of an alert")
def alert_state(alert_name: str) -> dict:
    return {"ok": True, "name": alert_name, "state": "ok", "since": time.time() - 3600}


@server.tool(description="Create an alert rule")
def create_alert(name: str, expr: str, severity: str = "warning") -> dict:
    aid = _hash("alert", name, time.time())
    ALERTS[aid] = {"id": aid, "name": name, "expr": expr, "severity": severity, "created_at": time.time()}
    return {"ok": True, "alert_id": aid}


@server.tool(description="Search OTEL traces")
def trace_search(service: str, min_duration_ms: int = 0) -> dict:
    traces = []
    for i in range(3):
        traces.append({"trace_id": _hash("trace", service, i), "service": service, "duration_ms": 100 + i * 50, "status": "ok"})
    return {"ok": True, "traces": [t for t in traces if t["duration_ms"] >= min_duration_ms]}


@server.tool(description="Aggregated health for a service")
def service_health(service: str) -> dict:
    return {"ok": True, "service": service, "status": "healthy", "uptime_s": 86400, "error_rate": 0.001}


@server.tool(description="Ingest OTEL traces")
def otel_ingest(service: str, traces: list) -> dict:
    return {"ok": True, "service": service, "ingested": len(traces), "ingest_id": _hash("ingest", service, time.time())}


if __name__ == "__main__":
    server.run()