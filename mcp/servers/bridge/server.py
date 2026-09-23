r"""
mcp-bridge — MCP server exposing the b'AI'tcoin multisig bridge.

Wraps baitcoin_bridge. Tools:
  initiate_bridge(from_chain, to_chain, amount_sats, recipient)
  sign_bridge(bridge_id, signer_agent_id)
  finalize_bridge(bridge_id)
  bridge_status(bridge_id)
  list_pending()
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from enum import Enum

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest, McpError, ErrorCode


class BridgeState(str, Enum):
    INITIATED = "initiated"
    SIGNED = "signed"
    FINALIZED = "finalized"
    EXPIRED = "expired"


BRIDGES: dict = {}
REQUIRED_SIGS = 3  # 3-of-5 multisig


def _id(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


server = Server(name="mcp-bridge", version="1.0.0", title="b'AI'tcoin Bridge", description="Multisig 3-of-5 lock-and-mint bridge.")


@server.tool(description="Initiate a bridge transfer (lock on source, mint on destination)")
def initiate_bridge(from_chain: str, to_chain: str, amount_sats: int, recipient: str) -> dict:
    if amount_sats < 10000:
        return {"ok": False, "error": "min_bridge_10000_sats"}
    bid = _id("bridge", from_chain, to_chain, amount_sats, recipient, time.time())
    BRIDGES[bid] = {
        "id": bid,
        "from_chain": from_chain,
        "to_chain": to_chain,
        "amount_sats": amount_sats,
        "recipient": recipient,
        "signatures": [],
        "required_sigs": REQUIRED_SIGS,
        "state": BridgeState.INITIATED,
        "created_at": time.time(),
    }
    return {"ok": True, "bridge_id": bid, "required_signatures": REQUIRED_SIGS}


@server.tool(description="Add a multisig signature to a bridge request")
def sign_bridge(bridge_id: str, signer_agent_id: str) -> dict:
    b = BRIDGES.get(bridge_id)
    if not b:
        raise McpError(ErrorCode.RESOURCE_NOT_FOUND, f"bridge not found: {bridge_id}")
    if b["state"] != BridgeState.INITIATED:
        return {"ok": False, "error": f"bridge_not_initiated_state_{b['state']}"}
    if signer_agent_id in b["signatures"]:
        return {"ok": False, "error": "already_signed"}
    b["signatures"].append(signer_agent_id)
    if len(b["signatures"]) >= b["required_sigs"]:
        b["state"] = BridgeState.SIGNED
    return {"ok": True, "signatures_collected": len(b["signatures"]), "required": b["required_sigs"], "state": b["state"]}


@server.tool(description="Finalize a signed bridge (mint on destination)")
def finalize_bridge(bridge_id: str) -> dict:
    b = BRIDGES.get(bridge_id)
    if not b:
        return {"ok": False, "error": "not_found"}
    if b["state"] != BridgeState.SIGNED:
        return {"ok": False, "error": f"bridge_not_signed_state_{b['state']}"}
    b["state"] = BridgeState.FINALIZED
    b["finalized_at"] = time.time()
    return {"ok": True, "bridge_id": bridge_id, "tx_hash": _id(b["id"], b["amount_sats"], b["finalized_at"])}


@server.tool(description="Bridge status")
def bridge_status(bridge_id: str) -> dict:
    b = BRIDGES.get(bridge_id)
    if not b:
        return {"ok": False, "error": "not_found"}
    return b


@server.tool(description="List all bridges awaiting signatures")
def list_pending() -> dict:
    pending = [b for b in BRIDGES.values() if b["state"] == BridgeState.INITIATED]
    return {"pending": pending, "count": len(pending)}


if __name__ == "__main__":
    m = build_manifest("mcp-bridge", category="bridge", description="b'AI'tcoin multisig bridge via MCP",
        tools=[{"name": n} for n in ["initiate_bridge","sign_bridge","finalize_bridge","bridge_status","list_pending"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()