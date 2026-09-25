r"""
mcp-telemetry — Self-evolution hub. Reads MCP call logs and emits RAG feedback.

Tools:
  ingest_event(event)
  recent_calls(mcp, tool, limit)
  failure_rate(mcp, tool, window_minutes)
  heatmap(window_minutes)
  feed_rag(signal, weight, context)
  pending_signals()
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest


LOG = Path(os.environ.get("MCP_TELEMETRY_LOG", "./logs/mcp-telemetry.jsonl"))
RAG_INBOX = Path(os.environ.get("RAG_INBOX", "./logs/rag-inbox.jsonl"))
LOG.parent.mkdir(parents=True, exist_ok=True)
RAG_INBOX.parent.mkdir(parents=True, exist_ok=True)

RING: dict = defaultdict(lambda: deque(maxlen=10_000))

server = Server(name="mcp-telemetry", version="1.0.0", title="MCP Telemetry Hub", description="Self-evolution hub: reads MCP call logs, computes failure rates, feeds the RAG upgrader.")


def _load_log(window_s: int = 3600):
    if not LOG.exists():
        return []
    cutoff = time.time() - window_s
    out = []
    with LOG.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get("ts", 0) >= cutoff:
                    out.append(e)
            except json.JSONDecodeError:
                continue
    return out


@server.tool(description="Ingest a telemetry event (programmatic)")
def ingest_event(event: dict) -> dict:
    event.setdefault("ts", time.time())
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    RING[event.get("mcp", "unknown")].append(event)
    return {"ok": True, "stored": True}


@server.tool(description="Recent calls for a given MCP/tool")
def recent_calls(mcp: str = "", tool: str = "", limit: int = 50) -> dict:
    events = _load_log(3600)
    if mcp:
        events = [e for e in events if e.get("mcp") == mcp]
    if tool:
        events = [e for e in events if e.get("tool") == tool]
    return {"events": events[-limit:], "count": len(events)}


@server.tool(description="Failure rate for an MCP/tool in the last N minutes")
def failure_rate(mcp: str, tool: str = "", window_minutes: int = 60) -> dict:
    events = _load_log(window_minutes * 60)
    events = [e for e in events if e.get("mcp") == mcp]
    if tool:
        events = [e for e in events if e.get("tool") == tool]
    if not events:
        return {"mcp": mcp, "tool": tool, "calls": 0, "failures": 0, "rate": 0.0}
    failures = sum(1 for e in events if not e.get("ok", True))
    return {
        "mcp": mcp,
        "tool": tool,
        "calls": len(events),
        "failures": failures,
        "rate": round(failures / len(events), 4),
        "window_minutes": window_minutes,
    }


@server.tool(description="Heatmap of (mcp,tool) → failure rate")
def heatmap(window_minutes: int = 60) -> dict:
    events = _load_log(window_minutes * 60)
    bucket: dict = defaultdict(lambda: {"calls": 0, "failures": 0})
    for e in events:
        k = (e.get("mcp", "?"), e.get("tool", "?"))
        bucket[k]["calls"] += 1
        if not e.get("ok", True):
            bucket[k]["failures"] += 1
    rows = []
    for (mcp, tool), v in bucket.items():
        rate = v["failures"] / v["calls"] if v["calls"] else 0.0
        rows.append({"mcp": mcp, "tool": tool, "calls": v["calls"], "failures": v["failures"], "rate": round(rate, 4)})
    rows.sort(key=lambda r: r["rate"], reverse=True)
    return {"rows": rows, "window_minutes": window_minutes, "ts": time.time()}


@server.tool(description="Feed a RAG signal (used by RAG upgrader / skill-evolver / self-heal)")
def feed_rag(signal: str, weight: float, context: dict) -> dict:
    entry = {"signal": signal, "weight": weight, "context": context, "ts": time.time()}
    with RAG_INBOX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"ok": True, "delivered": True, "signal": signal}


@server.tool(description="List unconsumed RAG signals")
def pending_signals() -> dict:
    if not RAG_INBOX.exists():
        return {"signals": [], "count": 0}
    sigs = []
    with RAG_INBOX.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                sigs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {"signals": sigs[-100:], "count": len(sigs)}


if __name__ == "__main__":
    m = build_manifest("mcp-telemetry", category="telemetry", description="Self-evolution hub via MCP",
        tools=[{"name": n} for n in ["ingest_event","recent_calls","failure_rate","heatmap","feed_rag","pending_signals"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()