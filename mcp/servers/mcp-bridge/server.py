#!/usr/bin/env python3
"""
MCP Bridge — Lock-and-mint multisig bridge and cross-chain transfers.

Tools:
  - get_bridge_status(txId): Get status of a bridge transaction
  - initiate_bridge(asset, amount, targetChain): Initiate a cross-chain bridge transfer
  - get_multisig_status(proposalId): Get multisig proposal status
  - list_pending_bridges(): List all pending bridge transactions
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
# In-memory bridge state
# ---------------------------------------------------------------------------

PENDING_BRIDGES: dict[str, dict] = {}
MULTISIG_PROPOSALS: dict[str, dict] = {}

SUPPORTED_CHAINS = ["baitchain", "ethereum", "solana", "avalanche", "polygon", "arbitrum"]
SUPPORTED_ASSETS = ["BAIT", "ETH", "BTC", "SOL", "AVAX", "USDC"]


def _new_tx_id() -> str:
    return f"btx-{uuid.uuid4().hex[:16]}"


def _new_proposal_id() -> str:
    return f"msp-{uuid.uuid4().hex[:12]}"


def _now() -> int:
    return int(time.time())


# ---------------------------------------------------------------------------
# Bridge MCP Server
# ---------------------------------------------------------------------------

class BridgeServer(BaseMCPServer):
    """MCP Bridge server for lock-and-mint cross-chain transfers with multisig."""

    def __init__(self):
        super().__init__(
            name="mcp-bridge",
            version="1.0.0",
            description="Lock-and-mint multisig bridge for cross-chain transfers in the b'AI'tcoin ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "get_bridge_status",
            "Get status of a bridge transaction by its ID",
            self._handle_get_bridge_status,
            input_schema={
                "type": "object",
                "properties": {"txId": {"type": "string", "description": "Bridge transaction ID"}},
                "required": ["txId"],
            },
            category="bridge",
        )
        self._register_tool(
            "initiate_bridge",
            "Initiate a cross-chain bridge transfer (lock-and-mint)",
            self._handle_initiate_bridge,
            input_schema={
                "type": "object",
                "properties": {
                    "asset": {"type": "string", "description": "Asset to bridge (e.g. BAIT, ETH)"},
                    "amount": {"type": "number", "description": "Amount to bridge"},
                    "targetChain": {"type": "string", "description": "Target chain (e.g. solana, ethereum)"},
                },
                "required": ["asset", "amount", "targetChain"],
            },
            category="bridge",
        )
        self._register_tool(
            "get_multisig_status",
            "Get multisig proposal status for a bridge transaction",
            self._handle_get_multisig_status,
            input_schema={
                "type": "object",
                "properties": {"proposalId": {"type": "string", "description": "Multisig proposal ID"}},
                "required": ["proposalId"],
            },
            category="multisig",
        )
        self._register_tool(
            "list_pending_bridges",
            "List all pending bridge transactions",
            self._handle_list_pending_bridges,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="bridge",
        )

    def _handle_get_bridge_status(self, arguments: dict) -> dict:
        tx_id = arguments.get("txId", "").strip()
        if not tx_id:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'txId' is required")

        # Check in-memory pending bridges
        if tx_id in PENDING_BRIDGES:
            return PENDING_BRIDGES[tx_id]

        # For unknown tx IDs, simulate a completed bridge
        rng = random.Random(hash(tx_id))
        return {
            "txId": tx_id,
            "status": rng.choice(["completed", "completed", "failed", "expired"]),
            "sourceChain": "baitchain",
            "targetChain": rng.choice(SUPPORTED_CHAINS[1:]),
            "asset": rng.choice(SUPPORTED_ASSETS),
            "amount": round(rng.uniform(0.1, 100), 4),
            "confirmations": rng.randint(12, 64),
            "lockTxHash": f"0x{hashlib.sha256(tx_id.encode()).hexdigest()[:40]}",
            "mintTxHash": f"0x{hashlib.sha256(f'mint:{tx_id}'.encode()).hexdigest()[:40]}",
            "timestamp": _now(),
        }

    def _handle_initiate_bridge(self, arguments: dict) -> dict:
        asset = arguments.get("asset", "").strip().upper()
        amount = arguments.get("amount")
        target_chain = arguments.get("targetChain", "").strip().lower()

        if not asset:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'asset' is required")
        if amount is None:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'amount' is required")
        if not target_chain:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'targetChain' is required")

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'amount' must be a number")

        if amount <= 0:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'amount' must be positive")

        if asset not in SUPPORTED_ASSETS:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, f"Unsupported asset: {asset}. Supported: {SUPPORTED_ASSETS}")
        if target_chain not in SUPPORTED_CHAINS:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, f"Unsupported chain: {target_chain}. Supported: {SUPPORTED_CHAINS}")

        tx_id = _new_tx_id()
        proposal_id = _new_proposal_id()

        bridge_record = {
            "txId": tx_id,
            "status": "pending_lock",
            "sourceChain": "baitchain",
            "targetChain": target_chain,
            "asset": asset,
            "amount": amount,
            "confirmations": 0,
            "lockTxHash": None,
            "mintTxHash": None,
            "multisigProposalId": proposal_id,
            "estimatedTimeMinutes": random.randint(5, 30),
            "feeSats": int(amount * 100_000_000 * 0.001),  # 0.1% fee
            "timestamp": _now(),
        }
        PENDING_BRIDGES[tx_id] = bridge_record

        multisig_record = {
            "proposalId": proposal_id,
            "bridgeTxId": tx_id,
            "status": "awaiting_signatures",
            "signatures": [],
            "requiredSignatures": 3,
            "totalValidators": 5,
            "timestamp": _now(),
        }
        MULTISIG_PROPOSALS[proposal_id] = multisig_record

        return bridge_record

    def _handle_get_multisig_status(self, arguments: dict) -> dict:
        proposal_id = arguments.get("proposalId", "").strip()
        if not proposal_id:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'proposalId' is required")

        if proposal_id in MULTISIG_PROPOSALS:
            return MULTISIG_PROPOSALS[proposal_id]

        # Simulate a past proposal
        rng = random.Random(hash(proposal_id))
        return {
            "proposalId": proposal_id,
            "status": rng.choice(["executed", "executed", "expired", "rejected"]),
            "signatures": [f"0x{rng.getrandbits(160):040x}" for _ in range(rng.randint(2, 5))],
            "requiredSignatures": 3,
            "totalValidators": 5,
            "timestamp": _now(),
        }

    def _handle_list_pending_bridges(self, arguments: dict) -> dict:
        pending = [
            bridge for bridge in PENDING_BRIDGES.values()
            if bridge["status"].startswith("pending")
        ]
        return {
            "count": len(pending),
            "bridges": pending,
            "timestamp": _now(),
        }


if __name__ == "__main__":
    BridgeServer().run()
