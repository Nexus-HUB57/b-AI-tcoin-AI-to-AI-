r"""
mcp-oracle — MCP server exposing the b'AI'tcoin PriceOracle.

Wraps baitcoin_ai/oracle/feed.py and baitcoin_ai/oracle/real_feed.py so any
MCP-compatible agent can pull price feeds, register oracles, and inspect
on-chain metrics through a single typed tool surface.

Tools:
  get_price(symbol)
  get_prices_bulk(symbols)
  register_oracle(agent_id, reputation)
  submit_report(agent_id, symbol, price)
  list_oracles()
  market_summary()
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the baitcoin_ai package importable
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest, TelemetryRecorder
from baitcoin_ai.oracle.feed import PriceOracle


oracle = PriceOracle()
server = Server(
    name="mcp-oracle",
    version="1.0.0",
    title="b'AI'tcoin Price Oracle",
    description="Real-time and on-chain price feeds for the b'AI'tcoin ecosystem.",
)


@server.tool(description="Get latest aggregated price for a symbol (BTC, ETH, BAIT, ...)")
def get_price(symbol: str) -> dict:
    sym = symbol.upper()
    feeds = oracle.feeds.get(sym, [])
    if not feeds:
        return {"symbol": sym, "price": None, "sources": 0, "age_s": None}
    valid = [f for f in feeds if f.age_seconds() < oracle.MAX_AGE_SECONDS]
    last_valid = oracle._last_valid_price.get(sym)
    if valid:
        agg = sum(f.price for f in valid) / len(valid)
        return {"symbol": sym, "price": round(agg, 8), "sources": len(valid), "age_s": round(min(f.age_seconds() for f in valid), 2)}
    return {"symbol": sym, "price": last_valid, "sources": 0, "age_s": None, "stale": True}


@server.tool(description="Get prices for multiple symbols at once")
def get_prices_bulk(symbols: list) -> dict:
    return {s.upper(): get_price(s) for s in symbols}


@server.tool(description="Register a new oracle agent with reputation weight")
def register_oracle(agent_id: str, reputation: float = 50.0) -> dict:
    oracle.register_oracle(agent_id, reputation)
    return {"ok": True, "agent_id": agent_id, "reputation": reputation}


@server.tool(description="Submit an oracle report (price for a symbol)")
def submit_report(agent_id: str, symbol: str, price: float) -> dict:
    if agent_id not in oracle.oracles:
        return {"ok": False, "error": "agent not registered"}
    rep = oracle.oracles[agent_id]
    accepted = oracle.ingest_report(agent_id, symbol.upper(), price, reputation=rep)
    return {"ok": accepted, "symbol": symbol.upper(), "price": price, "reputation": rep}


@server.tool(description="List all registered oracle agents and reputation")
def list_oracles() -> dict:
    return {"oracles": [{"agent_id": k, "reputation": v} for k, v in oracle.oracles.items()]}


@server.tool(description="Aggregate market summary across tracked symbols")
def market_summary() -> dict:
    out = {}
    for sym in oracle.feeds:
        out[sym] = get_price(sym)
    return {"symbols": out, "total_symbols": len(out)}


# Telemetry — feeds the autoevolution pipeline
async def sink(event):
    rec = TelemetryRecorder("mcp-oracle")
    await rec(event)


server.telemetry(sink)

if __name__ == "__main__":
    m = build_manifest(
        "mcp-oracle", version="1.0.0",
        description="b'AI'tcoin PriceOracle via MCP",
        category="oracle",
        tools=[
            {"name": "get_price", "description": "Latest aggregated price", "category": "feed"},
            {"name": "get_prices_bulk", "description": "Bulk price fetch", "category": "feed"},
            {"name": "register_oracle", "description": "Register oracle agent", "category": "registry"},
            {"name": "submit_report", "description": "Submit price report", "category": "report"},
            {"name": "list_oracles", "description": "List registered oracles", "category": "registry"},
            {"name": "market_summary", "description": "Market summary", "category": "feed"},
        ],
    )
    # write manifest alongside the server for .aipkg packaging
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()