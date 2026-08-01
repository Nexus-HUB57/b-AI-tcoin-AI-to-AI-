r"""
Pool de Staking b'AI'tcoin.

Agentes AI podem fazer stake de seus BAIT para:
- Participar da validação de blocos
- Ganhar recompensas de inflação
- Obter direitos de governança

Mecânica:
- Mínimo de stake para ser validador: 1,000 BAIT
- Período de lock: configurável (default 30 dias)
- Penalty para early unstake: 10% do stake
- Recompensa proporcional ao stake
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class StakeState(Enum):
    ACTIVE = "active"
    UNSTAKING = "unstaking"
    WITHDRAWN = "withdrawn"
    SLASHED = "slashed"


@dataclass
class StakePosition:
    r"""Posição de stake de um agente."""
    agent_id: str
    amount_sats: int
    start_time: float
    lock_period: float = 2592000  # 30 dias em segundos
    reward_earned: int = 0
    state: StakeState = StakeState.ACTIVE
    unlock_time: float = 0.0

    @property
    def is_locked(self) -> bool:
        if self.state == StakeState.ACTIVE:
            return time.time() - self.start_time < self.lock_period
        return False

    @property
    def effective_stake(self) -> int:
        if self.state in (StakeState.ACTIVE, StakeState.UNSTAKING):
            return self.amount_sats
        return 0


class StakingPool:
    r"""Pool de staking coletivo do b'AI'tcoin.

    Gerencia todas as posições de stake, distribui
    recompensas e aplica penalidades (slashing).
    """

    MIN_STAKE_SATS = 1000 * 100_000_000  # 1,000 BAIT
    EARLY_UNSTAKE_PENALTY = 0.10  # 10%
    ANNUAL_REWARD_RATE = 0.07  # 7% APY

    def __init__(self):
        self.positions: Dict[str, StakePosition] = {}
        self.total_staked: int = 0
        self.total_rewards_distributed: int = 0
        self._reward_accumulator: float = 0.0

    @property
    def total_staked_bait(self) -> float:
        return self.total_staked / 100_000_000

    @property
    def apy(self) -> float:
        return self.ANNUAL_REWARD_RATE * 100

    def stake(self, agent_id: str, amount_sats: int, lock_period: float = 2592000) -> bool:
        r"""Faz stake de BAIT no pool."""
        if amount_sats < self.MIN_STAKE_SATS:
            return False
        if agent_id in self.positions:
            return False  # Já tem posição ativa

        self.positions[agent_id] = StakePosition(
            agent_id=agent_id,
            amount_sats=amount_sats,
            start_time=time.time(),
            lock_period=lock_period,
        )
        self.total_staked += amount_sats
        return True

    def unstake(self, agent_id: str) -> int:
        r"""Inicia unstake. Retorna valor líquido após penalty."""
        pos = self.positions.get(agent_id)
        if pos is None or pos.state != StakeState.ACTIVE:
            return 0

        if pos.is_locked:
            penalty = int(pos.amount_sats * self.EARLY_UNSTAKE_PENALTY)
            net = pos.amount_sats - penalty
        else:
            net = pos.amount_sats

        pos.state = StakeState.WITHDRAWN
        self.total_staked -= pos.amount_sats
        return net

    def distribute_rewards(self, total_reward_sats: int) -> Dict[str, int]:
        r"""Distribui recompensas proporcionalmente ao stake."""
        if self.total_staked == 0:
            return {}

        rewards = {}
        for agent_id, pos in self.positions.items():
            if pos.effective_stake > 0:
                share = pos.effective_stake / self.total_staked
                reward = int(total_reward_sats * share)
                pos.reward_earned += reward
                rewards[agent_id] = reward

        self.total_rewards_distributed += total_reward_sats
        return rewards

    def slash(self, agent_id: str, fraction: float = 0.05) -> int:
        r"""Aplica slashing por comportamento malicioso."""
        pos = self.positions.get(agent_id)
        if pos is None:
            return 0
        slash_amount = int(pos.amount_sats * fraction)
        pos.amount_sats -= slash_amount
        self.total_staked -= slash_amount
        pos.state = StakeState.SLASHED
        return slash_amount

    def get_validator_set(self) -> List[str]:
        r"""Retorna lista de validadores ativos (com stake mínimo)."""
        return [
            agent_id for agent_id, pos in self.positions.items()
            if pos.effective_stake >= self.MIN_STAKE_SATS
            and pos.state == StakeState.ACTIVE
        ]

    def to_dict(self) -> dict:
        return {
            "total_staked_bait": self.total_staked_bait,
            "apy": self.apy,
            "positions": len(self.positions),
            "validators": len(self.get_validator_set()),
            "total_rewards_distributed": self.total_rewards_distributed,
        }
