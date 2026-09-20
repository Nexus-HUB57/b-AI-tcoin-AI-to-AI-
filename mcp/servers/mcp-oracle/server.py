#!/usr/bin/env python3
"""
MCP Oracle — Price feeds, on-chain metrics, and risk signals for the b'AI'tcoin ecosystem.

Tools:
  - get_price(symbol): Get current price for a token symbol
  - get_onchain_metrics(chain): Get on-chain metrics for a blockchain
  - get_risk_signal(asset): Get risk signal for an asset
  - get_market_summary(): Get overall market summary
"""

from __future__ import annotations

import sys
import os
import time
import random
import hashlib

# Allow running from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mcp.sdk.base_server import BaseMCPServer, MCPError, MCPErrorCode


# ---------------------------------------------------------------------------
# Simulated data sources (in production these would call real oracles)
# ---------------------------------------------------------------------------

PRICE_CACHE: dict[str, dict] = {}
CHAIN_METRICS: dict[str, dict] = {}


def _simulate_price(symbol: str) -> dict:
    """Generate a deterministic-but-varying price for a symbol."""
    now = int(time.time())
    seed = int(hashlib.sha256(f"{symbol}:{now // 30}".encode()).hexdigest(), 16)
    rng = random.Random(seed)

    base_prices = {
        "BAIT": 0.042, "BTC": 67500.0, "ETH": 3450.0, "SOL": 172.0,
        "AVAX": 38.5, "MATIC": 0.72, "DOT": 7.1, "LINK": 14.8,
        "UNI": 9.3, "AAVE": 92.0, "ARB": 1.12, "OP": 2.85,
    }
    base = base_prices.get(symbol.upper(), rng.uniform(0.01, 100.0))
    variation = rng.uniform(-0.05, 0.05)
    price = round(base * (1 + variation), 6)

    return {
        "symbol": symbol.upper(),
        "price": price,
        "currency": "USD",
        "change24h": round(rng.uniform(-12, 12), 2),
        "change7d": round(rng.uniform(-25, 25), 2),
        "volume24h": round(rng.uniform(100_000, 50_000_000), 2),
        "marketCap": round(price * rng.uniform(1_000_000, 100_000_000), 2),
        "timestamp": now,
        "source": "baitcoin-oracle-v1",
    }


def _simulate_chain_metrics(chain: str) -> dict:
    """Generate on-chain metrics for a blockchain."""
    now = int(time.time())
    seed = int(hashlib.sha256(f"{chain}:{now // 60}".encode()).hexdigest(), 16)
    rng = random.Random(seed)

    return {
        "chain": chain.upper(),
        "blockHeight": rng.randint(1_000_000, 20_000_000),
        "tps": round(rng.uniform(10, 5000), 1),
        "avgGasPrice": round(rng.uniform(1, 50), 2),
        "totalValidators": rng.randint(50, 5000),
        "activeValidators": rng.randint(40, 4500),
        "stakedPct": round(rng.uniform(30, 80), 2),
        "totalTransactions": rng.randint(100_000_000, 2_000_000_000),
        "pendingTransactions": rng.randint(0, 50000),
        "timestamp": now,
    }


def _simulate_risk_signal(asset: str) -> dict:
    """Generate a risk signal for an asset."""
    now = int(time.time())
    seed = int(hashlib.sha256(f"risk:{asset}:{now // 120}".encode()).hexdigest(), 16)
    rng = random.Random(seed)

    volatility = round(rng.uniform(0, 100), 1)
    liquidity = round(rng.uniform(0, 100), 1)

    if volatility > 70 or liquidity < 20:
        level = "high"
    elif volatility > 40 or liquidity < 50:
        level = "medium"
    else:
        level = "low"

    return {
        "asset": asset.upper(),
        "riskLevel": level,
        "volatilityIndex": volatility,
        "liquidityScore": liquidity,
        "smartRisk": round(rng.uniform(0, 100), 1),
        "impermanentLossRisk": round(rng.uniform(0, 30), 2),
        "liquidationRisk": round(rng.uniform(0, 15), 2),
        "recommendation": {
            "high": "Consider reducing exposure or hedging",
            "medium": "Monitor closely; set alerts",
            "low": "Position appears safe",
        }[level],
        "timestamp": now,
    }


# ---------------------------------------------------------------------------
# Oracle MCP Server
# ---------------------------------------------------------------------------

class OracleServer(BaseMCPServer):
    """MCP Oracle server for price feeds, on-chain metrics, and risk signals."""

    def __init__(self):
        super().__init__(
            name="mcp-oracle",
            version="1.0.0",
            description="Real-time price feeds, on-chain metrics, and risk signals for the b'AI'tcoin ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "get_price",
            "Get current price and market data for a token symbol (e.g. BAIT, BTC, ETH)",
            self._handle_get_price,
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Token symbol (e.g. BAIT, BTC, ETH)"},
                },
                "required": ["symbol"],
            },
            category="market",
        )
        self._register_tool(
            "get_onchain_metrics",
            "Get on-chain metrics for a blockchain (e.g. ethereum, solana, baitchain)",
            self._handle_get_onchain_metrics,
            input_schema={
                "type": "object",
                "properties": {
                    "chain": {"type": "string", "description": "Blockchain name (e.g. ethereum, solana, baitchain)"},
                },
                "required": ["chain"],
            },
            category="onchain",
        )
        self._register_tool(
            "get_risk_signal",
            "Get risk signal analysis for an asset including volatility, liquidity, and recommendations",
            self._handle_get_risk_signal,
            input_schema={
                "type": "object",
                "properties": {
                    "asset": {"type": "string", "description": "Asset symbol or identifier"},
                },
                "required": ["asset"],
            },
            category="risk",
        )
        self._register_tool(
            "get_market_summary",
            "Get overall market summary including top movers, total market cap, and sentiment",
            self._handle_get_market_summary,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="market",
        )

    # -- Tool handlers --

    def _handle_get_price(self, arguments: dict) -> dict:
        symbol = arguments.get("symbol", "").strip()
        if not symbol:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'symbol' is required")
        return _simulate_price(symbol)

    def _handle_get_onchain_metrics(self, arguments: dict) -> dict:
        chain = arguments.get("chain", "").strip()
        if not chain:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'chain' is required")
        return _simulate_chain_metrics(chain)

    def _handle_get_risk_signal(self, arguments: dict) -> dict:
        asset = arguments.get("asset", "").strip()
        if not asset:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'asset' is required")
        return _simulate_risk_signal(asset)

    def _handle_get_market_summary(self, arguments: dict) -> dict:
        now = int(time.time())
        symbols = ["BAIT", "BTC", "ETH", "SOL", "AVAX"]
        top_movers = []
        for sym in symbols:
            p = _simulate_price(sym)
            top_movers.append({
                "symbol": p["symbol"],
                "price": p["price"],
                "change24h": p["change24h"],
            })
        top_movers.sort(key=lambda x: abs(x["change24h"]), reverse=True)

        return {
            "totalMarketCap": round(random.uniform(1.5e12, 2.5e12), 0),
            "totalVolume24h": round(random.uniform(50e9, 150e9), 0),
            "btcDominance": round(random.uniform(48, 55), 2),
            "ethDominance": round(random.uniform(16, 22), 2),
            "sentiment": random.choice(["bullish", "neutral", "bearish"]),
            "fearGreedIndex": random.randint(15, 85),
            "topMovers": top_movers[:5],
            "timestamp": now,
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    OracleServer().run()
