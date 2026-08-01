r"""Testnet Faucet Node — Distributes testnet BAIT to developers.

Provides a programmable faucet for local testnet that mirrors the
mainnet faucet but with significantly higher limits and shorter
cooldowns for rapid testing.

Key differences from mainnet faucet:
    - 1,000,000 BAIT initial balance (vs 21,000 capped on mainnet)
    - 100 BAIT per claim (vs 10 BAIT on mainnet)
    - 60s cooldown (vs 3600s on mainnet)
    - No challenge signature required (convenience for testing)
    - Unlimited total claims (until exhausted)

Usage::

    faucet = FaucetNode(initial_balance_sats=1_000_000 * 100_000_000)
    result = faucet.claim("test_agent", "0xabc123...")
    assert result["success"]
    print(result["amount_bait"])  # 100.0
"""
import hashlib
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class FaucetClaim:
    r"""Record of a testnet faucet claim."""
    claim_id: str
    agent_id: str
    amount_sats: int
    pubkey_hex: str
    timestamp: float
    tx_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "agent_id": self.agent_id,
            "amount_sats": self.amount_sats,
            "amount_bait": self.amount_sats / 100_000_000,
            "pubkey_hex": self.pubkey_hex,
            "timestamp": self.timestamp,
            "tx_hash": self.tx_hash,
        }


class FaucetNode:
    r"""Testnet faucet for distributing BAIT to test accounts.

    The faucet tracks claims per agent with a configurable cooldown,
    enforces a maximum balance to prevent depletion, and provides
    detailed statistics for monitoring.

    Parameters
    ----------
    network_name : str
        Network identifier (default "baitcoin-testnet")
    initial_balance_sats : int
        Starting balance in satoshis
    claim_amount_sats : int
        Amount per claim in satoshis
    cooldown_seconds : float
        Minimum time between claims for same agent
    """

    def __init__(
        self,
        network_name: str = "baitcoin-testnet",
        initial_balance_sats: int = 1_000_000 * 100_000_000,
        claim_amount_sats: int = 100 * 100_000_000,
        cooldown_seconds: float = 60.0,
    ):
        self.network_name = network_name
        self.initial_balance_sats = initial_balance_sats
        self.claim_amount_sats = claim_amount_sats
        self.cooldown_seconds = cooldown_seconds

        self._balance_sats = initial_balance_sats
        self._claims: List[FaucetClaim] = []
        self._agent_last_claim: Dict[str, float] = {}
        self._total_distributed = 0
        self._total_claims = 0

    def claim(self, agent_id: str, pubkey_hex: str) -> dict:
        r"""Process a faucet claim for an agent.

        Validates cooldown, checks balance, creates claim record.

        Returns
        -------
        dict
            Claim result with success status and details.
        """
        now = time.time()

        # Check cooldown
        last_claim = self._agent_last_claim.get(agent_id, 0)
        if now - last_claim < self.cooldown_seconds:
            remaining = self.cooldown_seconds - (now - last_claim)
            return {
                "success": False,
                "error": "cooldown_active",
                "remaining_seconds": round(remaining, 1),
            }

        # Check balance
        if self._balance_sats < self.claim_amount_sats:
            return {
                "success": False,
                "error": "faucet_depleted",
                "remaining_balance_bait": round(
                    self._balance_sats / 100_000_000, 8
                ),
            }

        # Create claim
        claim_id = uuid.uuid4().hex[:16]
        tx_hash = hashlib.sha256(
            f"faucet:{claim_id}:{agent_id}:{now}".encode()
        ).hexdigest()

        claim = FaucetClaim(
            claim_id=claim_id,
            agent_id=agent_id,
            amount_sats=self.claim_amount_sats,
            pubkey_hex=pubkey_hex,
            timestamp=now,
            tx_hash=tx_hash,
        )

        # Update state
        self._balance_sats -= self.claim_amount_sats
        self._total_distributed += self.claim_amount_sats
        self._total_claims += 1
        self._agent_last_claim[agent_id] = now
        self._claims.append(claim)

        return {
            "success": True,
            "claim": claim.to_dict(),
            "remaining_balance_bait": round(
                self._balance_sats / 100_000_000, 8
            ),
            "total_distributed_bait": round(
                self._total_distributed / 100_000_000, 8
            ),
        }

    def get_balance(self) -> float:
        r"""Get remaining faucet balance in BAIT."""
        return self._balance_sats / 100_000_000

    def get_claim_history(self, agent_id: str = None) -> List[dict]:
        r"""Get claim history, optionally filtered by agent."""
        claims = self._claims
        if agent_id:
            claims = [c for c in claims if c.agent_id == agent_id]
        return [c.to_dict() for c in claims]

    def get_stats(self) -> dict:
        r"""Get faucet statistics."""
        unique_agents = len(set(c.agent_id for c in self._claims))
        return {
            "network_name": self.network_name,
            "balance_bait": round(self._balance_sats / 100_000_000, 8),
            "claim_amount_bait": self.claim_amount_sats / 100_000_000,
            "cooldown_seconds": self.cooldown_seconds,
            "total_claims": self._total_claims,
            "total_distributed_bait": round(
                self._total_distributed / 100_000_000, 8
            ),
            "unique_agents_served": unique_agents,
            "utilization_pct": round(
                (self.initial_balance_sats - self._balance_sats)
                / self.initial_balance_sats * 100, 2
            ),
        }

    def top_up(self, amount_sats: int) -> dict:
        r"""Add balance to the faucet (admin operation)."""
        self._balance_sats += amount_sats
        self.initial_balance_sats += amount_sats
        return {
            "new_balance_bait": round(self._balance_sats / 100_000_000, 8),
            "added_bait": amount_sats / 100_000_000,
        }
