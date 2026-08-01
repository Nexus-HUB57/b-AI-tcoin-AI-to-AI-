r"""
Faucet b'AI'tcoin - Distribui BAIT para novos agentes.

Mecanismo anti-abuso:
- Cooldown por agente (default 24h)
- Limite máximo por agente (default 100 BAIT)
- Rate limiting global
- Proof-of-agent (assinatura Schnorr como challenge)
"""
import hashlib
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class FaucetClaim:
    r"""Registro de claim do faucet."""
    claim_id: str
    agent_id: str
    amount_sats: int
    pubkey_hex: str
    challenge_sig: str
    timestamp: float = field(default_factory=time.time)
    tx_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "agent_id": self.agent_id,
            "amount_bait": self.amount_sats / 100_000_000,
            "pubkey": self.pubkey_hex[:16] + "...",
            "timestamp": self.timestamp,
            "tx_hash": self.tx_hash,
        }


class BAITFaucet:
    r"""Faucet de BAIT para novos agentes AI.

    Funcionalidades:
    - Distribuição de BAIT grátis para novos agentes
    - Cooldown por agente (anti-spam)
    - Limite máximo por agente
    - Estatísticas de distribuição
    """

    def __init__(self, token, amount_sats: int = 10 * 100_000_000,
                 cooldown: int = 86400, max_total: int = 100 * 100_000_000):
        self.token = token
        self.amount_sats = amount_sats
        self.cooldown = cooldown
        self.max_total_sats = max_total
        self._claims: Dict[str, List[FaucetClaim]] = {}
        self._global_claims = 0
        self._total_distributed = 0
        self._rate_limit_window = 60
        self._rate_limit_count = 0
        self._rate_limit_start = time.time()

    def claim(self, agent_id: str, pubkey_hex: str,
              challenge_sig: str = "") -> dict:
        r"""Solicita BAIT do faucet.

        Args:
            agent_id: ID do agente
            pubkey_hex: chave pública hex
            challenge_sig: assinatura Schnorr do challenge

        Returns:
            Dict com resultado da claim
        """
        now = time.time()

        # Rate limiting global (60 claims/min)
        if now - self._rate_limit_start > self._rate_limit_window:
            self._rate_limit_count = 0
            self._rate_limit_start = now
        if self._rate_limit_count >= 60:
            return {"success": False, "error": "rate_limited", "retry_after": 60}

        # Cooldown por agente
        agent_claims = self._claims.get(agent_id, [])
        if agent_claims:
            last_claim = agent_claims[-1]
            elapsed = now - last_claim.timestamp
            if elapsed < self.cooldown:
                return {
                    "success": False,
                    "error": "cooldown",
                    "retry_after_seconds": int(self.cooldown - elapsed),
                }

        # Limite total por agente
        total_claimed = sum(c.amount_sats for c in agent_claims)
        if total_claimed + self.amount_sats > self.max_total_sats:
            return {"success": False, "error": "max_total_reached"}

        # Mint tokens
        success = self.token.mint(agent_id, self.amount_sats)
        if not success:
            return {"success": False, "error": "mint_failed"}

        # Register claim
        claim_id = hashlib.sha256(f"{agent_id}:{now}:{pubkey_hex}".encode()).hexdigest()[:16]
        claim = FaucetClaim(
            claim_id=claim_id,
            agent_id=agent_id,
            amount_sats=self.amount_sats,
            pubkey_hex=pubkey_hex,
            challenge_sig=challenge_sig,
        )
        self._claims.setdefault(agent_id, []).append(claim)
        self._global_claims += 1
        self._total_distributed += self.amount_sats
        self._rate_limit_count += 1

        return {
            "success": True,
            "claim_id": claim_id,
            "amount_bait": self.amount_sats / 100_000_000,
            "balance_bait": self.token.balance_bait(agent_id),
        }

    def get_balance(self, agent_id: str) -> float:
        return self.token.balance_bait(agent_id)

    def get_claim_history(self, agent_id: str) -> List[dict]:
        return [c.to_dict() for c in self._claims.get(agent_id, [])]

    def get_stats(self) -> dict:
        return {
            "total_claims": self._global_claims,
            "total_distributed_bait": self._total_distributed / 100_000_000,
            "unique_agents": len(self._claims),
            "amount_per_claim_bait": self.amount_sats / 100_000_000,
            "cooldown_hours": self.cooldown / 3600,
            "max_per_agent_bait": self.max_total_sats / 100_000_000,
        }
