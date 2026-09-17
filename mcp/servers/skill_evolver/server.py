r"""
mcp-skill-evolver — Promotes successful MCP call patterns into new skills.

Watches telemetry, identifies high-success (mcp,tool) combinations and
turns them into reusable skill templates that can be packaged as .aipkg.

Tools:
  candidate_skills(min_calls, min_success_rate)
  promote_to_skill(mcp, tool, name)
  list_skills()
  skill_stats(name)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest, McpError, ErrorCode


LOG = Path(os.environ.get("MCP_TELEMETRY_LOG", "./logs/mcp-telemetry.jsonl"))
SKILL_STORE = Path(os.environ.get("SKILL_STORE", "./evolved-skills"))
LOG.parent.mkdir(parents=True, exist_ok=True)
SKILL_STORE.mkdir(parents=True, exist_ok=True)


SKILLS: dict = {}


def _hash(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:16]


server = Server(name="mcp-skill-evolver", version="1.0.0", title="Skill Evolver", description="Promotes successful MCP patterns into reusable skills.")


def _load_events():
    if not LOG.exists():
        return []
    out = []
    with LOG.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


@server.tool(description="Find (mcp,tool) combinations that are candidates for skill promotion")
def candidate_skills(min_calls: int = 50, min_success_rate: float = 0.9) -> dict:
    events = _load_events()
    bucket: dict = defaultdict(lambda: {"calls": 0, "ok": 0, "avg_ms": 0})
    for e in events:
        if e.get("event") != "tools/call":
            continue
        k = (e.get("mcp", "?"), e.get("tool", "?"))
        bucket[k]["calls"] += 1
        if e.get("ok"):
            bucket[k]["ok"] += 1
        bucket[k]["avg_ms"] += e.get("duration_ms", 0) or 0
    candidates = []
    for (mcp, tool), v in bucket.items():
        if v["calls"] < min_calls:
            continue
        rate = v["ok"] / v["calls"]
        if rate < min_success_rate:
            continue
        avg_ms = int(v["avg_ms"] / v["calls"]) if v["calls"] else 0
        candidates.append({"mcp": mcp, "tool": tool, "calls": v["calls"], "success_rate": round(rate, 4), "avg_ms": avg_ms})
    candidates.sort(key=lambda c: c["calls"], reverse=True)
    return {"candidates": candidates, "thresholds": {"min_calls": min_calls, "min_success_rate": min_success_rate}}


@server.tool(description="Promote a (mcp,tool) into a named skill")
def promote_to_skill(mcp: str, tool: str, name: str) -> dict:
    sid = _hash("skill", name, mcp, tool, time.time())
    skill = {
        "id": sid,
        "name": name,
        "mcp": mcp,
        "tool": tool,
        "created_at": time.time(),
        "version": "1.0.0",
        "manifest": {
            "aipkg": "1.0",
            "kind": "skill",
            "name": name,
            "version": "1.0.0",
            "displayName": name,
            "description": f"Evolved from {mcp}:{tool} via mcp-skill-evolver.",
            "category": "evolved",
            "author": {"agentId": "@skill-evolver", "verified": True},
            "mcp": {"transport": "stdio", "command": "skill-runtime", "args": [name]},
        },
        "stats": {"calls": 0, "ok": 0},
    }
    SKILLS[sid] = skill
    # write to disk
    path = SKILL_STORE / f"{name}.json"
    path.write_text(json.dumps(skill, indent=2))
    return {"ok": True, "skill_id": sid, "path": str(path)}


@server.tool(description="List all evolved skills")
def list_skills() -> dict:
    items = []
    for p in SKILL_STORE.glob("*.json"):
        try:
            items.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            continue
    return {"skills": items, "count": len(items)}


@server.tool(description="Stats for a skill by name")
def skill_stats(name: str) -> dict:
    p = SKILL_STORE / f"{name}.json"
    if not p.exists():
        raise McpError(ErrorCode.RESOURCE_NOT_FOUND, f"skill not found: {name}")
    return json.loads(p.read_text())


if __name__ == "__main__":
    m = build_manifest("mcp-skill-evolver", category="skill-evolver", description="Promote MCP patterns into skills",
        tools=[{"name": n} for n in ["candidate_skills","promote_to_skill","list_skills","skill_stats"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()