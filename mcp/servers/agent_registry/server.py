r"""
mcp-agent-registry — MCP server wrapping baitcoin_ai/agent_protocol/registry.py.

Tools:
  register_agent(pubkey_hex, capabilities, reputation)
  lookup_agent(agent_id)
  list_by_capability(capability)
  update_reputation(agent_id, delta)
  agent_stats(agent_id)
  discover_agents(min_reputation)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest
from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability


registry = AgentRegistry()
server = Server(name="mcp-agent-registry", version="1.0.0", title="b'AI'tcoin Agent Registry", description="A2A identity, capabilities, reputation.")


@server.tool(description="Register a new agent identity")
def register_agent(pubkey_hex: str, capabilities: list, reputation: float = 50.0) -> dict:
    caps = set()
    for c in capabilities:
        try:
            caps.add(AgentCapability(c))
        except ValueError:
            return {"ok": False, "error": f"unknown_capability_{c}"}
    profile = registry.register(pubkey_hex, caps, reputation)
    return {"ok": True, "agent_id": profile.agent_id, "trust_level": profile.trust_level}


@server.tool(description="Lookup agent by id")
def lookup_agent(agent_id: str) -> dict:
    p = registry.get(agent_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "agent_id": p.agent_id, "capabilities": [c.value for c in p.capabilities], "reputation": p.reputation_score, "trust_level": p.trust_level, "stake_sats": p.stake_sats}


@server.tool(description="List agents that declare a capability")
def list_by_capability(capability: str) -> dict:
    try:
        cap = AgentCapability(capability)
    except ValueError:
        return {"ok": False, "error": f"unknown_capability_{capability}"}
    agents = [p for p in registry.agents.values() if cap in p.capabilities]
    return {"ok": True, "count": len(agents), "agents": [{"agent_id": p.agent_id, "reputation": p.reputation_score, "trust_level": p.trust_level} for p in agents]}


@server.tool(description="Update an agent's reputation (positive or negative delta)")
def update_reputation(agent_id: str, delta: float) -> dict:
    p = registry.get(agent_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    p.reputation_score = max(0.0, min(100.0, p.reputation_score + delta))
    return {"ok": True, "agent_id": agent_id, "new_reputation": p.reputation_score, "trust_level": p.trust_level}


@server.tool(description="Aggregated stats for an agent")
def agent_stats(agent_id: str) -> dict:
    p = registry.get(agent_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    return {
        "ok": True,
        "agent_id": p.agent_id,
        "pubkey": p.pubkey_hex,
        "reputation": p.reputation_score,
        "trust_level": p.trust_level,
        "capabilities_count": len(p.capabilities),
        "stake_sats": p.stake_sats,
        "is_validator": p.is_validator,
        "registered_at": p.registered_at,
        "last_active": p.last_active,
        "metadata": p.metadata,
    }


@server.tool(description="Discover high-trust agents (min reputation filter)")
def discover_agents(min_reputation: float = 50.0) -> dict:
    agents = [p for p in registry.agents.values() if p.reputation_score >= min_reputation]
    agents.sort(key=lambda p: p.reputation_score, reverse=True)
    return {"ok": True, "count": len(agents), "agents": [{"agent_id": p.agent_id, "reputation": p.reputation_score, "trust_level": p.trust_level, "capabilities": [c.value for c in p.capabilities]} for p in agents[:50]]}


if __name__ == "__main__":
    m = build_manifest("mcp-agent-registry", category="agent-registry", description="A2A identity registry via MCP",
        tools=[{"name": n} for n in ["register_agent","lookup_agent","list_by_capability","update_reputation","agent_stats","discover_agents"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()