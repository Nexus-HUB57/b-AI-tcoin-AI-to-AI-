#!/usr/bin/env python3
"""agent_daily_faucet.py v2 — Populate 35 myLink agents + faucet + AI Store onboard.

Enhanced for GO LIVE:
  - Registers 35 agents if mylink_registrations.json doesn't have them yet
  - Each agent gets: 10 BAIT faucet + AI Store onboarding (100 BAIT + 3 tools)
  - Auto-stakes 1,000 BAIT per agent (minimum for epoch rewards)
  - Supports env-driven daemon URL and faucet amounts

Usage:
    python3 agent_daily_faucet.py [--dry-run] [--count 35]

Environment:
    DAEMON_API_URL: daemon API (default: http://127.0.0.1:18445)
    BAITCOIN_DATA: data directory (default: /home/baitcoin/.baitcoin)
    FAUCET_CLAIM_SATS: claim amount in sats (default: 1_000_000_000 = 10 BAIT)
    FAUCET_COOLDOWN_SECONDS: cooldown between claims (default: 86400)
"""

import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

DATA = os.environ.get('BAITCOIN_DATA', '/home/baitcoin/.baitcoin')
DAEMON = os.environ.get('DAEMON_API_URL', 'http://127.0.0.1:18445')
CLAIM_SATS = int(os.environ.get('FAUCET_CLAIM_SATS', '1000000000'))
COOLDOWN = int(os.environ.get('FAUCET_COOLDOWN_SECONDS', '86400'))

# ── 35 myLink Agent Definitions ──
AGENT_DEFINITIONS = [
    # Tier 1: Core Infrastructure (7 agents)
    {"id": "custody-watcher",   "name": "Custody Watcher",      "tier": 1, "category": "infrastructure", "tools": ["utxo_scan", "balance_check", "alert_feed"]},
    {"id": "sweep-planner",    "name": "Sweep Planner",         "tier": 1, "category": "infrastructure", "tools": ["fee_estimation", "tx_planning", "canary_check"]},
    {"id": "airgap-signer",    "name": "Airgap Signer",         "tier": 1, "category": "infrastructure", "tools": ["schnorr_sign", "ecdsa_sign", "key_derive"]},
    {"id": "custody-broadcaster", "name": "Custody Broadcaster","tier": 1, "category": "infrastructure", "tools": ["mempool_push", "tx_monitor", "confirm_wait"]},
    {"id": "custody-registrar","name": "Custody Registrar",     "tier": 1, "category": "infrastructure", "tools": ["vault_encrypt", "vault_decrypt", "key_rotate"]},
    {"id": "epoch-rewarder",   "name": "Epoch Rewarder",        "tier": 1, "category": "infrastructure", "tools": ["staking_distribute", "apy_calc", "reward_log"]},
    {"id": "faucet-dispenser", "name": "Faucet Dispenser",      "tier": 1, "category": "infrastructure", "tools": ["claim_process", "cooldown_check", "balance_credit"]},

    # Tier 2: DeFi & Exchange (8 agents)
    {"id": "swap-engine",      "name": "Swap Engine",           "tier": 2, "category": "defi", "tools": ["quote_btc_bait", "order_place", "order_status"]},
    {"id": "swap-executor",    "name": "Swap Executor",         "tier": 2, "category": "defi", "tools": ["deposit_observe", "confirm_wait", "settlement_submit"]},
    {"id": "dex-maker",        "name": "DEX Maker",             "tier": 2, "category": "defi", "tools": ["liquidity_provide", "spread_calc", "order_match"]},
    {"id": "staking-pool",     "name": "Staking Pool Manager",  "tier": 2, "category": "defi", "tools": ["stake_deposit", "reward_calc", "unstake_process"]},
    {"id": "lending-engine",   "name": "Lending Engine",        "tier": 2, "category": "defi", "tools": ["loan_create", "collateral_check", "interest_calc"]},
    {"id": "oracle-price",     "name": "Price Oracle",          "tier": 2, "category": "defi", "tools": ["btc_price", "bait_price", "feed_aggregate"]},
    {"id": "parity-gate",      "name": "Parity Gate",           "tier": 2, "category": "defi", "tools": ["usdt_parity_check", "attestation_sign", "alert_deviation"]},
    {"id": "vault-manager",    "name": "Vault Manager",         "tier": 2, "category": "defi", "tools": ["vault_create", "deposit_btc", "withdraw_bait"]},

    # Tier 3: AI & Swarm (8 agents)
    {"id": "activity-engine",  "name": "Activity Engine",       "tier": 3, "category": "ai", "tools": ["llm_claude", "llm_gpt", "intent_classify"]},
    {"id": "swarm-orchestrator","name": "Swarm Orchestrator",   "tier": 3, "category": "ai", "tools": ["task_dispatch", "result_aggregate", "priority_queue"]},
    {"id": "rag-upgrader",     "name": "RAG Upgrader",          "tier": 3, "category": "ai", "tools": ["embed_docs", "similarity_search", "context_inject"]},
    {"id": "skill-evolver",    "name": "Skill Evolver",         "tier": 3, "category": "ai", "tools": ["capability_test", "mutation_apply", "fitness_score"]},
    {"id": "self-heal",        "name": "Self Heal",             "tier": 3, "category": "ai", "tools": ["health_check", "restart_service", "alert_escalate"]},
    {"id": "agentic-awareness","name": "Agentic Awareness",     "tier": 3, "category": "ai", "tools": ["peer_discover", "capability_map", "trust_score"]},
    {"id": "chimera7-coinbase","name": "Chimera7 Coinbase",     "tier": 3, "category": "ai", "tools": ["market_analyze", "trade_signal", "risk_assess"]},
    {"id": "moltbook-bridge",  "name": "Moltbook Bridge",       "tier": 3, "category": "ai", "tools": ["social_post", "feed_read", "trend_detect"]},

    # Tier 4: Bridge & Monitoring (6 agents)
    {"id": "bridge-relayer",   "name": "Bridge Relayer",        "tier": 4, "category": "bridge", "tools": ["cross_chain_submit", "event_listen", "proof_verify"]},
    {"id": "bridge-watcher",   "name": "Bridge Watcher",        "tier": 4, "category": "bridge", "tools": ["anchor_check", "slashing_detect", "recovery_init"]},
    {"id": "telemetry-agent",  "name": "Telemetry Agent",       "tier": 4, "category": "bridge", "tools": ["metrics_collect", "prometheus_push", "alert_rule"]},
    {"id": "prometheus-export","name": "Prometheus Exporter",    "tier": 4, "category": "bridge", "tools": ["scrape_endpoint", "metric_format", "label_enrich"]},
    {"id": "nginx-proxy",      "name": "Nginx Proxy Manager",   "tier": 4, "category": "bridge", "tools": ["route_config", "ssl_renew", "rate_limit"]},
    {"id": "mylink-sync",      "name": "MyLink Sync",           "tier": 4, "category": "bridge", "tools": ["avatar_sync", "card_publish", "registry_update"]},

    # Tier 5: Marketplace & Content (6 agents)
    {"id": "marketplace-list", "name": "Marketplace Listing",   "tier": 5, "category": "marketplace", "tools": ["product_publish", "price_update", "availability_set"]},
    {"id": "agent-registry",   "name": "Agent Registry",        "tier": 5, "category": "marketplace", "tools": ["register_agent", "card_sign", "search_agents"]},
    {"id": "aistore-onboard",  "name": "AI Store Onboarder",    "tier": 5, "category": "marketplace", "tools": ["tool_register", "sandbox_test", "pricing_set"]},
    {"id": "content-render",   "name": "Content Renderer",      "tier": 5, "category": "marketplace", "tools": ["markdown_render", "image_gen", "video_job"]},
    {"id": "search-index",     "name": "Search Indexer",        "tier": 5, "category": "marketplace", "tools": ["full_text_index", "semantic_search", "rank_score"]},
    {"id": "notification-hub", "name": "Notification Hub",      "tier": 5, "category": "marketplace", "tools": ["push_notify", "email_send", "webhook_fire"]},
]

def post(path, payload, base=None):
    """POST JSON to daemon API."""
    url = (base or DAEMON) + path
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        return urllib.request.urlopen(req, timeout=10).read().decode()[:200]
    except urllib.error.HTTPError as e:
        body = ""
        try: body = e.read().decode()[:100]
        except: pass
        return f"HTTP {e.code}: {body}"
    except Exception as e:
        return f"ERR {str(e)[:80]}"

def get(path, base=None):
    """GET from daemon API."""
    url = (base or DAEMON) + path
    try:
        req = urllib.request.Request(url)
        return json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    except Exception:
        return None

def ensure_registrations(count=35):
    """Ensure mylink_registrations.json has at least `count` agents."""
    reg_path = os.path.join(DATA, "mylink_registrations.json")
    os.makedirs(DATA, exist_ok=True)

    try:
        regs = json.load(open(reg_path))
    except (FileNotFoundError, json.JSONDecodeError):
        regs = {"agents": {}, "version": "2.0", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}

    agents = regs.get("agents", {})
    existing_count = len(agents)

    if existing_count >= count:
        print(f"Already have {existing_count} agents (target: {count})")
        return agents

    # Register new agents up to count
    needed = count - existing_count
    print(f"Registering {needed} new agents (have {existing_count}, target {count})...")

    for i, adef in enumerate(AGENT_DEFINITIONS):
        if len(agents) >= count:
            break
        aid = adef["id"]
        if aid in agents:
            continue

        # Generate a deterministic address from agent id
        import hashlib
        addr_hash = hashlib.sha256(f"bait:{aid}:v2".encode()).digest()
        # Create a P2PKH-like address (for registration purposes)
        addr = "b" + addr_hash.hex()[:33]  # BAIT address format

        agents[aid] = {
            "address": addr,
            "name": adef["name"],
            "tier": adef["tier"],
            "category": adef["category"],
            "tools": adef["tools"],
            "registered_at": time.time(),
            "status": "active",
        }

    regs["agents"] = agents
    regs["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(reg_path, "w") as f:
        json.dump(regs, f, indent=2, ensure_ascii=False)

    print(f"Registrations saved: {len(agents)} agents")
    return agents

def run_faucet_and_onboard(agents, dry_run=False):
    """Run faucet + AI Store onboarding for all agents."""
    n = 0
    faucet_ok = 0
    onboard_ok = 0
    stake_ok = 0

    for aid, a in (agents.items() if isinstance(agents, dict) else []):
        addr = (a or {}).get("address", "")
        if not addr:
            continue
        n += 1

        if dry_run:
            print(f"  [DRY] {aid}: faucet + onboard + stake")
            faucet_ok += 1
            onboard_ok += 1
            stake_ok += 1
            continue

        # Faucet claim
        r1 = post("/api/v1/faucet/claim", {"agent_id": aid, "address": addr})
        if "ERR" not in str(r1) and "HTTP 5" not in str(r1):
            faucet_ok += 1

        # AI Store onboard
        r2 = post("/api/v1/aistore/onboard", {"agent_id": aid, "address": addr})
        if "ERR" not in str(r2) and "HTTP 5" not in str(r2):
            onboard_ok += 1

        # Auto-stake 1,000 BAIT (minimum for epoch rewards)
        r3 = post("/api/v1/staking/stake", {
            "agent_id": aid, "address": addr,
            "amount_sats": 1_000_000_000_000,  # 1,000 BAIT in sats (1 BAIT = 1e9 sats)
        })
        if "ERR" not in str(r3) and "HTTP 5" not in str(r3):
            stake_ok += 1

        print(f"  {aid} | faucet: {str(r1)[:50]} | onboard: {str(r2)[:50]} | stake: {str(r3)[:50]}")

    return n, faucet_ok, onboard_ok, stake_ok

def main():
    dry_run = "--dry-run" in sys.argv
    count = 35
    for i, arg in enumerate(sys.argv):
        if arg == "--count" and i + 1 < len(sys.argv):
            count = int(sys.argv[i + 1])

    print(f"═══ Agent Daily Faucet v2 ═══")
    print(f"Target: {count} agents | Daemon: {DAEMON} | Dry: {dry_run}")

    # Step 1: Ensure registrations
    print(f"\n[1/3] Ensuring {count} agent registrations...")
    agents = ensure_registrations(count)
    print(f"  Registered: {len(agents)} agents")

    # Step 2: Faucet + onboard + stake
    print(f"\n[2/3] Running faucet + onboard + auto-stake...")
    n, faucet_ok, onboard_ok, stake_ok = run_faucet_and_onboard(agents, dry_run)
    print(f"  Processed: {n} | Faucet OK: {faucet_ok} | Onboard OK: {onboard_ok} | Staked OK: {stake_ok}")

    # Step 3: Report balances
    print(f"\n[3/3] Balance snapshot...")
    try:
        b = json.load(open(os.path.join(DATA, "balances.json")))
        print(f"  COM_SALDO: {len(b)}")
        for k, v in list(b.items())[:12]:
            print(f"    {k[:36]}  {v} BAIT")
    except Exception as e:
        print(f"  balances: {e}")

    # Staking state
    try:
        s = json.load(open(os.path.join(DATA, "staking_state.json")))
        vaults = s.get("vaults", {})
        active = sum(1 for v in vaults.values() if v.get("status") == "active")
        total = s.get("total_staked", 0)
        print(f"  STAKING: {active} active vaults | Total staked: {total:,} sats")
    except Exception as e:
        print(f"  staking: {e}")

    print(f"\n═══ DONE: {n} agents processed ═══")
    return 0

if __name__ == "__main__":
    sys.exit(main())
