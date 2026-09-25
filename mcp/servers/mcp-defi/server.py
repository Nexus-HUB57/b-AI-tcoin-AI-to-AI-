#!/usr/bin/env python3
"""
MCP DeFi — Staking, lending, swap quotes, and pool APY for the b'AI'tcoin ecosystem.

Tools:
  - get_staking_info(pool): Get staking information for a liquidity pool
  - get_lending_rates(asset): Get lending/borrowing rates for an asset
  - get_swap_quote(from,to,amount): Get a swap quote between two tokens
  - get_pool_apy(pool): Get APY for a liquidity pool
"""

from __future__ import annotations

import sys
import os
import time
import random
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mcp.sdk.base_server import BaseMCPServer, MCPError, MCPErrorCode


# ---------------------------------------------------------------------------
# Simulated DeFi data
# ---------------------------------------------------------------------------

KNOWN_POOLS = {
    "bait-eth": {"token0": "BAIT", "token1": "ETH", "tvl": 1_200_000, "fee": 0.003},
    "bait-btc": {"token0": "BAIT", "token1": "BTC", "tvl": 800_000, "fee": 0.003},
    "eth-usdc": {"token0": "ETH", "token1": "USDC", "tvl": 45_000_000, "fee": 0.003},
    "sol-usdc": {"token0": "SOL", "token1": "USDC", "tvl": 12_000_000, "fee": 0.003},
    "bait-usdc": {"token0": "BAIT", "token1": "USDC", "tvl": 350_000, "fee": 0.003},
}

KNOWN_LENDING_ASSETS = ["BAIT", "ETH", "BTC", "USDC", "SOL", "AVAX", "DAI"]


def _seeded_rng(*parts: str) -> random.Random:
    now = int(time.time())
    seed = int(hashlib.sha256(f"{':'.join(parts)}:{now // 30}".encode()).hexdigest(), 16)
    return random.Random(seed)


def _simulate_staking_info(pool: str) -> dict:
    now = int(time.time())
    pool_lower = pool.lower()
    base = KNOWN_POOLS.get(pool_lower, {
        "token0": "UNKNOWN", "token1": "UNKNOWN", "tvl": 100_000, "fee": 0.003,
    })
    rng = _seeded_rng("staking", pool)

    apy = round(rng.uniform(2, 45), 2)
    return {
        "pool": pool_lower,
        "token0": base["token0"],
        "token1": base["token1"],
        "tvl": base["tvl"] + rng.randint(-50_000, 50_000),
        "apy": apy,
        "baseApy": round(apy * rng.uniform(0.4, 0.8), 2),
        "rewardApy": round(apy * rng.uniform(0.2, 0.6), 2),
        "totalStakers": rng.randint(50, 5000),
        "lockPeriod": rng.choice([0, 7, 14, 30, 90, 365]),
        "feeBps": int(base["fee"] * 10000),
        "timestamp": now,
    }


def _simulate_lending_rates(asset: str) -> dict:
    now = int(time.time())
    rng = _seeded_rng("lending", asset)
    is_stablecoin = asset.upper() in ("USDC", "DAI", "USDT")

    supply_base = rng.uniform(0.5, 3.0) if is_stablecoin else rng.uniform(0.1, 8.0)
    borrow_base = rng.uniform(1.0, 5.0) if is_stablecoin else rng.uniform(1.0, 12.0)

    return {
        "asset": asset.upper(),
        "supplyApy": round(supply_base, 2),
        "borrowApy": round(borrow_base, 2),
        "supplyApyVariable": round(supply_base * rng.uniform(0.8, 1.2), 2),
        "borrowApyVariable": round(borrow_base * rng.uniform(0.8, 1.2), 2),
        "utilization": round(rng.uniform(30, 95), 2),
        "totalDeposits": round(rng.uniform(500_000, 50_000_000), 2),
        "totalBorrows": round(rng.uniform(100_000, 30_000_000), 2),
        "collateralFactor": round(rng.uniform(50, 85), 2) if not is_stablecoin else 90.0,
        "liquidationThreshold": round(rng.uniform(60, 90), 2),
        "timestamp": now,
    }


def _simulate_swap_quote(from_token: str, to_token: str, amount: float) -> dict:
    now = int(time.time())
    rng = _seeded_rng("swap", from_token, to_token)

    # Simulated price ratios
    price_map = {"BAIT": 0.042, "BTC": 67500, "ETH": 3450, "SOL": 172, "USDC": 1.0, "AVAX": 38.5}
    p_from = price_map.get(from_token.upper(), rng.uniform(0.1, 100))
    p_to = price_map.get(to_token.upper(), rng.uniform(0.1, 100))

    rate = (p_from / p_to) * rng.uniform(0.995, 1.005)
    output = amount * rate
    fee = output * 0.003
    slippage = round(rng.uniform(0.01, 0.5), 3)

    return {
        "fromToken": from_token.upper(),
        "toToken": to_token.upper(),
        "inputAmount": amount,
        "outputAmount": round(output - fee, 8),
        "exchangeRate": round(rate, 8),
        "fee": round(fee, 8),
        "feeBps": 30,
        "priceImpact": f"{slippage}%",
        "route": [from_token.upper(), to_token.upper()],
        "estimatedGas": rng.randint(100_000, 300_000),
        "timestamp": now,
    }


def _simulate_pool_apy(pool: str) -> dict:
    now = int(time.time())
    rng = _seeded_rng("apy", pool)
    pool_lower = pool.lower()
    base = KNOWN_POOLS.get(pool_lower, {
        "token0": "UNKNOWN", "token1": "UNKNOWN", "tvl": 100_000, "fee": 0.003,
    })

    apy = round(rng.uniform(1.5, 50), 2)
    return {
        "pool": pool_lower,
        "token0": base["token0"],
        "token1": base["token1"],
        "apy": apy,
        "apy7d": round(apy * rng.uniform(0.8, 1.2), 2),
        "apy30d": round(apy * rng.uniform(0.7, 1.3), 2),
        "ilRisk": round(rng.uniform(0, 15), 2),
        "tvl": base["tvl"],
        "volume24h": round(rng.uniform(10_000, 5_000_000), 2),
        "fee24h": round(rng.uniform(100, 15000), 2),
        "timestamp": now,
    }


# ---------------------------------------------------------------------------
# DeFi MCP Server
# ---------------------------------------------------------------------------

class DeFiServer(BaseMCPServer):
    """MCP DeFi server for staking, lending, swap quotes, and pool APY."""

    def __init__(self):
        super().__init__(
            name="mcp-defi",
            version="1.0.0",
            description="Staking, lending, swap quotes, and pool APY for the b'AI'tcoin DeFi ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "get_staking_info",
            "Get staking information for a liquidity pool",
            self._handle_get_staking_info,
            input_schema={
                "type": "object",
                "properties": {"pool": {"type": "string", "description": "Pool identifier (e.g. bait-eth, eth-usdc)"}},
                "required": ["pool"],
            },
            category="staking",
        )
        self._register_tool(
            "get_lending_rates",
            "Get lending and borrowing rates for an asset",
            self._handle_get_lending_rates,
            input_schema={
                "type": "object",
                "properties": {"asset": {"type": "string", "description": "Asset symbol (e.g. BAIT, ETH, USDC)"}},
                "required": ["asset"],
            },
            category="lending",
        )
        self._register_tool(
            "get_swap_quote",
            "Get a swap quote between two tokens",
            self._handle_get_swap_quote,
            input_schema={
                "type": "object",
                "properties": {
                    "from": {"type": "string", "description": "Source token symbol"},
                    "to": {"type": "string", "description": "Destination token symbol"},
                    "amount": {"type": "number", "description": "Amount of source token to swap"},
                },
                "required": ["from", "to", "amount"],
            },
            category="swap",
        )
        self._register_tool(
            "get_pool_apy",
            "Get APY and performance metrics for a liquidity pool",
            self._handle_get_pool_apy,
            input_schema={
                "type": "object",
                "properties": {"pool": {"type": "string", "description": "Pool identifier"}},
                "required": ["pool"],
            },
            category="pool",
        )

    def _handle_get_staking_info(self, arguments: dict) -> dict:
        pool = arguments.get("pool", "").strip()
        if not pool:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'pool' is required")
        return _simulate_staking_info(pool)

    def _handle_get_lending_rates(self, arguments: dict) -> dict:
        asset = arguments.get("asset", "").strip()
        if not asset:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'asset' is required")
        return _simulate_lending_rates(asset)

    def _handle_get_swap_quote(self, arguments: dict) -> dict:
        from_token = arguments.get("from", "").strip()
        to_token = arguments.get("to", "").strip()
        amount = arguments.get("amount")
        if not from_token or not to_token:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameters 'from' and 'to' are required")
        if amount is None:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'amount' is required")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'amount' must be a number")
        if amount <= 0:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'amount' must be positive")
        return _simulate_swap_quote(from_token, to_token, amount)

    def _handle_get_pool_apy(self, arguments: dict) -> dict:
        pool = arguments.get("pool", "").strip()
        if not pool:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'pool' is required")
        return _simulate_pool_apy(pool)


if __name__ == "__main__":
    DeFiServer().run()
