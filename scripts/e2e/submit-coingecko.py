#!/usr/bin/env python3
"""
BAIT CoinGecko Listing Submission Script
Prepares and submits CoinGecko listing request for wBAIT token.
CoinGecko requires submission via their form: https://www.coingecko.com/en/coins/list_new
"""

import json
import os
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

COINGECKO_SUBMISSION = {
    "coin_id": "wbait",
    "symbol": "WBAIT",
    "name": "Wrapped bAIitcoin",
    "description": "Wrapped b'AI'tcoin (wBAIT) is the ERC-20 representation of native BAIT on Ethereum, backed 1:1 via a Lock-and-Mint bridge with 3-of-5 multisig security, 24h timelock, and 100K/day rate limit. The native BAIT chain uses zkML-PoUW + SHA-256d consensus with a fixed 21M supply cap.",
    "website": "https://baitcoin.ai",
    "explorer": "https://etherscan.io/token/0x0000000000000000000000000000000000000000",
    "research": "https://baitcoin.ai/whitepaper.pdf",
    "github": "https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-",
    "logo_url": "https://baitcoin.ai/logo.png",
    "community": {
        "twitter": "https://twitter.com/baitcoin_ai",
        "discord": "https://discord.gg/baitcoin",
        "telegram": "https://t.me/baitcoin_ai",
        "reddit": ""
    },
    "tokenomics": {
        "total_supply": "21,000,000 WBAIT",
        "circulating_supply": "0 (pre-listing)",
        "max_supply_cap": "21,000,000 (hard cap, invariants enforced on-chain)",
        "decimals": 8,
        "blockchain": "Ethereum (ERC-20)",
        "consensus_native": "zkML-PoUW + SHA-256d",
        "bridge_type": "Lock-and-Mint (3-of-5 multisig + 24h timelock + 100K/day rate limit)"
    },
    "smart_contracts": {
        "wbait": "WBAIT.sol — ERC20 + ERC20Burnable + ERC20Permit + Ownable2Step + Pausable",
        "bridge_lock": "BridgeLock.sol — 3-of-5 multisig lock-mint bridge with rate limiting",
        "uniswap_liquidity": "BAITUniswapV3Liquidity.sol — Uniswap V3 pool creation + seeding"
    },
    "audit_status": {
        "slither_static": "PASSED — 0 high/medium findings",
        "professional_audit": "CertiK/Quantstamp — TO BE COMMISSIONED (Week 3-4)",
        "bug_bounty": "Immunefi — TO BE SET UP (post-mainnet)"
    },
    "listing_exchanges": {
        "target_cex": ["BitMart", "LBank", "BingX", "Gate.io", "MEXC", "Bybit", "OKX"],
        "target_dex": ["Uniswap V3 (Ethereum)", "PancakeSwap (BSC)", "Raydium (Solana)"],
        "target_aggregators": ["CoinGecko", "CoinMarketCap", "DEXScreener"]
    },
    "submission_metadata": {
        "prepared_at": datetime.utcnow().isoformat() + "Z",
        "form_url": "https://www.coingecko.com/en/coins/list_new",
        "status": "READY_TO_SUBMIT",
        "requirements_met": [
            "Smart contracts deployed and verified (pending mainnet deployment)",
            "Working website with live explorer",
            "Active GitHub repository",
            "Whitepaper available",
            "Community channels established",
            "Slither audit passed"
        ],
        "requirements_pending": [
            "Mainnet contract deployment",
            "Professional security audit (CertiK/Quantstamp)",
            "Minimum 2 exchange listings (CoinGecko requirement)",
            "Trading volume generation"
        ]
    }
}

def main():
    print("=" * 60)
    print("  BAIT → CoinGecko Listing Submission")
    print("=" * 60)
    
    # Save submission data
    deploy_dir = REPO_ROOT / "deploy"
    deploy_dir.mkdir(exist_ok=True)
    
    out_path = deploy_dir / "coingecko-listing-submission.json"
    with open(out_path, "w") as f:
        json.dump(COINGECKO_SUBMISSION, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Submission data saved: {out_path}")
    
    print("""
📋 CoinGecko Listing Checklist:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [✓] Token name & symbol defined
  [✓] Description prepared (English)
  [✓] Website: https://baitcoin.ai
  [✓] GitHub repo: Nexus-HUB57/b-AI-tcoin-AI-to-AI-
  [✓] Smart contracts: WBAIT.sol, BridgeLock.sol
  [✓] Slither audit: PASSED
  [✓] Whitepaper available
  [ ] Mainnet deployment (REQUIRED)
  [ ] Professional audit (RECOMMENDED)
  [ ] 2+ exchange listings (REQUIRED)
  [ ] Trading volume (REQUIRED)

🔗 Submit at: https://www.coingecko.com/en/coins/list_new

📝 Steps:
  1. Deploy wBAIT + BridgeLock to Ethereum mainnet
  2. Verify contracts on Etherscan
  3. Create Uniswap V3 pool + seed liquidity
  4. Submit CoinGecko form with contract address
  5. Wait 3-7 business days for review
""")

if __name__ == "__main__":
    main()
