r"""
mcp-faucet — MCP server for the b'AI'tcoin testnet faucet.

Tools:
  request_drip(agent_address, amount_sats, reason)
  balance(agent_address)
  drip_history(agent_address)
  faucet_stats()
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest


DRIPS: dict = {}
LIMITS = {"per_request_sats": 50_000, "per_day_sats": 100_000, "cooldown_s": 3600}


def _now():
    return int(time.time())


def _hash(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


server = Server(name="mcp-faucet", version="1.0.0", title="b'AI'tcoin Faucet", description="Testnet BAIT distribution for new agents.")


@server.tool(description="Request a faucet drip for a new agent")
def request_drip(agent_address: str, amount_sats: int = 50_000, reason: str = "onboarding") -> dict:
    if amount_sats > LIMITS["per_request_sats"]:
        return {"ok": False, "error": f"exceeds_per_request_{LIMITS['per_request_sats']}"}
    history = DRIPS.setdefault(agent_address, [])
    day_window = [d for d in history if d["ts"] > _now() - 86400]
    if sum(d["amount_sats"] for d in day_window) + amount_sats > LIMITS["per_day_sats"]:
        return {"ok": False, "error": "exceeds_daily_limit"}
    if history and history[-1]["ts"] > _now() - LIMITS["cooldown_s"]:
        wait = LIMITS["cooldown_s"] - (_now() - history[-1]["ts"])
        return {"ok": False, "error": "cooldown", "wait_s": wait}
    drip_id = _hash(agent_address, amount_sats, reason, _now())
    entry = {"drip_id": drip_id, "agent": agent_address, "amount_sats": amount_sats, "reason": reason, "ts": _now(), "tx_hash": _hash("tx", drip_id)}
    return {"ok": True, **entry}


@server.tool(description="Balance for an agent from faucet alone (does not reflect chain balance)")
def balance(agent_address: str) -> dict:
    history = DRIPS.get(agent_address, [])
    return {"agent": agent_address, "total_sats": sum(d["amount_sats"] for d in history), "drip_count": len(history)}


@server.tool(description="History of faucet drips for an agent")
def drip_history(agent_address: str, limit: int = 50) -> dict:
    history = DRIPS.get(agent_address, [])[-limit:]
    return {"agent": agent_address, "history": history, "count": len(history)}


@server.tool(description="Global faucet stats")
def faucet_stats() -> dict:
    total_sats = sum(sum(d["amount_sats"] for d in v) for v in DRIPS.values())
    return {
        "unique_agents": len(DRIPS),
        "total_drips": sum(len(v) for v in DRIPS.values()),
        "total_sats": total_sats,
        "limits": LIMITS,
    }


if __name__ == "__main__":
    m = build_manifest("mcp-faucet", category="faucet", description="b'AI'tcoin testnet faucet via MCP",
        tools=[{"name": n} for n in ["request_drip","balance","drip_history","faucet_stats"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()