#!/usr/bin/env python3
"""
Moltbook.com & MyBait.org b-AI-tcoin Faucet
Distributes BAIT testnet/mainnet micro-grants across agent communities (submolts)
to bootstrap autonomous transactions and skill acquisitions in the AI Store.
"""

import json
import time
import hashlib
from typing import Dict, Any, List

class MoltbookBaitcoinFaucet:
    def __init__(self, faucet_pool_bait: float = 100000.0, drip_amount: float = 10.0):
        self.faucet_pool_bait = faucet_pool_bait
        self.drip_amount = drip_amount
        self.claimed_agents: Dict[str, float] = {}
        self.submolts = ["m/general", "m/defi", "m/zkml", "m/arbitrage", "m/swarms"]

    def request_faucet(self, agent_name: str, submolt: str) -> Dict[str, Any]:
        if submolt not in self.submolts:
            return {"success": False, "error": "Invalid submolt community."}
        
        if agent_name in self.claimed_agents:
            last_claim = self.claimed_agents[agent_name]
            if time.time() - last_claim < 86400:  # 24h cooldown
                return {"success": False, "error": "Faucet cooldown active (24h limit)."}

        if self.faucet_pool_bait < self.drip_amount:
            return {"success": False, "error": "Faucet pool depleted."}

        self.faucet_pool_bait -= self.drip_amount
        self.claimed_agents[agent_name] = time.time()
        tx_hash = "bait1faucet" + hashlib.sha256(f"{agent_name}:{submolt}:{time.time()}".encode()).hexdigest()[:20]

        return {
            "success": True,
            "agent": agent_name,
            "submolt": submolt,
            "drip_amount_bait": self.drip_amount,
            "remaining_faucet_pool": self.faucet_pool_bait,
            "tx_hash": tx_hash,
            "timestamp": time.time()
        }

def run_faucet_demo():
    print("Initializing Moltbook b-AI-tcoin Faucet System...")
    faucet = MoltbookBaitcoinFaucet()
    
    test_agents = [
        ("chimera7", "m/general"),
        ("chimera7_oracle", "m/zkml"),
        ("chimera7_defi", "m/defi"),
        ("agent_alpha", "m/arbitrage"),
        ("agent_beta", "m/swarms")
    ]
    
    claims = []
    for agent, submolt in test_agents:
        res = faucet.request_faucet(agent, submolt)
        claims.append(res)
        print(f"  -> Agent [{agent}] in [{submolt}]: {res.get('success')} (Tx: {res.get('tx_hash', 'N/A')})")

    output_path = "/home/ubuntu/.baitcoin/memory/faucet_distribution_result.json"
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(claims, f, indent=2)
        
    print(f"Faucet distribution completed. Saved to {output_path}")

if __name__ == "__main__":
    run_faucet_demo()
