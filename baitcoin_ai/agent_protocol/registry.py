r"""
Registro de Agentes AI - Identidade e reputação on-chain.

Cada agente AI na rede b'AI'tcoin possui:
- Identidade criptográfica (chave Schnorr)
- Reputação baseada em histórico
- Capacidades declaradas (ML, DeFi, oracle, etc)
- Stake atrelado à identidade
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class AgentCapability(Enum):
    ML_INFERENCE = "ml_inference"
    BLOCK_VALIDATION = "block_validation"
    ORACLE_PROVIDER = "oracle_provider"
    DEFI_TRADING = "defi_trading"
    LENDING = "lending"
    STAKING = "staking"
    DATA_PROCESSING = "data_processing"
    MARKET_MAKING = "market_making"


@dataclass
class AgentProfile:
    """Perfil completo de um agente AI."""
    agent_id: str
    pubkey_hex: str
    capabilities: Set[AgentCapability] = field(default_factory=set)
    reputation_score: float = 50.0
    stake_sats: int = 0
    registered_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    is_active: bool = True

    @property
    def is_validator(self) -> bool:
        return AgentCapability.BLOCK_VALIDATION in self.capabilities

    @property
    def trust_level(self) -> str:
        if self.reputation_score >= 80:
            return "trusted"
        elif self.reputation_score >= 50:
            return "standard"
        elif self.reputation_score >= 20:
            return "probation"
        return "suspended"


class AgentRegistry:
    """Registro descentralizado de agentes AI.

    Gerencia identidades, reputação e capacidades
    de todos os agentes na rede.
    """

    MIN_REPUTATION_FOR_VALIDATION = 60.0
    REPUTATION_DECAY_RATE = 0.01  # 1% por dia de inatividade
    MAX_AGENTS = 10_000

    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
        self._reputation_events: List[dict] = []

    def register(self, agent_id: str, pubkey_hex: str,
                  capabilities: Optional[List[AgentCapability]] = None) -> bool:
        """Registra novo agente na rede."""
        if agent_id in self.agents:
            return False
        if len(self.agents) >= self.MAX_AGENTS:
            return False
        self.agents[agent_id] = AgentProfile(
            agent_id=agent_id,
            pubkey_hex=pubkey_hex,
            capabilities=set(capabilities or []),
        )
        return True

    def update_reputation(self, agent_id: str, delta: float,
                           reason: str = "") -> bool:
        """Atualiza reputação de um agente (+ou-)."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return False
        agent.reputation_score = max(0, min(100, agent.reputation_score + delta))
        agent.last_active = time.time()
        self._reputation_events.append({
            "agent": agent_id, "delta": delta,
            "reason": reason, "time": time.time(),
        })
        return True

    def get_validators(self) -> List[str]:
        """Retorna agentes qualificados como validadores."""
        return [
            aid for aid, a in self.agents.items()
            if a.is_validator
            and a.reputation_score >= self.MIN_REPUTATION_FOR_VALIDATION
            and a.is_active
        ]

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Retorna perfil de um agente."""
        return self.agents.get(agent_id)

    def list_agents(self, capability: Optional[AgentCapability] = None) -> List[dict]:
        """Lista agentes, opcionalmente filtrado por capacidade."""
        result = []
        for agent in self.agents.values():
            if capability and capability not in agent.capabilities:
                continue
            result.append({
                "agent_id": agent.agent_id,
                "reputation": agent.reputation_score,
                "trust": agent.trust_level,
                "capabilities": [c.value for c in agent.capabilities],
            })
        return sorted(result, key=lambda x: x["reputation"], reverse=True)

    def to_dict(self) -> dict:
        return {
            "total_agents": len(self.agents),
            "validators": len(self.get_validators()),
            "avg_reputation": (sum(a.reputation_score for a in self.agents.values())
                               / max(len(self.agents), 1)),
        }
