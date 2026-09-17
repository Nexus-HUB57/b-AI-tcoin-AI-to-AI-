#!/usr/bin/env python3
"""
BAIT Deployment Readiness Assessment
Evaluates all prerequisites for mainnet deployment and exchange listing.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent.parent

def assess():
    print("=" * 70)
    print("  BAIT Mainnet Deployment Readiness Assessment")
    print("  " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    print("=" * 70)

    assessment = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_readiness": 0,
        "categories": {}
    }

    # === SMART CONTRACTS ===
    contracts = {
        "wbait_compiled": {"status": True, "weight": 5, "note": "WBAIT.sol compiled with Solc 0.8.20"},
        "bridgelock_compiled": {"status": True, "weight": 5, "note": "BridgeLock.sol compiled with Solc 0.8.20"},
        "uniswap_liq_compiled": {"status": True, "weight": 3, "note": "BAITUniswapV3Liquidity.sol compiled"},
        "tests_passing": {"status": True, "weight": 10, "note": "12/12 Foundry tests passing"},
        "slither_passed": {"status": True, "weight": 8, "note": "0 High/Medium findings in Slither"},
        "professional_audit": {"status": False, "weight": 15, "note": "CertiK/Quantstamp audit not yet commissioned"},
        "formal_verification": {"status": False, "weight": 5, "note": "Certora/Halmos formal verification pending"},
        "bug_bounty_setup": {"status": False, "weight": 3, "note": "Immunefi bug bounty not set up"},
        "contracts_deployed_sepolia": {"status": False, "weight": 5, "note": "Not deployed to Sepolia yet"},
        "contracts_deployed_mainnet": {"status": False, "weight": 15, "note": "Not deployed to mainnet yet"},
        "contracts_verified_etherscan": {"status": False, "weight": 5, "note": "Not verified on Etherscan yet"},
    }

    # === BRIDGE ===
    bridge = {
        "multisig_configured": {"status": False, "weight": 5, "note": "3-of-5 operators not configured"},
        "timelock_active": {"status": True, "weight": 3, "note": "24h timelock in contract code"},
        "rate_limit_active": {"status": True, "weight": 3, "note": "100K/day rate limit in contract code"},
        "bridge_tested_e2e": {"status": False, "weight": 5, "note": "Full lock-mint-burn-release lifecycle not tested on-chain"},
    }

    # === DEX / LIQUIDITY ===
    dex = {
        "uniswap_pool_created": {"status": False, "weight": 5, "note": "Uniswap V3 pool not created"},
        "initial_liquidity_seeded": {"status": False, "weight": 5, "note": "No liquidity seeded ($50K target)"},
        "trading_volume_generated": {"status": False, "weight": 3, "note": "No trading volume yet"},
    }

    # === AGGREGATORS ===
    aggregators = {
        "coingecko_submitted": {"status": False, "weight": 3, "note": "Submission data prepared but not submitted"},
        "coingecko_listed": {"status": False, "weight": 5, "note": "Not listed on CoinGecko"},
        "coinmarketcap_submitted": {"status": False, "weight": 3, "note": "Submission data prepared but not submitted"},
        "coinmarketcap_listed": {"status": False, "weight": 5, "note": "Not listed on CoinMarketCap"},
        "dexscreener_listed": {"status": False, "weight": 2, "note": "Will auto-list after Uniswap pool creation"},
    }

    # === COMPLIANCE ===
    compliance = {
        "howey_opinion": {"status": False, "weight": 5, "note": "Legal opinion letter not commissioned"},
        "kyc_aml_procedures": {"status": False, "weight": 3, "note": "KYC/AML procedures not documented"},
        "insurance_coverage": {"status": False, "weight": 2, "note": "Smart contract insurance not obtained"},
        "terms_of_service": {"status": False, "weight": 2, "note": "ToS for bridge not drafted"},
    }

    # === EXCHANGE APPLICATIONS ===
    exchanges = {
        "bitmart_application": {"status": True, "weight": 3, "note": "Application package prepared"},
        "lbank_application": {"status": True, "weight": 3, "note": "Application package prepared"},
        "bingx_application": {"status": True, "weight": 3, "note": "Application package prepared"},
        "gateio_application": {"status": True, "weight": 2, "note": "Application package prepared"},
        "mexc_application": {"status": True, "weight": 2, "note": "Application package prepared"},
        "tier1_applications": {"status": True, "weight": 1, "note": "Packages prepared (Binance/Coinbase/Kraken)"},
    }

    all_categories = {
        "smart_contracts": contracts,
        "bridge": bridge,
        "dex_liquidity": dex,
        "aggregators": aggregators,
        "compliance": compliance,
        "exchange_applications": exchanges,
    }

    total_weight = 0
    achieved_weight = 0

    for cat_name, items in all_categories.items():
        cat_weight = sum(i["weight"] for i in items.values())
        cat_achieved = sum(i["weight"] for i in items.values() if i["status"])
        total_weight += cat_weight
        achieved_weight += cat_achieved
        pct = int((cat_achieved / cat_weight) * 100) if cat_weight > 0 else 0

        assessment["categories"][cat_name] = {
            "readiness": f"{pct}%",
            "items_ready": sum(1 for i in items.values() if i["status"]),
            "items_total": len(items),
            "weight_achieved": cat_achieved,
            "weight_total": cat_weight
        }

        print(f"\n  [{cat_name.upper()}] — {pct}% ready ({cat_achieved}/{cat_weight} pts)")
        for name, item in items.items():
            icon = "✅" if item["status"] else "❌"
            print(f"    {icon} {name} ({item['weight']}pt) — {item['note']}")

    overall = int((achieved_weight / total_weight) * 100) if total_weight > 0 else 0
    assessment["overall_readiness"] = overall

    print(f"\n{'='*70}")
    print(f"  OVERALL READINESS: {overall}% ({achieved_weight}/{total_weight} pts)")
    print(f"{'='*70}")

    # Priority actions
    print(f"""
  🚨 PRIORITY ACTIONS (sorted by impact):

  1. Commission CertiK Professional Audit (15 pts) — Week 3-4
     → Contact: audit@certik.com
     → Cost: $15K-$50K
     → Timeline: 2-4 weeks

  2. Deploy to Ethereum Mainnet (15 pts) — Week 1-2
     → Prerequisite: Sepolia deployment + testing
     → Cost: ~0.5 ETH deployment gas
     → Use: forge script DeployBAIT.s.sol --rpc-url $MAINNET_RPC_URL --broadcast

  3. Configure Bridge Multisig Operators (5 pts) — Week 1
     → Generate 5 operator keys (HSM recommended)
     → Set 3-of-5 threshold
     → Test full lifecycle on Sepolia

  4. Commission Howey Test Legal Opinion (5 pts) — Week 2
     → Legal counsel for securities analysis
     → Cost: $5K-$15K
     → Required for Tier-1 exchanges

  5. Create Uniswap V3 Pool + Seed Liquidity (5 pts) — Week 2
     → Target: $50K+ initial liquidity
     → Fee tier: 0.3%
     → Concentrated liquidity around initial price

  6. Submit CoinGecko + CoinMarketCap Listings (8 pts) — Week 3
     → Prerequisite: 2+ exchange listings + trading volume
     → Free: 2-4 weeks review
     → Fast Track (CMC): $5K-$50K, 3-7 days
""")

    # Save
    deploy_dir = REPO / "deploy"
    deploy_dir.mkdir(exist_ok=True)
    out = deploy_dir / "deployment-readiness-assessment.json"
    with open(out, "w") as f:
        json.dump(assessment, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Assessment saved: {out}")

if __name__ == "__main__":
    assess()
