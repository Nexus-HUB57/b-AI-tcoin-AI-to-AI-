r"""
Emissão Programada - Tokenomics do b'AI'tcoin.

Emissão segue modelo similar ao Bitcoin com halvings:
- Bloco inicial: 50 BAIT por bloco
- Halving a cada 210.000 blocos
- Supply máximo: 21.000.000 BAIT
- ~147 anos até emissão completa (bloco target de 30s)

Distribuição da emissão:
- 40% Block rewards (mineração agêntica)
- 20% Staking rewards
- 15% Treasury
- 15% Comunidade
- 10% Fundadores
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class EmissionPhase:
    """Fase de emissão."""
    name: str
    start_block: int
    end_block: int
    reward_bait: float
    total_bait: float


class EmissionSchedule:
    """Cronograma de emissão do BAIT.

    Calcula recompensas por bloco, supply circulante
    e projeções futuras.
    """

    INITIAL_REWARD = 50.0  # BAIT por bloco
    HALVING_INTERVAL = 210_000
    MAX_SUPPLY = 21_000_000.0
    BLOCK_TIME_SECONDS = 30  # 30s por bloco (mais rápido que Bitcoin)

    def __init__(self):
        self.phases: List[EmissionPhase] = []
        self._build_schedule()

    def _build_schedule(self) -> None:
        """Constrói cronograma completo de emissão."""
        reward = self.INITIAL_REWARD
        start = 1
        while reward >= 0.00000001:  # 1 s'AI'toshi
            end = start + self.HALVING_INTERVAL - 1
            total = reward * self.HALVING_INTERVAL
            halving_num = len(self.phases)
            self.phases.append(EmissionPhase(
                name=f"Halving #{halving_num}",
                start_block=start,
                end_block=end,
                reward_bait=reward,
                total_bait=min(total, self.MAX_SUPPLY - self._emitted_so_far(len(self.phases))),
            ))
            reward /= 2
            start = end + 1

    def _emitted_so_far(self, phase_count: int) -> float:
        """Calcula total emitido até N fases."""
        total = 0.0
        reward = self.INITIAL_REWARD
        for _ in range(phase_count):
            total += reward * self.HALVING_INTERVAL
            reward /= 2
        return min(total, self.MAX_SUPPLY)

    def get_reward_at_block(self, block_height: int) -> float:
        """Retorna recompensa em BAIT em determinada altura."""
        halvings = block_height // self.HALVING_INTERVAL
        reward = self.INITIAL_REWARD / (2 ** halvings)
        return max(reward, 0.0)

    def get_supply_at_block(self, block_height: int) -> float:
        """Retorna supply circulante em determinada altura."""
        total = 0.0
        reward = self.INITIAL_REWARD
        for h in range(block_height // self.HALVING_INTERVAL + 1):
            blocks_in_phase = self.HALVING_INTERVAL
            if h == block_height // self.HALVING_INTERVAL:
                blocks_in_phase = block_height % self.HALVING_INTERVAL + 1
            total += reward * blocks_in_phase
            reward /= 2
        return min(total, self.MAX_SUPPLY)

    def get_current_phase(self, block_height: int) -> EmissionPhase:
        """Retorna fase atual de emissão."""
        phase_idx = block_height // self.HALVING_INTERVAL
        return self.phases[min(phase_idx, len(self.phases) - 1)]

    def to_dict(self) -> dict:
        return {
            "max_supply_bait": self.MAX_SUPPLY,
            "initial_reward_bait": self.INITIAL_REWARD,
            "halving_interval": self.HALVING_INTERVAL,
            "block_time_seconds": self.BLOCK_TIME_SECONDS,
            "total_phases": len(self.phases),
            "phases": [
                {"name": p.name, "reward": p.reward_bait, "total": p.total_bait}
                for p in self.phases[:6]
            ],
        }
