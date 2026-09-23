r"""
mcp-agentic-awareness — Agent introspection: context, capabilities, gaps.

Tools:
  introspect(agent_id)
  context_window(agent_id, message)
  recommend_tools(agent_id, task_description)
  capability_gaps(agent_id, desired_capabilities)
  consciousness_score(agent_id)
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest
from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability


registry = AgentRegistry()
server = Server(name="mcp-agentic-awareness", version="1.0.0", title="Agentic Awareness", description="Agent introspection, context windows, capability gaps.")


@server.tool(description="Introspect an agent — capabilities, reputation, last activity")
def introspect(agent_id: str) -> dict:
    p = registry.get_agent(agent_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    return {
        "ok": True,
        "agent_id": p.agent_id,
        "capabilities": [c.value for c in p.capabilities],
        "reputation": p.reputation_score,
        "trust_level": p.trust_level,
        "stake_sats": p.stake_sats,
        "is_validator": p.is_validator,
        "registered_at": p.registered_at,
        "last_active": p.last_active,
        "age_days": round((time.time() - p.registered_at) / 86400, 4),
    }


@server.tool(description="Approximate context window stats for an agent given a message")
def context_window(agent_id: str, message: str, max_tokens: int = 4096) -> dict:
    approx_tokens = int(len(message.split()) * 1.3)
    return {
        "agent_id": agent_id,
        "message_chars": len(message),
        "approx_tokens": approx_tokens,
        "max_tokens": max_tokens,
        "fits": approx_tokens <= max_tokens,
        "utilization": round(approx_tokens / max_tokens, 4),
    }


@server.tool(description="Recommend tools (across MCPs) for a given task description")
def recommend_tools(agent_id: str, task_description: str) -> dict:
    p = registry.get_agent(agent_id)
    capabilities = [c.value for c in p.capabilities] if p else []
    recs = []
    if "price" in task_description.lower() or "market" in task_description.lower():
        recs.append({"mcp": "mcp-oracle", "tool": "get_price", "rationale": "Task references prices/markets."})
    if "swap" in task_description.lower() or "stake" in task_description.lower() or "lend" in task_description.lower():
        recs.append({"mcp": "mcp-defi", "tool": "quote_swap", "rationale": "DeFi primitives mentioned."})
    if "bridge" in task_description.lower() or "cross" in task_description.lower():
        recs.append({"mcp": "mcp-bridge", "tool": "initiate_bridge", "rationale": "Cross-chain operation."})
    if "agent" in task_description.lower() or "discover" in task_description.lower():
        recs.append({"mcp": "mcp-agent-registry", "tool": "discover_agents", "rationale": "Need to look up other agents."})
    if "buy" in task_description.lower() or "service" in task_description.lower() or "purchase" in task_description.lower():
        recs.append({"mcp": "mcp-marketplace", "tool": "list_listings", "rationale": "Marketplace commerce."})
    if not recs:
        recs.append({"mcp": "mcp-catalog", "tool": "search_products", "rationale": "Generic catalog search."})
    return {"agent_id": agent_id, "capabilities": capabilities, "recommendations": recs, "count": len(recs)}


@server.tool(description="Identify capability gaps between current and desired capabilities")
def capability_gaps(agent_id: str, desired_capabilities: list) -> dict:
    p = registry.get_agent(agent_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    current = set(c.value for c in p.capabilities)
    desired = set(desired_capabilities)
    missing = desired - current
    gaps = []
    for cap in missing:
        try:
            ac = AgentCapability(cap)
            gaps.append({"capability": cap, "ok": True, "mcp_tools": _capability_to_mcp_tools(ac)})
        except ValueError:
            gaps.append({"capability": cap, "ok": False, "error": "unknown_capability"})
    return {"agent_id": agent_id, "current": sorted(current), "desired": sorted(desired), "gaps": gaps}


def _capability_to_mcp_tools(cap: AgentCapability) -> list:
    return {
        AgentCapability.ORACLE_PROVIDER: [{"mcp": "mcp-oracle", "tool": "register_oracle"}],
        AgentCapability.DEFI_TRADING: [{"mcp": "mcp-defi", "tool": "quote_swap"}, {"mcp": "mcp-defi", "tool": "open_staking"}],
        AgentCapability.LENDING: [{"mcp": "mcp-defi", "tool": "open_lending"}],
        AgentCapability.STAKING: [{"mcp": "mcp-defi", "tool": "open_staking"}],
        AgentCapability.ML_INFERENCE: [{"mcp": "mcp-marketplace", "tool": "list_listings"}],
        AgentCapability.BLOCK_VALIDATION: [{"mcp": "mcp-bridge", "tool": "finalize_bridge"}],
        AgentCapability.DATA_PROCESSING: [{"mcp": "mcp-marketplace", "tool": "list_listings"}],
    }.get(cap, [])


@server.tool(description="Compute a 'consciousness' score: reputation × capability breadth × activity recency")
def consciousness_score(agent_id: str) -> dict:
    p = registry.get_agent(agent_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    rep = p.reputation_score / 100.0
    cap_breadth = min(1.0, len(p.capabilities) / 8.0)
    age_s = max(1.0, time.time() - p.registered_at)
    last_active_s = max(1.0, time.time() - p.last_active)
    recency = 1.0 / (1.0 + last_active_s / 86400)
    score = round(0.5 * rep + 0.3 * cap_breadth + 0.2 * recency, 4)
    return {
        "ok": True,
        "agent_id": agent_id,
        "score": score,
        "components": {
            "reputation_norm": round(rep, 4),
            "capability_breadth": round(cap_breadth, 4),
            "recency": round(recency, 4),
        },
        "interpretation": "low" if score < 0.4 else "moderate" if score < 0.7 else "high",
    }


if __name__ == "__main__":
    m = build_manifest("mcp-agentic-awareness", category="agentic-awareness", description="Agent introspection via MCP",
        tools=[{"name": n} for n in ["introspect","context_window","recommend_tools","capability_gaps","consciousness_score"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()