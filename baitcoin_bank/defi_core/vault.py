r"""
Vault DeFi Core - O coração do "Be Your Bank".

Um Vault é uma conta inteligente auto-custodiada que combina:
- Gestão automática de ativos
- Yield optimization (auto-compound)
- Rebalanceamento entre estratégias
- Proteção contra perdas (stop-loss)

Cada agente AI possui seu próprio Vault,
funcionando como seu "banco pessoal".
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class StrategyType(Enum):
    HODL = "hodl"
    STAKING = "staking"
    LENDING = "lending"
    LP_PROVIDE = "lp_provide"
    COMPOUND = "compound"


@dataclass
class VaultAllocation:
    """Alocação de ativos em uma estratégia."""
    strategy: StrategyType
    amount_sats: int
    apy: float = 0.0
    entry_time: float = field(default_factory=time.time)

    @property
    def accrued_yield(self) -> int:
        elapsed = time.time() - self.entry_time
        annual_yield = int(self.amount_sats * (self.apy / 100))
        return int(annual_yield * (elapsed / 31536000))


@dataclass
class VaultConfig:
    """Configuração do Vault de um agente."""
    agent_id: str
    risk_tolerance: float = 0.5  # 0.0 (conservador) a 1.0 (agressivo)
    auto_compound: bool = True
    rebalance_threshold: float = 0.10  # 10% de desvio para rebalancear
    stop_loss_pct: float = 0.20  # Stop loss de 20%


class Vault:
    """Vault auto-custodiado para agente AI.

    Implementa o conceito "Be Your Bank":
    - O agente controla 100% dos fundos
    - Estratégias são executadas automaticamente
    - Yield é otimizado sem intervenção humana
    """

    def __init__(self, config: VaultConfig):
        self.config = config
        self.allocations: List[VaultAllocation] = []
        self.deposits_total: int = 0
        self.withdrawals_total: int = 0
        self.created_at = time.time()
        self._tx_history: List[dict] = []

    @property
    def total_value(self) -> int:
        return sum(a.amount_sats + a.accrued_yield for a in self.allocations)

    @property
    def total_yield(self) -> int:
        return sum(a.accrued_yield for a in self.allocations)

    @property
    def net_pnl(self) -> int:
        return self.total_value - self.deposits_total + self.withdrawals_total

    def deposit(self, amount_sats: int, strategy: StrategyType = StrategyType.HODL) -> bool:
        """Deposita fundos no vault com estratégia específica."""
        if amount_sats <= 0:
            return False
        self.allocations.append(VaultAllocation(
            strategy=strategy,
            amount_sats=amount_sats,
            apy=self._get_strategy_apy(strategy),
        ))
        self.deposits_total += amount_sats
        self._tx_history.append({
            "type": "deposit",
            "amount": amount_sats,
            "strategy": strategy.value,
            "time": time.time(),
        })
        return True

    def withdraw(self, amount_sats: int, strategy: Optional[StrategyType] = None) -> int:
        """Saca fundos do vault. Retorna valor sacado."""
        available = 0
        targets = []
        for i, alloc in enumerate(self.allocations):
            if strategy and alloc.strategy != strategy:
                continue
            targets.append(i)
            available += alloc.amount_sats + alloc.accrued_yield

        actual = min(amount_sats, available)
        if actual <= 0:
            return 0

        remaining = actual
        for i in reversed(targets):
            alloc = self.allocations[i]
            val = alloc.amount_sats + alloc.accrued_yield
            take = min(remaining, val)
            alloc.amount_sats = max(0, alloc.amount_sats - take)
            remaining -= take

        self.withdrawals_total += actual
        self._tx_history.append({
            "type": "withdraw",
            "amount": actual,
            "time": time.time(),
        })
        self.allocations = [a for a in self.allocations if a.amount_sats > 0]
        return actual

    def rebalance(self, target_weights: Dict[StrategyType, float]) -> bool:
        """Rebalanceia alocações conforme pesos-alvo."""
        total = self.total_value
        if total <= 0:
            return False
        for alloc in self.allocations:
            target_pct = target_weights.get(alloc.strategy, 0)
            current_pct = (alloc.amount_sats + alloc.accrued_yield) / total
            if abs(current_pct - target_pct) > self.config.rebalance_threshold:
                alloc.entry_time = time.time()
        return True

    def _get_strategy_apy(self, strategy: StrategyType) -> float:
        """Retorna APY esperado por estratégia (baseado no risk tolerance)."""
        base_apys = {
            StrategyType.HODL: 0.0,
            StrategyType.STAKING: 7.0,
            StrategyType.LENDING: 12.0,
            StrategyType.LP_PROVIDE: 18.0,
            StrategyType.COMPOUND: 15.0,
        }
        base = base_apys.get(strategy, 0.0)
        risk_mult = 0.5 + self.config.risk_tolerance
        return base * risk_mult

    def check_stop_loss(self) -> bool:
        """Verifica se stop loss foi atingido."""
        if self.deposits_total <= 0:
            return False
        loss_pct = 1 - (self.total_value / max(self.deposits_total - self.withdrawals_total, 1))
        return loss_pct > self.config.stop_loss_pct

    def to_dict(self) -> dict:
        return {
            "agent_id": self.config.agent_id,
            "total_value_bait": self.total_value / 100_000_000,
            "total_yield_bait": self.total_yield / 100_000_000,
            "net_pnl_bait": self.net_pnl / 100_000_000,
            "strategies": [
                {"strategy": a.strategy.value, "amount": a.amount_sats, "apy": a.apy}
                for a in self.allocations
            ],
            "tx_count": len(self._tx_history),
        }
