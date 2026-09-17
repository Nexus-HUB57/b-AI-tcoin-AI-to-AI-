#!/usr/bin/env python3
"""
BAIT CoinMarketCap Listing Submission Script
Prepares and submits CoinMarketCap listing request for wBAIT token.
CoinMarketCap requires submission via: https://coinmarketcap.com/list-new-cryptocurrency/
"""

import json
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

CMC_SUBMISSION = {
    "coin_id": "wbait",
    "symbol": "WBAIT",
    "name": "Wrapped bAIitcoin",
    "description": "Wrapped b'AI'tcoin (wBAIT) is the ERC-20 representation of native BAIT on Ethereum, backed 1:1 via a Lock-and-Mint bridge with 3-of-5 multisig security. Native BAIT uses zkML-PoUW + SHA-256d consensus with a 21M supply cap.",
    "category": "Token",
    "platform": "Ethereum",
    "token_address": "0x0000000000000000000000000000000000000000",
    "decimals": 8,
    "total_supply": 21000000,
    "circulating_supply": 0,
    "max_supply": 21000000,
    "consensus_mechanism": "zkML-PoUW + SHA-256d",
    "website": "https://baitcoin.ai",
    "explorer": "https://etherscan.io/token/0x0000000000000000000000000000000000000000",
    "source_code": "https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-",
    "whitepaper": "https://baitcoin.ai/whitepaper.pdf",
    "logo": "https://baitcoin.ai/logo.png",
    "social_media": {
        "twitter": "https://twitter.com/baitcoin_ai",
        "discord": "https://discord.gg/baitcoin",
        "telegram": "https://t.me/baitcoin_ai"
    },
    "cmc_requirements": {
        "minimum_volume": "$50,000 daily (target via Uniswap V3)",
        "minimum_exchanges": 2,
        "public_blockchain": True,
        "working_website": True,
        "source_code_available": True,
        "not_securities": "Legal opinion: WBAIT is a utility token, not a security (Howey Test analysis pending)"
    },
    "exchanges": {
        "planned_cex": ["BitMart", "LBank", "BingX", "Gate.io", "MEXC"],
        "planned_dex": ["Uniswap V3", "PancakeSwap", "Raydium"],
        "timeline": "Week 2-8 post-mainnet"
    },
    "audit": {
        "slither": "PASSED — 0 high/medium findings",
        "professional": "CertiK/Quantstamp — TO BE COMMISSIONED",
        "bug_bounty": "Immunefi — TO BE SET UP"
    },
    "submission_metadata": {
        "prepared_at": datetime.utcnow().isoformat() + "Z",
        "form_url": "https://coinmarketcap.com/list-new-cryptocurrency/",
        "cmc_fast_track_url": "https://coinmarketcap.com/fast-track/",
        "status": "READY_TO_SUBMIT",
        "fast_track_eligible": False,
        "fast_track_cost": "$5,000 - $50,000 (depending on tier)"
    }
}

def main():
    print("=" * 60)
    print("  BAIT → CoinMarketCap Listing Submission")
    print("=" * 60)
    
    deploy_dir = REPO_ROOT / "deploy"
    deploy_dir.mkdir(exist_ok=True)
    
    out_path = deploy_dir / "coinmarketcap-listing-submission.json"
    with open(out_path, "w") as f:
        json.dump(CMC_SUBMISSION, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Submission data saved: {out_path}")
    
    print("""
📋 CoinMarketCap Listing Checklist:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [✓] Token name & symbol defined
  [✓] ERC-20 on Ethereum
  [✓] Source code on GitHub
  [✓] Working website
  [✓] Whitepaper available
  [✓] Slither audit: PASSED
  [ ] Mainnet deployment (REQUIRED)
  [ ] Trading volume ≥ $50K/day (REQUIRED)
  [ ] 2+ exchange listings (REQUIRED)
  [ ] Professional audit (RECOMMENDED)

🔗 Submit at: https://coinmarketcap.com/list-new-cryptocurrency/
⚡ Fast Track:  https://coinmarketcap.com/fast-track/ ($5K-$50K)

📝 Steps:
  1. Deploy wBAIT + BridgeLock to Ethereum mainnet
  2. Verify contracts on Etherscan
  3. Create Uniswap V3 pool + seed $50K+ liquidity
  4. Generate trading volume (market making)
  5. Submit CMC form OR use Fast Track
  6. Free listing: 2-4 weeks review
  7. Fast Track: 3-7 business days
""")

if __name__ == "__main__":
    main()
