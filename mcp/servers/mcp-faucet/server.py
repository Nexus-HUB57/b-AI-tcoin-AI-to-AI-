#!/usr/bin/env python3
"""
MCP Faucet — BAIT token distribution for agents.

Tools:
  - claim_bait(agentAddress): Claim BAIT tokens for an agent address
  - get_faucet_status(): Get current faucet status and remaining supply
  - get_claim_history(agent): Get claim history for an agent
"""

from __future__ import annotations

import sys
import os
import time
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mcp.sdk.base_server import BaseMCPServer, MCPError, MCPErrorCode


# ---------------------------------------------------------------------------
# In-memory faucet state
# ---------------------------------------------------------------------------

FAUCET_SUPPLY = 10_000_000.0  # 10M BAIT
CLAIM_AMOUNT = 100.0  # 100 BAIT per claim
COOLDOWN_SECONDS = 3600  # 1 hour cooldown between claims

CLAIM_HISTORY: dict[str, list[dict]] = {}  # address → list of claims
TOTAL_DISTRIBUTED = 0.0


def _now() -> int:
    return int(time.time())


# ---------------------------------------------------------------------------
# Faucet MCP Server
# ---------------------------------------------------------------------------

class FaucetServer(BaseMCPServer):
    """MCP Faucet server for BAIT token distribution to agents."""

    def __init__(self):
        super().__init__(
            name="mcp-faucet",
            version="1.0.0",
            description="BAIT token faucet for agent onboarding and testing in the b'AI'tcoin ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "claim_bait",
            "Claim BAIT tokens for an agent address (100 BAIT per claim, 1hr cooldown)",
            self._handle_claim_bait,
            input_schema={
                "type": "object",
                "properties": {"agentAddress": {"type": "string", "description": "Agent address to claim BAIT for"}},
                "required": ["agentAddress"],
            },
            category="distribution",
        )
        self._register_tool(
            "get_faucet_status",
            "Get current faucet status including remaining supply and distribution stats",
            self._handle_get_faucet_status,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="status",
        )
        self._register_tool(
            "get_claim_history",
            "Get claim history for a specific agent address",
            self._handle_get_claim_history,
            input_schema={
                "type": "object",
                "properties": {"agent": {"type": "string", "description": "Agent address to look up"}},
                "required": ["agent"],
            },
            category="history",
        )

    def _handle_claim_bait(self, arguments: dict) -> dict:
        global TOTAL_DISTRIBUTED

        address = arguments.get("agentAddress", "").strip()
        if not address:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'agentAddress' is required")

        now = _now()

        # Check supply
        remaining = FAUCET_SUPPLY - TOTAL_DISTRIBUTED
        if remaining < CLAIM_AMOUNT:
            return {
                "status": "insufficient_supply",
                "message": "Faucet supply exhausted",
                "remainingSupply": remaining,
                "timestamp": now,
            }

        # Check cooldown
        if address in CLAIM_HISTORY and CLAIM_HISTORY[address]:
            last_claim = CLAIM_HISTORY[address][-1]
            elapsed = now - last_claim["timestamp"]
            if elapsed < COOLDOWN_SECONDS:
                return {
                    "status": "cooldown_active",
                    "message": f"Cooldown active; {COOLDOWN_SECONDS - elapsed}s remaining",
                    "nextClaimAt": last_claim["timestamp"] + COOLDOWN_SECONDS,
                    "cooldownRemaining": COOLDOWN_SECONDS - elapsed,
                    "timestamp": now,
                }

        # Process claim
        claim_record = {
            "amount": CLAIM_AMOUNT,
            "token": "BAIT",
            "txHash": f"0x{hashlib.sha256(f'{address}:{now}'.encode()).hexdigest()[:40]}",
            "timestamp": now,
        }

        if address not in CLAIM_HISTORY:
            CLAIM_HISTORY[address] = []
        CLAIM_HISTORY[address].append(claim_record)
        TOTAL_DISTRIBUTED += CLAIM_AMOUNT

        return {
            "status": "success",
            "agentAddress": address,
            "amount": CLAIM_AMOUNT,
            "token": "BAIT",
            "txHash": claim_record["txHash"],
            "newBalance": sum(c["amount"] for c in CLAIM_HISTORY[address]),
            "totalClaims": len(CLAIM_HISTORY[address]),
            "timestamp": now,
        }

    def _handle_get_faucet_status(self, arguments: dict) -> dict:
        now = _now()
        remaining = FAUCET_SUPPLY - TOTAL_DISTRIBUTED
        total_agents = len(CLAIM_HISTORY)
        total_claims = sum(len(claims) for claims in CLAIM_HISTORY.values())

        return {
            "status": "active" if remaining >= CLAIM_AMOUNT else "exhausted",
            "totalSupply": FAUCET_SUPPLY,
            "remainingSupply": remaining,
            "distributed": TOTAL_DISTRIBUTED,
            "claimAmount": CLAIM_AMOUNT,
            "cooldownSeconds": COOLDOWN_SECONDS,
            "uniqueAgents": total_agents,
            "totalClaims": total_claims,
            "timestamp": now,
        }

    def _handle_get_claim_history(self, arguments: dict) -> dict:
        agent = arguments.get("agent", "").strip()
        if not agent:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'agent' is required")

        now = _now()
        claims = CLAIM_HISTORY.get(agent, [])

        return {
            "agent": agent,
            "totalClaims": len(claims),
            "totalAmount": sum(c["amount"] for c in claims),
            "claims": claims,
            "timestamp": now,
        }


if __name__ == "__main__":
    FaucetServer().run()
