#!/usr/bin/env python3
"""
MCP Agent Registry — A2A discovery, identity, and reputation.

Tools:
  - register_agent(name, capabilities): Register a new agent
  - discover_agents(capability): Discover agents by capability
  - get_agent_profile(address): Get agent profile by address
  - get_reputation(address): Get reputation score for an agent
"""

from __future__ import annotations

import sys
import os
import time
import random
import hashlib
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mcp.sdk.base_server import BaseMCPServer, MCPError, MCPErrorCode


# ---------------------------------------------------------------------------
# In-memory agent registry
# ---------------------------------------------------------------------------

AGENT_REGISTRY: dict[str, dict] = {}  # address → profile


def _now() -> int:
    return int(time.time())


def _generate_address() -> str:
    """Generate a deterministic-looking agent address."""
    return f"0x{uuid.uuid4().hex[:40]}"


# ---------------------------------------------------------------------------
# Agent Registry MCP Server
# ---------------------------------------------------------------------------

class AgentRegistryServer(BaseMCPServer):
    """MCP Agent Registry for A2A discovery, identity, and reputation."""

    def __init__(self):
        super().__init__(
            name="mcp-agent-registry",
            version="1.0.0",
            description="Agent-to-Agent discovery, identity management, and reputation scoring for the b'AI'tcoin ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "register_agent",
            "Register a new agent with name and capabilities",
            self._handle_register_agent,
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Agent display name"},
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of capability strings (e.g. trading, analysis, bridging)",
                    },
                },
                "required": ["name", "capabilities"],
            },
            category="identity",
        )
        self._register_tool(
            "discover_agents",
            "Discover agents matching a specific capability",
            self._handle_discover_agents,
            input_schema={
                "type": "object",
                "properties": {"capability": {"type": "string", "description": "Capability to search for"}},
                "required": ["capability"],
            },
            category="discovery",
        )
        self._register_tool(
            "get_agent_profile",
            "Get full agent profile by address",
            self._handle_get_agent_profile,
            input_schema={
                "type": "object",
                "properties": {"address": {"type": "string", "description": "Agent address"}},
                "required": ["address"],
            },
            category="identity",
        )
        self._register_tool(
            "get_reputation",
            "Get reputation score and history for an agent",
            self._handle_get_reputation,
            input_schema={
                "type": "object",
                "properties": {"address": {"type": "string", "description": "Agent address"}},
                "required": ["address"],
            },
            category="reputation",
        )

    def _handle_register_agent(self, arguments: dict) -> dict:
        name = arguments.get("name", "").strip()
        capabilities = arguments.get("capabilities", [])

        if not name:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'name' is required")
        if not capabilities or not isinstance(capabilities, list):
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'capabilities' must be a non-empty list")

        now = _now()
        address = _generate_address()

        profile = {
            "address": address,
            "name": name,
            "capabilities": [str(c) for c in capabilities],
            "status": "active",
            "registeredAt": now,
            "lastActiveAt": now,
            "reputation": {
                "score": 50.0,  # Start at neutral
                "totalInteractions": 0,
                "successfulInteractions": 0,
                "failedInteractions": 0,
                "endorsements": 0,
                "flags": 0,
            },
            "metadata": {
                "version": "1.0.0",
                "framework": "baitcoin-a2a",
            },
        }

        AGENT_REGISTRY[address] = profile

        return {
            "status": "registered",
            "address": address,
            "name": name,
            "capabilities": profile["capabilities"],
            "timestamp": now,
        }

    def _handle_discover_agents(self, arguments: dict) -> dict:
        capability = arguments.get("capability", "").strip().lower()
        if not capability:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'capability' is required")

        now = _now()
        matching = []
        for addr, profile in AGENT_REGISTRY.items():
            if any(capability in c.lower() for c in profile.get("capabilities", [])):
                matching.append({
                    "address": addr,
                    "name": profile["name"],
                    "capabilities": profile["capabilities"],
                    "reputation": profile["reputation"]["score"],
                    "status": profile["status"],
                })

        # Sort by reputation (highest first)
        matching.sort(key=lambda a: a["reputation"], reverse=True)

        return {
            "capability": capability,
            "count": len(matching),
            "agents": matching,
            "timestamp": now,
        }

    def _handle_get_agent_profile(self, arguments: dict) -> dict:
        address = arguments.get("address", "").strip()
        if not address:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'address' is required")

        if address not in AGENT_REGISTRY:
            raise MCPError(MCPErrorCode.RESOURCE_NOT_FOUND, f"Agent not found: {address}")

        profile = AGENT_REGISTRY[address]
        profile["lastActiveAt"] = _now()
        return profile

    def _handle_get_reputation(self, arguments: dict) -> dict:
        address = arguments.get("address", "").strip()
        if not address:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'address' is required")

        if address not in AGENT_REGISTRY:
            raise MCPError(MCPErrorCode.RESOURCE_NOT_FOUND, f"Agent not found: {address}")

        profile = AGENT_REGISTRY[address]
        rep = profile["reputation"]

        # Compute tier
        score = rep["score"]
        if score >= 80:
            tier = "platinum"
        elif score >= 60:
            tier = "gold"
        elif score >= 40:
            tier = "silver"
        else:
            tier = "bronze"

        return {
            "address": address,
            "name": profile["name"],
            "score": score,
            "tier": tier,
            "totalInteractions": rep["totalInteractions"],
            "successfulInteractions": rep["successfulInteractions"],
            "failedInteractions": rep["failedInteractions"],
            "successRate": (
                round(rep["successfulInteractions"] / rep["totalInteractions"] * 100, 2)
                if rep["totalInteractions"] > 0 else 0.0
            ),
            "endorsements": rep["endorsements"],
            "flags": rep["flags"],
            "timestamp": _now(),
        }


if __name__ == "__main__":
    AgentRegistryServer().run()
