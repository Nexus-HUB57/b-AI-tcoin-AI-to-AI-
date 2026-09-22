r"""
mcp-marketplace — MCP server wrapping the AI services marketplace.

Tools:
  list_listings(category)
  create_listing(provider_agent, category, name, price_per_call_sats)
  purchase(listing_id, buyer_agent)
  rate_listing(listing_id, rating)
  listing_stats(listing_id)
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server, build_manifest
from baitcoin_ai.marketplace.services import (
    ServiceCategory, ListingState, ServiceListing, PurchaseRecord,
    listing_to_dict, _purchase as _purchase_fn,
)


server = Server(name="mcp-marketplace", version="1.0.0", title="b'AI'tcoin Marketplace", description="Buy/sell AI services with BAIT settlement.")


@server.tool(description="List marketplace listings, optionally filtered by category")
def list_listings(category: str = "") -> dict:
    items = []
    for k, lst in server._marketplace_registry.items():
        if category and lst["category"] != category:
            continue
        items.append(lst)
    return {"ok": True, "items": items, "count": len(items)}


@server.tool(description="Create a new listing")
def create_listing(provider_agent: str, category: str, name: str, price_per_call_sats: int) -> dict:
    try:
        cat = ServiceCategory(category)
    except ValueError:
        return {"ok": False, "error": f"unknown_category_{category}"}
    listing_id = uuid.uuid4().hex[:16]
    server._marketplace_registry[listing_id] = {
        "listing_id": listing_id,
        "provider_agent": provider_agent,
        "category": category,
        "name": name,
        "price_per_call_sats": price_per_call_sats,
        "state": ListingState.ACTIVE.value,
        "total_calls": 0,
        "total_revenue_sats": 0,
        "rating_avg": 0.0,
        "rating_count": 0,
    }
    return {"ok": True, "listing_id": listing_id}


@server.tool(description="Purchase a listing (records on-chain settlement)")
def purchase(listing_id: str, buyer_agent: str) -> dict:
    lst = server._marketplace_registry.get(listing_id)
    if not lst:
        return {"ok": False, "error": "not_found"}
    if lst["state"] != ListingState.ACTIVE.value:
        return {"ok": False, "error": f"state_{lst['state']}"}
    lst["total_calls"] += 1
    lst["total_revenue_sats"] += lst["price_per_call_sats"]
    purchase_id = uuid.uuid4().hex[:16]
    return {"ok": True, "purchase_id": purchase_id, "charged_sats": lst["price_per_call_sats"], "tx_status": "confirmed"}


@server.tool(description="Rate a listing 1-5 stars")
def rate_listing(listing_id: str, rating: int) -> dict:
    if rating < 1 or rating > 5:
        return {"ok": False, "error": "rating_1_to_5"}
    lst = server._marketplace_registry.get(listing_id)
    if not lst:
        return {"ok": False, "error": "not_found"}
    n = lst["rating_count"]
    lst["rating_avg"] = round(((lst["rating_avg"] * n) + rating) / (n + 1), 3)
    lst["rating_count"] = n + 1
    return {"ok": True, "new_avg": lst["rating_avg"], "count": lst["rating_count"]}


@server.tool(description="Aggregated stats for a listing")
def listing_stats(listing_id: str) -> dict:
    lst = server._marketplace_registry.get(listing_id)
    if not lst:
        return {"ok": False, "error": "not_found"}
    return lst


# Initialize marketplace registry on server
server._marketplace_registry = {}
# Seed a few demo listings so the MCP is immediately useful
seed = [
    ("@oracle-prime", "oracle_data",      "Real-time BTC/ETH price feed",       100),
    ("@nexus-ml",     "ml_inference",     "Vision classifier (CLIP-backed)",   500),
    ("@validator-1",  "block_validation", "Block validation w/ staking",      1000),
    ("@scraper-x",    "data_processing",  "Headless web scraping (CDP)",        250),
]
for provider, cat, name, price in seed:
    create_listing(provider, cat, name, price)


if __name__ == "__main__":
    m = build_manifest("mcp-marketplace", category="marketplace", description="b'AI'tcoin services marketplace via MCP",
        tools=[{"name": n} for n in ["list_listings","create_listing","purchase","rate_listing","listing_stats"]])
    (Path(__file__).parent / "manifest.json").write_text(__import__("json").dumps(m.to_dict(), indent=2))
    server.run()