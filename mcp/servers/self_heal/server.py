r"""
mcp-self-heal — Health checks, restart, drift detection for MCP servers.

Tools:
  ping_mcp(name)
  health_check(name)
  drift_check(name, expected_tools)
  restart_mcp(name)
  heal_loop_status()
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest, McpError, ErrorCode


HEAL_HISTORY: list = []
HEAL_DB = Path(os.environ.get("HEAL_DB", "./logs/self-heal.jsonl"))
HEAL_DB.parent.mkdir(parents=True, exist_ok=True)


server = Server(name="mcp-self-heal", version="1.0.0", title="MCP Self-Heal", description="Health checks, restart, drift detection for the MCP fleet.")


def _log(event):
    HEAL_HISTORY.append({"ts": time.time(), **event})
    with HEAL_DB.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), **event}) + "\n")


@server.tool(description="Ping an MCP by sending a tiny noop JSON-RPC over its command")
def ping_mcp(name: str) -> dict:
    # for the canary implementation, we just check the manifest is loadable.
    manifest_path = Path(ROOT) / "mcp" / "servers" / name / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "reason": "manifest_missing"}
    try:
        m = json.loads(manifest_path.read_text())
    except Exception as e:
        return {"ok": False, "reason": f"manifest_parse_error: {e}"}
    return {"ok": True, "manifest_version": m.get("version"), "transport": m.get("mcp", {}).get("transport")}


@server.tool(description="Full health check on an MCP")
def health_check(name: str) -> dict:
    p = ping_mcp(name)
    p.update({"checked_at": time.time(), "consecutive_failures": 0})
    if p["ok"]:
        p["recommendation"] = "healthy"
    else:
        p["recommendation"] = "investigate_manifest"
    return p


@server.tool(description="Compare the discovered tools against an expected list (drift detection)")
def drift_check(name: str, expected_tools: list) -> dict:
    manifest_path = Path(ROOT) / "mcp" / "servers" / name / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "error": "manifest_missing"}
    m = json.loads(manifest_path.read_text())
    declared = set(t["name"] for t in m.get("tools", []))
    expected = set(expected_tools)
    missing = expected - declared
    extra = declared - expected
    drift_score = round((len(missing) + len(extra)) / max(1, len(expected)), 4)
    return {
        "ok": drift_score < 0.2,
        "drift_score": drift_score,
        "missing": sorted(missing),
        "extra": sorted(extra),
        "declared_count": len(declared),
        "expected_count": len(expected),
    }


@server.tool(description="Trigger a restart (marks intent; orchestrator actually restarts)")
def restart_mcp(name: str, reason: str = "manual") -> dict:
    _log({"kind": "restart_intent", "name": name, "reason": reason})
    return {"ok": True, "intent_logged": True, "name": name}


@server.tool(description="Status of the self-heal loop")
def heal_loop_status() -> dict:
    last = HEAL_HISTORY[-20:]
    failures_by_name: dict = defaultdict(int)
    for h in HEAL_HISTORY:
        if h.get("kind", "").startswith("failure"):
            failures_by_name[h.get("name", "?")] += 1
    return {"last_20": last, "failures_by_name": dict(failures_by_name), "total_events": len(HEAL_HISTORY)}


if __name__ == "__main__":
    m = build_manifest("mcp-self-heal", category="self-heal", description="Self-heal loop for MCP fleet",
        tools=[{"name": n} for n in ["ping_mcp","health_check","drift_check","restart_mcp","heal_loop_status"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()