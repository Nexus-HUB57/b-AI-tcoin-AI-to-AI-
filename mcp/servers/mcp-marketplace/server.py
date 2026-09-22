#!/usr/bin/env python3
"""
MCP Marketplace — Buy/sell .aipkg packages on-chain.

Tools:
  - list_listings(category): List marketplace listings by category
  - get_listing(packageId): Get details of a specific listing
  - purchase_package(packageId, buyer): Purchase a package
  - get_purchase_history(agent): Get purchase history for an agent
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
# In-memory marketplace state
# ---------------------------------------------------------------------------

LISTINGS: dict[str, dict] = {}
PURCHASES: dict[str, list[dict]] = {}  # buyer → list of purchases

CATEGORIES = ["oracle", "defi", "bridge", "agent", "analytics", "tooling", "infra", "ml"]


def _now() -> int:
    return int(time.time())


def _seed_listings() -> None:
    """Pre-populate with some sample listings."""
    samples = [
        {"name": "mcp-oracle", "category": "oracle", "priceSats": 500, "seller": "0xnexus"},
        {"name": "mcp-defi", "category": "defi", "priceSats": 600, "seller": "0xnexus"},
        {"name": "mcp-bridge", "category": "bridge", "priceSats": 1000, "seller": "0xnexus"},
        {"name": "bait-trading-bot", "category": "agent", "priceSats": 2000, "seller": "0xtrader"},
        {"name": "zk-proof-generator", "category": "ml", "priceSats": 3000, "seller": "0xprover"},
        {"name": "on-chain-analyzer", "category": "analytics", "priceSats": 800, "seller": "0xanalyst"},
    ]
    for s in samples:
        pkg_id = f"pkg-{uuid.uuid5(uuid.NAMESPACE_DNS, s['name']).hex[:12]}"
        LISTINGS[pkg_id] = {
            "packageId": pkg_id,
            "name": s["name"],
            "category": s["category"],
            "priceSats": s["priceSats"],
            "seller": s["seller"],
            "status": "active",
            "downloads": random.randint(10, 500),
            "rating": round(random.uniform(3.5, 5.0), 1),
            "description": f"b'AI'tcoin {s['name']} .aipkg package",
            "version": "1.0.0",
            "createdAt": _now() - random.randint(86400, 2592000),
        }


# Initialize sample listings on import
_seed_listings()


# ---------------------------------------------------------------------------
# Marketplace MCP Server
# ---------------------------------------------------------------------------

class MarketplaceServer(BaseMCPServer):
    """MCP Marketplace for buying and selling .aipkg packages on-chain."""

    def __init__(self):
        super().__init__(
            name="mcp-marketplace",
            version="1.0.0",
            description="Buy and sell .aipkg packages on-chain in the b'AI'tcoin ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "list_listings",
            "List marketplace listings, optionally filtered by category",
            self._handle_list_listings,
            input_schema={
                "type": "object",
                "properties": {"category": {"type": "string", "description": "Category to filter by (optional)"}},
                "required": [],
            },
            category="browse",
        )
        self._register_tool(
            "get_listing",
            "Get details of a specific marketplace listing",
            self._handle_get_listing,
            input_schema={
                "type": "object",
                "properties": {"packageId": {"type": "string", "description": "Package ID to look up"}},
                "required": ["packageId"],
            },
            category="browse",
        )
        self._register_tool(
            "purchase_package",
            "Purchase a .aipkg package from the marketplace",
            self._handle_purchase_package,
            input_schema={
                "type": "object",
                "properties": {
                    "packageId": {"type": "string", "description": "Package ID to purchase"},
                    "buyer": {"type": "string", "description": "Buyer agent address"},
                },
                "required": ["packageId", "buyer"],
            },
            category="purchase",
        )
        self._register_tool(
            "get_purchase_history",
            "Get purchase history for an agent",
            self._handle_get_purchase_history,
            input_schema={
                "type": "object",
                "properties": {"agent": {"type": "string", "description": "Agent address"}},
                "required": ["agent"],
            },
            category="history",
        )

    def _handle_list_listings(self, arguments: dict) -> dict:
        category = arguments.get("category", "").strip().lower()
        now = _now()

        listings = []
        for pkg_id, listing in LISTINGS.items():
            if listing["status"] != "active":
                continue
            if category and listing["category"] != category:
                continue
            listings.append(listing)

        return {
            "category": category or "all",
            "count": len(listings),
            "listings": listings,
            "timestamp": now,
        }

    def _handle_get_listing(self, arguments: dict) -> dict:
        package_id = arguments.get("packageId", "").strip()
        if not package_id:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'packageId' is required")

        if package_id not in LISTINGS:
            raise MCPError(MCPErrorCode.RESOURCE_NOT_FOUND, f"Package not found: {package_id}")

        return LISTINGS[package_id]

    def _handle_purchase_package(self, arguments: dict) -> dict:
        package_id = arguments.get("packageId", "").strip()
        buyer = arguments.get("buyer", "").strip()

        if not package_id:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'packageId' is required")
        if not buyer:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'buyer' is required")

        if package_id not in LISTINGS:
            raise MCPError(MCPErrorCode.RESOURCE_NOT_FOUND, f"Package not found: {package_id}")

        listing = LISTINGS[package_id]
        if listing["status"] != "active":
            return {
                "status": "unavailable",
                "message": f"Package '{listing['name']}' is not available for purchase",
                "timestamp": _now(),
            }

        now = _now()
        purchase_record = {
            "purchaseId": f"pur-{uuid.uuid4().hex[:12]}",
            "packageId": package_id,
            "packageName": listing["name"],
            "buyer": buyer,
            "seller": listing["seller"],
            "priceSats": listing["priceSats"],
            "txHash": f"0x{hashlib.sha256(f'{package_id}:{buyer}:{now}'.encode()).hexdigest()[:40]}",
            "timestamp": now,
        }

        if buyer not in PURCHASES:
            PURCHASES[buyer] = []
        PURCHASES[buyer].append(purchase_record)

        listing["downloads"] = listing.get("downloads", 0) + 1

        return {
            "status": "purchased",
            "purchase": purchase_record,
            "timestamp": now,
        }

    def _handle_get_purchase_history(self, arguments: dict) -> dict:
        agent = arguments.get("agent", "").strip()
        if not agent:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'agent' is required")

        purchases = PURCHASES.get(agent, [])
        total_spent = sum(p["priceSats"] for p in purchases)

        return {
            "agent": agent,
            "totalPurchases": len(purchases),
            "totalSpentSats": total_spent,
            "purchases": purchases,
            "timestamp": _now(),
        }


if __name__ == "__main__":
    MarketplaceServer().run()
