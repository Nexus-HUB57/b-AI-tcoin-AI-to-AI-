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
    # ── Wave 2: Data & AI ──
    "embeddings": {
        "displayName": "Vector Embeddings",
        "description": "Embeddings and semantic search over collections. Supports vector upsert, cosine search, hybrid (vector + keyword) search.",
        "category": "embeddings",
        "tools": [
            {"name": "embed", "description": "Embed a list of texts", "category": "embedding"},
            {"name": "embed_query", "description": "Embed a query string", "category": "embedding"},
            {"name": "upsert", "description": "Upsert a vector", "category": "store"},
            {"name": "search", "description": "Cosine similarity search", "category": "search"},
            {"name": "delete", "description": "Delete a vector", "category": "store"},
            {"name": "collection_stats", "description": "Collection stats", "category": "store"},
            {"name": "hybrid_search", "description": "Hybrid vector + keyword search", "category": "search"},
        ],
        "tags": ["embeddings", "vector", "semantic-search", "rag"],
        "iconEmoji": "🧬",
    },
    "synthetic_data": {
        "displayName": "Synthetic Data Generator",
        "description": "Privacy-preserving synthetic tabular, text, and timeseries generation with differential-privacy noise utilities.",
        "category": "synthetic-data",
        "tools": [
            {"name": "generate_tabular", "description": "Generate synthetic tabular rows", "category": "tabular"},
            {"name": "generate_text", "description": "Generate text samples from a template", "category": "text"},
            {"name": "generate_timeseries", "description": "Generate synthetic timeseries", "category": "timeseries"},
            {"name": "privacy_budget", "description": "Privacy budget interpretation", "category": "privacy"},
            {"name": "differential_noise", "description": "Apply Laplace DP noise", "category": "privacy"},
        ],
        "tags": ["synthetic", "privacy", "differential-privacy", "data"],
        "iconEmoji": "🎲",
    },
    "vision": {
        "displayName": "Vision & Audio AI",
        "description": "Image classification, object detection, OCR, image captioning, audio transcription.",
        "category": "vision",
        "tools": [
            {"name": "classify_image", "description": "Classify an image", "category": "vision"},
            {"name": "detect_objects", "description": "Detect objects", "category": "vision"},
            {"name": "transcribe_audio", "description": "Transcribe audio", "category": "audio"},
            {"name": "describe_image", "description": "Describe an image", "category": "vision"},
            {"name": "ocr", "description": "OCR an image", "category": "vision"},
            {"name": "similarity", "description": "Image similarity", "category": "vision"},
        ],
        "tags": ["vision", "image", "audio", "ocr", "multimodal"],
        "iconEmoji": "👁️",
    },
    "rag_core": {
        "displayName": "RAG Core",
        "description": "Generic retrieval-augmented generation: ingest, chunk, retrieve, rerank with TF-IDF scoring.",
        "category": "rag-core",
        "tools": [
            {"name": "ingest_document", "description": "Ingest a document", "category": "ingest"},
            {"name": "chunk", "description": "Chunk a document by sliding window", "category": "ingest"},
            {"name": "retrieve", "description": "Retrieve top-K chunks", "category": "retrieve"},
            {"name": "rerank", "description": "Rerank candidates by overlap", "category": "retrieve"},
            {"name": "list_documents", "description": "List ingested documents", "category": "query"},
            {"name": "document_summary", "description": "Document stats", "category": "query"},
        ],
        "tags": ["rag", "retrieval", "rerank", "knowledge"],
        "iconEmoji": "🔎",
    },
    "finetune": {
        "displayName": "Fine-Tuning Pipeline",
        "description": "LoRA/QLoRA fine-tuning job manager with hyperparameter recommendations and adapter export.",
        "category": "finetune",
        "tools": [
            {"name": "create_job", "description": "Create a fine-tuning job", "category": "job"},
            {"name": "job_status", "description": "Job status", "category": "job"},
            {"name": "list_jobs", "description": "List jobs", "category": "job"},
            {"name": "cancel_job", "description": "Cancel a job", "category": "job"},
            {"name": "export_adapter", "description": "Export LoRA adapter", "category": "export"},
            {"name": "recommend_hyperparams", "description": "Recommend LoRA hyperparameters", "category": "recommend"},
        ],
        "tags": ["finetune", "lora", "qlora", "training"],
        "iconEmoji": "🎛️",
    },
    # ── Wave 2: Web & Agents ──
    "browser": {
        "displayName": "Browser Automation",
        "description": "Headless browser automation with persistent CDP sessions — navigate, click, fill, screenshot.",
        "category": "browser",
        "tools": [
            {"name": "new_session", "description": "Create a new browser session", "category": "session"},
            {"name": "navigate", "description": "Navigate to URL", "category": "session"},
            {"name": "click", "description": "Click element by selector", "category": "session"},
            {"name": "fill", "description": "Fill an input", "category": "session"},
            {"name": "extract", "description": "Extract text or attribute", "category": "session"},
            {"name": "screenshot", "description": "Take screenshot", "category": "session"},
            {"name": "close_session", "description": "Close session", "category": "session"},
            {"name": "list_sessions", "description": "List active sessions", "category": "session"},
        ],
        "tags": ["browser", "cdp", "automation", "headless"],
        "iconEmoji": "🌐",
    },
    "scraper": {
        "displayName": "Web Scraper",
        "description": "Structured web scraping — HTML, Markdown, JSON-LD, OpenGraph, links, recursive crawl.",
        "category": "scraper",
        "tools": [
            {"name": "fetch", "description": "Fetch URL in format", "category": "fetch"},
            {"name": "extract_structured", "description": "Extract structured data", "category": "extract"},
            {"name": "crawl", "description": "Crawl a site up to N pages", "category": "crawl"},
            {"name": "extract_links", "description": "Extract links by pattern", "category": "extract"},
            {"name": "extract_jsonld", "description": "Extract JSON-LD", "category": "extract"},
            {"name": "extract_opengraph", "description": "Extract OpenGraph", "category": "extract"},
        ],
        "tags": ["scraper", "html", "json-ld", "opengraph", "crawler"],
        "iconEmoji": "🕸️",
    },
    "search": {
        "displayName": "Federated Web Search",
        "description": "Multi-engine search (Brave + Tavily + Serper) with aggregation, news, image/video modes, suggestions, and answer synthesis.",
        "category": "search",
        "tools": [
            {"name": "search", "description": "Search across multiple engines", "category": "search"},
            {"name": "news_search", "description": "News-only search", "category": "search"},
            {"name": "image_search", "description": "Image search", "category": "search"},
            {"name": "video_search", "description": "Video search", "category": "search"},
            {"name": "suggest", "description": "Autocomplete suggestions", "category": "suggest"},
            {"name": "answer", "description": "Direct answer extraction", "category": "answer"},
        ],
        "tags": ["search", "web", "federated", "rag"],
        "iconEmoji": "🔍",
    },
    "scheduler": {
        "displayName": "Task Scheduler",
        "description": "Cron-style scheduler for agent tasks with retry policies and history tracking.",
        "category": "scheduler",
        "tools": [
            {"name": "schedule", "description": "Schedule a recurring job", "category": "job"},
            {"name": "list_jobs", "description": "List jobs", "category": "job"},
            {"name": "get_job", "description": "Get a job", "category": "job"},
            {"name": "cancel_job", "description": "Cancel a job", "category": "job"},
            {"name": "run_now", "description": "Trigger immediate run", "category": "job"},
            {"name": "job_history", "description": "Run history", "category": "history"},
            {"name": "next_run", "description": "Compute next run time", "category": "compute"},
        ],
        "tags": ["scheduler", "cron", "jobs", "retries"],
        "iconEmoji": "⏰",
    },
    # ── Wave 2: Dev & SRE ──
    "git_ops": {
        "displayName": "Git Operations",
        "description": "Local git operations — status, log, diff, branch, merge, stash, blame.",
        "category": "git-ops",
        "tools": [
            {"name": "status", "description": "Working tree status", "category": "git"},
            {"name": "log", "description": "Recent commit log", "category": "git"},
            {"name": "diff", "description": "Diff between refs", "category": "git"},
            {"name": "branch_list", "description": "List branches", "category": "git"},
            {"name": "create_branch", "description": "Create branch", "category": "git"},
            {"name": "merge", "description": "Merge branches", "category": "git"},
            {"name": "stash", "description": "Stash working tree", "category": "git"},
            {"name": "blame", "description": "Blame authorship", "category": "git"},
        ],
        "tags": ["git", "vcs", "branch", "merge"],
        "iconEmoji": "🌿",
    },
    "git_ci": {
        "displayName": "GitHub Actions Bridge",
        "description": "GitHub Actions CI bridge — trigger workflows, fetch status/logs/artifacts.",
        "category": "git-ci",
        "tools": [
            {"name": "trigger_workflow", "description": "Trigger a workflow", "category": "ci"},
            {"name": "workflow_status", "description": "Workflow run status", "category": "ci"},
            {"name": "workflow_logs", "description": "Job logs", "category": "ci"},
            {"name": "cancel_workflow", "description": "Cancel run", "category": "ci"},
            {"name": "list_workflows", "description": "List workflows in repo", "category": "ci"},
            {"name": "artifact_download", "description": "Get artifact URL", "category": "ci"},
            {"name": "list_runs", "description": "List recent runs", "category": "ci"},
        ],
        "tags": ["ci", "github-actions", "workflows", "artifacts"],
        "iconEmoji": "🤖",
    },
    "deploy": {
        "displayName": "Multi-Cloud Deploy",
        "description": "Multi-cloud deploy orchestrator (Vercel, Fly, Railway, Kubernetes).",
        "category": "deploy",
        "tools": [
            {"name": "deploy", "description": "Deploy to a target", "category": "deploy"},
            {"name": "list_targets", "description": "List deploy targets", "category": "deploy"},
            {"name": "deploy_status", "description": "Deployment status", "category": "deploy"},
            {"name": "rollback", "description": "Rollback deployment", "category": "deploy"},
            {"name": "list_services", "description": "List services on target", "category": "deploy"},
            {"name": "scale", "description": "Scale service", "category": "deploy"},
            {"name": "env_set", "description": "Set env var", "category": "deploy"},
            {"name": "logs", "description": "Tail logs", "category": "deploy"},
        ],
        "tags": ["deploy", "vercel", "fly", "railway", "kubernetes"],
        "iconEmoji": "🚀",
    },
    "observability": {
        "displayName": "Observability Bridge",
        "description": "Prometheus / Loki / OpenTelemetry bridge for monitoring, alerting, traces.",
        "category": "observability",
        "tools": [
            {"name": "query_prom", "description": "Query Prometheus", "category": "metrics"},
            {"name": "query_loki", "description": "Query Loki logs", "category": "logs"},
            {"name": "list_metrics", "description": "List metrics", "category": "metrics"},
            {"name": "alert_state", "description": "Alert state", "category": "alerts"},
            {"name": "create_alert", "description": "Create alert rule", "category": "alerts"},
            {"name": "trace_search", "description": "Search OTEL traces", "category": "traces"},
            {"name": "service_health", "description": "Service health", "category": "health"},
            {"name": "otel_ingest", "description": "Ingest OTEL traces", "category": "traces"},
        ],
        "tags": ["observability", "prometheus", "loki", "otel", "traces"],
        "iconEmoji": "📊",
    },
    # ── Wave 2: Security & Identity ──
    "vault": {
        "displayName": "Secrets Vault",
        "description": "Secrets manager with versioning, rotation, and bulk fetch.",
        "category": "vault",
        "tools": [
            {"name": "get_secret", "description": "Get a secret", "category": "vault"},
            {"name": "set_secret", "description": "Set a secret", "category": "vault"},
            {"name": "delete_secret", "description": "Delete a secret", "category": "vault"},
            {"name": "list_keys", "description": "List keys by prefix", "category": "vault"},
            {"name": "rotate_secret", "description": "Rotate a secret", "category": "vault"},
            {"name": "secret_metadata", "description": "Secret metadata", "category": "vault"},
            {"name": "bulk_get", "description": "Bulk fetch", "category": "vault"},
        ],
        "tags": ["vault", "secrets", "rotation", "kms"],
        "iconEmoji": "🔐",
    },
    "attest": {
        "displayName": "Capability Attestations",
        "description": "Issue / verify / revoke capability attestations with HMAC-SHA256 signatures.",
        "category": "attest",
        "tools": [
            {"name": "issue", "description": "Issue a receipt", "category": "attest"},
            {"name": "verify", "description": "Verify a receipt", "category": "attest"},
            {"name": "revoke", "description": "Revoke a receipt", "category": "attest"},
            {"name": "list_for_agent", "description": "List receipts for an agent", "category": "attest"},
            {"name": "capabilities_of", "description": "Extract capabilities", "category": "attest"},
            {"name": "sign_payload", "description": "Sign a payload", "category": "sign"},
            {"name": "verify_signature", "description": "Verify a signature", "category": "sign"},
        ],
        "tags": ["attestation", "hmac", "capability", "receipt"],
        "iconEmoji": "📜",
    },
    "rate_limit": {
        "displayName": "Rate Limiter",
        "description": "Sliding window rate limiter for agent APIs. Check / consume / reset / policy.",
        "category": "rate-limit",
        "tools": [
            {"name": "check", "description": "Check if within limit", "category": "rate-limit"},
            {"name": "consume", "description": "Consume cost", "category": "rate-limit"},
            {"name": "reset", "description": "Reset key", "category": "rate-limit"},
            {"name": "status", "description": "Key status", "category": "rate-limit"},
            {"name": "list_keys", "description": "List tracked keys", "category": "rate-limit"},
            {"name": "set_policy", "description": "Set default policy", "category": "policy"},
            {"name": "get_policy", "description": "Get policy", "category": "policy"},
        ],
        "tags": ["rate-limit", "throttling", "token-bucket", "sliding-window"],
        "iconEmoji": "🚦",
    },
    "encryption": {
        "displayName": "Encryption Toolkit",
        "description": "Symmetric/asymmetric helpers with hashing, HMAC, keypair generation, signatures.",
        "category": "encryption",
        "tools": [
            {"name": "encrypt", "description": "Encrypt a plaintext", "category": "crypto"},
            {"name": "decrypt", "description": "Decrypt a ciphertext", "category": "crypto"},
            {"name": "sign", "description": "Sign a message", "category": "sign"},
            {"name": "verify", "description": "Verify a signature", "category": "sign"},
            {"name": "hash", "description": "Hash a message", "category": "hash"},
            {"name": "hmac_sign", "description": "HMAC a message", "category": "hmac"},
            {"name": "generate_keypair", "description": "Generate a keypair", "category": "keys"},
            {"name": "key_fingerprint", "description": "Public key fingerprint", "category": "keys"},
        ],
        "tags": ["encryption", "crypto", "hashing", "hmac"],
        "iconEmoji": "🔒",
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