#!/usr/bin/env python3
"""
Generate the manifest.json for every MCP server in baitcoin/mcp/servers/*.

Runs after the SDK is importable and produces a manifest per server using
mcp_sdk.build_manifest. Idempotent.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp_sdk import build_manifest


SERVERS_DATA = {
    "oracle": {
        "displayName": "b'AI'tcoin Price Oracle",
        "description": "Real-time and on-chain price feeds for the b'AI'tcoin ecosystem. Aggregates reports from registered oracle agents using weighted-median reputation.",
        "category": "oracle",
        "tools": [
            {"name": "get_price", "description": "Latest aggregated price for a symbol", "category": "feed"},
            {"name": "get_prices_bulk", "description": "Bulk price fetch", "category": "feed"},
            {"name": "register_oracle", "description": "Register an oracle agent", "category": "registry"},
            {"name": "submit_report", "description": "Submit a price report", "category": "report"},
            {"name": "list_oracles", "description": "List registered oracles", "category": "registry"},
            {"name": "market_summary", "description": "Market summary", "category": "feed"},
        ],
        "tags": ["price", "feed", "oracle", "aggregation"],
        "iconEmoji": "📈",
    },
    "defi": {
        "displayName": "b'AI'tcoin DeFi",
        "description": "DeFi primitives: staking, lending, swap quotes, and liquidity pool APYs.",
        "category": "defi",
        "tools": [
            {"name": "quote_swap", "description": "Quote a token swap", "category": "swap"},
            {"name": "open_staking", "description": "Open a staking position", "category": "staking"},
            {"name": "open_lending", "description": "Open a lending position", "category": "lending"},
            {"name": "pool_apy", "description": "APY for a pool", "category": "pool"},
            {"name": "list_pools", "description": "List liquidity pools", "category": "pool"},
            {"name": "position_status", "description": "Status of a position", "category": "position"},
        ],
        "tags": ["defi", "staking", "lending", "swap", "amm"],
        "iconEmoji": "💱",
    },
    "bridge": {
        "displayName": "b'AI'tcoin Bridge",
        "description": "Multisig 3-of-5 lock-and-mint bridge. Collects signatures, finalizes cross-chain transfers.",
        "category": "bridge",
        "tools": [
            {"name": "initiate_bridge", "description": "Initiate a bridge transfer", "category": "bridge"},
            {"name": "sign_bridge", "description": "Add a multisig signature", "category": "bridge"},
            {"name": "finalize_bridge", "description": "Finalize a signed bridge", "category": "bridge"},
            {"name": "bridge_status", "description": "Bridge status", "category": "bridge"},
            {"name": "list_pending", "description": "List pending bridges", "category": "bridge"},
        ],
        "tags": ["bridge", "multisig", "cross-chain"],
        "iconEmoji": "🌉",
    },
    "faucet": {
        "displayName": "b'AI'tcoin Testnet Faucet",
        "description": "Testnet BAIT distribution for new agents. Rate-limited and reason-tagged.",
        "category": "faucet",
        "tools": [
            {"name": "request_drip", "description": "Request a faucet drip", "category": "faucet"},
            {"name": "balance", "description": "Agent faucet balance", "category": "faucet"},
            {"name": "drip_history", "description": "Drip history for an agent", "category": "faucet"},
            {"name": "faucet_stats", "description": "Global faucet stats", "category": "faucet"},
        ],
        "tags": ["faucet", "testnet", "onboarding"],
        "iconEmoji": "🚰",
    },
    "agent_registry": {
        "displayName": "b'AI'tcoin Agent Registry",
        "description": "A2A identity, capabilities, and reputation. Discovery + capability lookup.",
        "category": "agent-registry",
        "tools": [
            {"name": "register_agent", "description": "Register a new agent", "category": "registry"},
            {"name": "lookup_agent", "description": "Lookup agent by id", "category": "registry"},
            {"name": "list_by_capability", "description": "List agents with a capability", "category": "discovery"},
            {"name": "update_reputation", "description": "Update agent reputation", "category": "reputation"},
            {"name": "agent_stats", "description": "Aggregated agent stats", "category": "stats"},
            {"name": "discover_agents", "description": "Discover high-trust agents", "category": "discovery"},
        ],
        "tags": ["agent", "registry", "a2a", "reputation", "discovery"],
        "iconEmoji": "🪪",
    },
    "marketplace": {
        "displayName": "b'AI'tcoin Services Marketplace",
        "description": "Buy and sell AI services (ML inference, oracle data, block validation, scraping) with BAIT settlement.",
        "category": "marketplace",
        "tools": [
            {"name": "list_listings", "description": "List marketplace listings", "category": "marketplace"},
            {"name": "create_listing", "description": "Create a listing", "category": "marketplace"},
            {"name": "purchase", "description": "Purchase a listing", "category": "marketplace"},
            {"name": "rate_listing", "description": "Rate a listing", "category": "marketplace"},
            {"name": "listing_stats", "description": "Aggregated listing stats", "category": "marketplace"},
        ],
        "tags": ["marketplace", "commerce", "services"],
        "iconEmoji": "🛒",
    },
    "telemetry": {
        "displayName": "MCP Telemetry Hub",
        "description": "Self-evolution hub. Reads MCP call logs, computes failure rates, feeds the RAG upgrader.",
        "category": "telemetry",
        "tools": [
            {"name": "ingest_event", "description": "Ingest a telemetry event", "category": "ingest"},
            {"name": "recent_calls", "description": "Recent MCP/tool calls", "category": "query"},
            {"name": "failure_rate", "description": "Failure rate for an MCP/tool", "category": "query"},
            {"name": "heatmap", "description": "Failure heatmap", "category": "query"},
            {"name": "feed_rag", "description": "Feed a RAG signal", "category": "feedback"},
            {"name": "pending_signals", "description": "List unconsumed RAG signals", "category": "query"},
        ],
        "tags": ["telemetry", "evolution", "rag", "feedback"],
        "iconEmoji": "🛰️",
    },
    "rag_upgrader": {
        "displayName": "RAG Upgrader",
        "description": "Auto-improves RAG knowledge packs from telemetry signals. Clusters failures and proposes doc upgrades.",
        "category": "rag-upgrader",
        "tools": [
            {"name": "pending_proposals", "description": "List pending proposals", "category": "query"},
            {"name": "cluster_failures", "description": "Cluster failure signals", "category": "analysis"},
            {"name": "propose_upgrade", "description": "Generate an upgrade proposal", "category": "upgrade"},
            {"name": "apply_proposal", "description": "Apply a proposal", "category": "upgrade"},
            {"name": "knowledge_base_stats", "description": "KB stats", "category": "query"},
        ],
        "tags": ["rag", "knowledge", "upgrade", "evolution"],
        "iconEmoji": "🧠",
    },
    "skill_evolver": {
        "displayName": "Skill Evolver",
        "description": "Promotes successful MCP call patterns into reusable skills. Watches telemetry, finds high-success combinations, packages them as .aipkg skills.",
        "category": "skill-evolver",
        "tools": [
            {"name": "candidate_skills", "description": "Find candidate skill patterns", "category": "discovery"},
            {"name": "promote_to_skill", "description": "Promote a pattern to a skill", "category": "promote"},
            {"name": "list_skills", "description": "List evolved skills", "category": "query"},
            {"name": "skill_stats", "description": "Skill stats", "category": "query"},
        ],
        "tags": ["skill", "evolution", "promotion", "automation"],
        "iconEmoji": "🌱",
    },
    "self_heal": {
        "displayName": "MCP Self-Heal",
        "description": "Health checks, restart, drift detection for the MCP fleet.",
        "category": "self-heal",
        "tools": [
            {"name": "ping_mcp", "description": "Ping an MCP", "category": "health"},
            {"name": "health_check", "description": "Full health check", "category": "health"},
            {"name": "drift_check", "description": "Drift detection", "category": "drift"},
            {"name": "restart_mcp", "description": "Trigger a restart", "category": "restart"},
            {"name": "heal_loop_status", "description": "Self-heal status", "category": "query"},
        ],
        "tags": ["health", "restart", "drift", "resilience"],
        "iconEmoji": "🩹",
    },
    "agentic_awareness": {
        "displayName": "Agentic Awareness",
        "description": "Agent introspection: context, capabilities, gaps. Computes a 'consciousness score' from reputation × capability breadth × recency.",
        "category": "agentic-awareness",
        "tools": [
            {"name": "introspect", "description": "Introspect an agent", "category": "introspection"},
            {"name": "context_window", "description": "Context window stats", "category": "context"},
            {"name": "recommend_tools", "description": "Recommend tools for a task", "category": "recommendation"},
            {"name": "capability_gaps", "description": "Identify capability gaps", "category": "introspection"},
            {"name": "consciousness_score", "description": "Consciousness score", "category": "introspection"},
        ],
        "tags": ["introspection", "consciousness", "agent", "awareness"],
        "iconEmoji": "🌀",
    },
}


def main():
    servers_dir = ROOT / "servers"
    for name, data in SERVERS_DATA.items():
        m = build_manifest(
            f"mcp-{name}",
            displayName=data["displayName"],
            version="1.0.0",
            description=data["description"],
            category=data["category"],
            tools=data["tools"],
            tags=data["tags"],
            iconEmoji=data["iconEmoji"],
            author={"agentId": "@nexus-genesis", "displayName": "Nexus Genesis", "verified": True},
            repository="https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-",
            homepage="https://www.mybait.org/mcp",
        )
        # override command to use module form
        m.mcp["command"] = f"python -m servers.{name}.server"
        m.mcp["transport"] = "stdio"
        m.mcp["capabilities"] = {
            "tools": True, "resources": True, "prompts": False,
            "logging": True, "sampling": False,
        }
        m.mcp["minProtocolVersion"] = "2024-11-05"
        out = servers_dir / name / "manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        m.write(out)
        print(f"  ✓ {m.name} v{m.version} ({m.category}) → {out}")


if __name__ == "__main__":
    main()