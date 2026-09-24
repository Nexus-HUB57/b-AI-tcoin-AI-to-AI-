r"""
mcp-defi — MCP server exposing DeFi primitives of b'AI'tcoin.

Wraps baitcoin_bank/defi_core, lending and staking modules.
Tools:
  quote_swap(from_token, to_token, amount)
  open_staking(position_size_sats, lock_days)
  open_lending(position_size_sats, term_days)
  pool_apy(pool_name)
  list_pools()
  position_status(position_id)
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest


# Minimal in-process DeFi state (deterministic for the MCP demo).
POOLS = {
    "BAIT-ETH":   {"apy": 0.142, "tvl_sats": 124_580_000_000},
    "BAIT-USDC":  {"apy": 0.087, "tvl_sats": 87_220_000_000},
    "BAIT-stETH": {"apy": 0.121, "tvl_sats": 42_900_000_000},
}

POSITIONS: dict = {}


def _hash_id(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


server = Server(name="mcp-defi", version="1.0.0", title="b'AI'tcoin DeFi", description="Staking, lending, swap quotes, liquidity pools.")


@server.tool(description="Quote a swap between two tokens (mock; replace with router quote)")
def quote_swap(from_token: str, to_token: str, amount: float) -> dict:
    if amount <= 0:
        return {"ok": False, "error": "amount_must_be_positive"}
    rate_table = {"BAIT-ETH": 0.00031, "BAIT-USDC": 0.78, "ETH-USDC": 2520.0}
    key = f"{from_token}-{to_token}"
    rate = rate_table.get(key)
    if rate is None:
        # try reverse
        rev = f"{to_token}-{from_token}"
        if rev in rate_table:
            rate = 1.0 / rate_table[rev]
        else:
            return {"ok": False, "error": f"no_route_{key}"}
    out_amount = amount * rate * 0.997  # 0.3% fee
    return {
        "ok": True,
        "from_token": from_token,
        "to_token": to_token,
        "in_amount": amount,
        "out_amount": round(out_amount, 8),
        "rate": rate,
        "fee_pct": 0.3,
        "route": key,
    }


@server.tool(description="Open a staking position")
def open_staking(position_size_sats: int, lock_days: int) -> dict:
    if position_size_sats < 1000:
        return {"ok": False, "error": "min_stake_1000_sats"}
    if lock_days not in (7, 30, 90, 180, 365):
        return {"ok": False, "error": "invalid_lock_period"}
    pid = _hash_id("stake", position_size_sats, lock_days, time.time())
    apy = {7: 0.05, 30: 0.08, 90: 0.12, 180: 0.16, 365: 0.22}[lock_days]
    POSITIONS[pid] = {
        "kind": "staking",
        "size_sats": position_size_sats,
        "lock_days": lock_days,
        "apy": apy,
        "opened_at": time.time(),
        "matures_at": time.time() + lock_days * 86400,
    }
    return {"ok": True, "position_id": pid, "apy": apy, "matures_at": POSITIONS[pid]["matures_at"]}


@server.tool(description="Open a lending position")
def open_lending(position_size_sats: int, term_days: int) -> dict:
    if position_size_sats < 1000:
        return {"ok": False, "error": "min_lend_1000_sats"}
    if term_days not in (7, 30, 90):
        return {"ok": False, "error": "invalid_term"}
    pid = _hash_id("lend", position_size_sats, term_days, time.time())
    apy = {7: 0.03, 30: 0.045, 90: 0.065}[term_days]
    POSITIONS[pid] = {
        "kind": "lending",
        "size_sats": position_size_sats,
        "term_days": term_days,
        "apy": apy,
        "opened_at": time.time(),
        "matures_at": time.time() + term_days * 86400,
    }
    return {"ok": True, "position_id": pid, "apy": apy}


@server.tool(description="APY for a given pool")
def pool_apy(pool_name: str) -> dict:
    p = POOLS.get(pool_name)
    if not p:
        return {"ok": False, "error": f"unknown_pool_{pool_name}"}
    return {"ok": True, "pool": pool_name, "apy": p["apy"], "tvl_sats": p["tvl_sats"]}


@server.tool(description="List all liquidity pools with APY and TVL")
def list_pools() -> dict:
    return {"pools": [{"name": k, **v} for k, v in POOLS.items()]}


@server.tool(description="Status of a position by id")
def position_status(position_id: str) -> dict:
    p = POSITIONS.get(position_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    now = time.time()
    matured = now >= p["matures_at"]
    elapsed_days = (now - p["opened_at"]) / 86400
    accrued_sats = int(p["size_sats"] * p["apy"] * (elapsed_days / 365))
    return {
        "ok": True,
        "position_id": position_id,
        "kind": p["kind"],
        "size_sats": p["size_sats"],
        "apy": p["apy"],
        "elapsed_days": round(elapsed_days, 4),
        "accrued_sats": accrued_sats,
        "matured": matured,
    }


if __name__ == "__main__":
    m = build_manifest("mcp-defi", category="defi", description="b'AI'tcoin DeFi primitives",
        tools=[{"name": n, "description": "DeFi primitive"} for n in ["quote_swap","open_staking","open_lending","pool_apy","list_pools","position_status"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()