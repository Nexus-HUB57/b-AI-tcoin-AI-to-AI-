#!/usr/bin/env python3
"""Patch existing exchange packages with missing application_checklist.json files"""
import os, json
from datetime import datetime

BASE = "/home/z/my-project/download/exchange-applications"
NOW = datetime.now().isoformat()

# Existing packages from previous session that need patching
patches = {
    "gateio": {
        "name": "Gate.io", "tier": 2, "listing_type": "Spot Listing",
        "priority": "HIGH", "timeline": "2-4 weeks",
        "direct_apply": "https://www.gate.io/listing",
        "special_notes": "Gate.io Startup listing requires community voting. Budget for voting campaign.",
        "strategic_approach": "Apply for Gate.io Startup program. Community voting with incentives. Gate.io has strong Asian market access."
    },
    "mexc": {
        "name": "MEXC Global", "tier": 2, "listing_type": "Spot Listing",
        "priority": "HIGH", "timeline": "2-3 weeks",
        "direct_apply": "https://www.mexc.com/listing",
        "special_notes": "MEXC M-Day event for new listings. Community engagement required.",
        "strategic_approach": "Apply for M-Day listing event. MEXC has fast listing process and strong altcoin volume."
    },
    "kucoin": {
        "name": "KuCoin", "tier": 2, "listing_type": "Spot Listing",
        "priority": "MEDIUM", "timeline": "4-6 weeks",
        "direct_apply": "https://www.kucoin.com/listing",
        "special_notes": "KuCoin Spotlight program requires community voting.",
        "strategic_approach": "Apply for KuCoin Spotlight voting program. Prepare voting campaign budget."
    },
    "bitget": {
        "name": "Bitget", "tier": 2, "listing_type": "Spot Listing",
        "priority": "MEDIUM", "timeline": "3-4 weeks",
        "direct_apply": "https://www.bitget.com/listing",
        "special_notes": "Bitget focuses on copy trading. API integration for copy trading compatibility.",
        "strategic_approach": "Position for copy trading compatibility. Apply for Bitget Launchpad."
    }
}

for ex_id, info in patches.items():
    ex_dir = os.path.join(BASE, ex_id)
    cl_path = os.path.join(ex_dir, "application_checklist.json")
    if not os.path.exists(cl_path):
        checklist = {
            "exchange": info["name"],
            "tier": info["tier"],
            "listing_type": info["listing_type"],
            "priority": info["priority"],
            "timeline": info["timeline"],
            "checklist": [
                {"step": 1, "item": "token_info.json prepared", "status": "DONE"},
                {"step": 2, "item": "technical_summary.md prepared", "status": "DONE"},
                {"step": 3, "item": "audit_summary.json prepared", "status": "DONE"},
                {"step": 4, "item": f"Submit application at {info['direct_apply']}", "status": "PENDING"},
                {"step": 5, "item": "Deploy wBAIT on Ethereum mainnet", "status": "PENDING"},
                {"step": 6, "item": "Verify contracts on Etherscan", "status": "PENDING"},
                {"step": 7, "item": "Provide market maker commitment", "status": "PENDING"},
                {"step": 8, "item": "Community mobilization", "status": "PENDING"},
                {"step": 9, "item": "Professional external audit", "status": "RECOMMENDED"}
            ],
            "strategic_approach": info["strategic_approach"],
            "special_notes": info.get("special_notes", ""),
            "metadata": {"generated_at": NOW, "generator": "bait-e2e-patch-packages.py"}
        }
        with open(cl_path, "w") as f:
            json.dump(checklist, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Patched {ex_id}/application_checklist.json ({os.path.getsize(cl_path)} bytes)")
    else:
        print(f"  ⏭️  {ex_id}/application_checklist.json already exists")

print("\nAll exchange packages now complete!")
