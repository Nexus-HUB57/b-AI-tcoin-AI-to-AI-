r"""
mcp-rag-upgrader — Auto-improves the RAG knowledge packs.

Reads pending signals from RAG_INBOX, clusters failures, and proposes
upgrades (additions to docs, new embeddings, schema fixes) that an operator
or a downstream agent can approve.

Tools:
  pending_proposals()
  cluster_failures(window_minutes)
  propose_upgrade(target_kb, signal_ids)
  apply_proposal(proposal_id)
  knowledge_base_stats()
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


RAG_INBOX = Path(os.environ.get("RAG_INBOX", "./logs/rag-inbox.jsonl"))
KB_ROOT = Path(os.environ.get("KB_ROOT", "./knowledge"))
RAG_INBOX.parent.mkdir(parents=True, exist_ok=True)
KB_ROOT.mkdir(parents=True, exist_ok=True)

PROPOSALS: dict = {}


def _hash(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:16]


server = Server(name="mcp-rag-upgrader", version="1.0.0", title="RAG Upgrader", description="Auto-improves RAG knowledge packs from telemetry signals.")


@server.tool(description="List pending upgrade proposals")
def pending_proposals() -> dict:
    return {"proposals": [p for p in PROPOSALS.values() if not p["applied"]], "count": len(PROPOSALS)}


@server.tool(description="Cluster failure signals in the last N minutes by (mcp,tool)")
def cluster_failures(window_minutes: int = 60) -> dict:
    cutoff = time.time() - window_minutes * 60
    clusters: dict = defaultdict(list)
    if not RAG_INBOX.exists():
        return {"clusters": [], "window_minutes": window_minutes}
    with RAG_INBOX.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            if s.get("ts", 0) < cutoff:
                continue
            if s.get("signal") not in ("failure", "low_rating", "missing_capability"):
                continue
            ctx = s.get("context", {})
            k = (ctx.get("mcp", "?"), ctx.get("tool", "?"), s["signal"])
            clusters[k].append(s)
    rows = []
    for (mcp, tool, signal), sigs in clusters.items():
        rows.append({"mcp": mcp, "tool": tool, "signal": signal, "count": len(sigs), "weight": sum(s.get("weight", 1) for s in sigs)})
    rows.sort(key=lambda r: r["weight"], reverse=True)
    return {"clusters": rows, "window_minutes": window_minutes}


@server.tool(description="Generate an upgrade proposal for a knowledge base")
def propose_upgrade(target_kb: str, signal_ids: list) -> dict:
    pid = _hash("prop", target_kb, signal_ids, time.time())
    target_path = KB_ROOT / target_kb
    proposal = {
        "id": pid,
        "target_kb": target_kb,
        "target_path": str(target_path),
        "signal_ids": signal_ids,
        "created_at": time.time(),
        "applied": False,
        "diffs": [
            {
                "kind": "add_doc",
                "reason": f"Auto-generated from {len(signal_ids)} failure signal(s) to address recurring failure mode.",
                "stub": f"# Auto-upgrade for {target_kb}\n\nGenerated at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n\nBased on {len(signal_ids)} failure signals.\n",
            }
        ],
    }
    PROPOSALS[pid] = proposal
    return {"ok": True, "proposal_id": pid, "diffs": len(proposal["diffs"])}


@server.tool(description="Apply a proposal (writes the stub doc into the KB)")
def apply_proposal(proposal_id: str) -> dict:
    p = PROPOSALS.get(proposal_id)
    if not p:
        raise McpError(ErrorCode.RESOURCE_NOT_FOUND, f"proposal not found: {proposal_id}")
    if p["applied"]:
        return {"ok": False, "error": "already_applied"}
    target = Path(p["target_path"])
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for d in p["diffs"]:
        if d["kind"] == "add_doc":
            f = target / f"auto-upgrade-{int(time.time())}.md"
            f.write_text(d["stub"])
            written.append(str(f))
    p["applied"] = True
    p["applied_at"] = time.time()
    return {"ok": True, "written": written}


@server.tool(description="Stats for the local knowledge bases")
def knowledge_base_stats() -> dict:
    stats = []
    for p in KB_ROOT.iterdir():
        if not p.is_dir():
            continue
        files = list(p.glob("**/*.md")) + list(p.glob("**/*.txt"))
        total_size = sum(f.stat().st_size for f in files)
        stats.append({"kb": p.name, "files": len(files), "size_bytes": total_size})
    return {"kbs": stats, "root": str(KB_ROOT)}


if __name__ == "__main__":
    m = build_manifest("mcp-rag-upgrader", category="rag-upgrader", description="Auto-RAG upgrader via MCP",
        tools=[{"name": n} for n in ["pending_proposals","cluster_failures","propose_upgrade","apply_proposal","knowledge_base_stats"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()