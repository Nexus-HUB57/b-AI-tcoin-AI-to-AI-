r"""
Token BAIT - Implementação ERC-20 like para b'AI'tcoin.

Características:
- Supply total: 21.000.000 BAIT (como Bitcoin)
- 8 casas decimais (s'AI'toshis)
- Transferências AI-to-AI com metadata
- Approval pattern para delegação
- Events (log de transferências)
"""

import hashlib
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class TokenEvent(Enum):
    TRANSFER = "transfer"
    APPROVAL = "approval"
    MINT = "mint"
    BURN = "burn"


@dataclass
class TokenLog:
    """Log de evento on-chain."""
    event_type: TokenEvent
    from_agent: str
    to_agent: str
    amount_sats: int
    timestamp: float = field(default_factory=time.time)
    tx_hash: str = ""
    memo: str = ""


class BAITToken:
    r"""Token BAIT (b'AI'tcoin).

    Total Supply: 21.000.000 BAIT
    Decimals: 8
    Unit: BAIT (100.000.000 s'AI'toshis)

    Distribuição inicial:
    - 40% Mineração (block rewards)
    - 20% Staking rewards
    - 15% Treasury / ecossistema
    - 15% Comunidade / airdrops
    - 10% Fundadores / early contributors
    """

    TOTAL_SUPPLY_SATS = 21_000_000 * 100_000_000
    DECIMALS = 8
    SATS_PER_BAIT = 100_000_000

    def __init__(self):
        self.balances: Dict[str, int] = {}
        self.allowances: Dict[str, Dict[str, int]] = {}
        self.total_minted: int = 0
        self.total_burned: int = 0
        self.event_log: List[TokenLog] = []
        self._nonces: Dict[str, int] = {}

    @property
    def circulating_supply(self) -> int:
        return self.total_minted - self.total_burned

    @property
    def circulating_bait(self) -> float:
        return self.circulating_supply / self.SATS_PER_BAIT

    @property
    def max_supply_bait(self) -> float:
        return self.TOTAL_SUPPLY_SATS / self.SATS_PER_BAIT

    def mint(self, agent_id: str, amount_sats: int) -> bool:
        r"""Emite novos tokens (só para coinbase/governança)."""
        if self.total_minted + amount_sats > self.TOTAL_SUPPLY_SATS:
            return False
        self.balances[agent_id] = self.balances.get(agent_id, 0) + amount_sats
        self.total_minted += amount_sats
        self._emit(TokenEvent.MINT, "mint", agent_id, amount_sats)
        return True

    def burn(self, agent_id: str, amount_sats: int) -> bool:
        r"""Queima tokens (reduz supply)."""
        if self.balances.get(agent_id, 0) < amount_sats:
            return False
        self.balances[agent_id] -= amount_sats
        self.total_burned += amount_sats
        self._emit(TokenEvent.BURN, agent_id, "burn", amount_sats)
        return True

    def transfer(self, from_agent: str, to_agent: str,
                  amount_sats: int, memo: str = "") -> bool:
        r"""Transfere tokens entre agentes."""
        if self.balances.get(from_agent, 0) < amount_sats:
            return False
        if amount_sats <= 0:
            return False
        self.balances[from_agent] -= amount_sats
        self.balances[to_agent] = self.balances.get(to_agent, 0) + amount_sats
        self._emit(TokenEvent.TRANSFER, from_agent, to_agent, amount_sats, memo)
        return True

    def approve(self, owner: str, spender: str, amount_sats: int) -> bool:
        r"""Aprova que spender gaste até amount_sats do owner."""
        if owner not in self.allowances:
            self.allowances[owner] = {}
        self.allowances[owner][spender] = amount_sats
        self._emit(TokenEvent.APPROVAL, owner, spender, amount_sats)
        return True

    def transfer_from(self, spender: str, from_agent: str,
                       to_agent: str, amount_sats: int) -> bool:
        r"""Transferência via approval."""
        allowed = self.allowances.get(from_agent, {}).get(spender, 0)
        if allowed < amount_sats:
            return False
        self.allowances[from_agent][spender] -= amount_sats
        return self.transfer(from_agent, to_agent, amount_sats)

    def balance_of(self, agent_id: str) -> int:
        r"""Retorna saldo em s'AI'toshis."""
        return self.balances.get(agent_id, 0)

    def balance_bait(self, agent_id: str) -> float:
        r"""Retorna saldo em BAIT."""
        return self.balance_of(agent_id) / self.SATS_PER_BAIT

    def get_nonce(self, agent_id: str) -> int:
        r"""Retorna nonce do agente (para replay protection)."""
        return self._nonces.get(agent_id, 0)

    def _emit(self, event: TokenEvent, from_a: str, to_a: str,
              amount: int, memo: str = "") -> None:
        r"""Emite evento no log."""
        self.event_log.append(TokenLog(
            event_type=event,
            from_agent=from_a,
            to_agent=to_a,
            amount_sats=amount,
            tx_hash=hashlib.sha256(f"{event.value}:{from_a}:{to_a}:{amount}:{time.time()}".encode()).hexdigest()[:16],
            memo=memo,
        ))

    def to_dict(self) -> dict:
        return {
            "name": "BAIT",
            "symbol": "BAIT",
            "decimals": self.DECIMALS,
            "total_supply_bait": self.max_supply_bait,
            "circulating_bait": self.circulating_bait,
            "total_minted_bait": self.total_minted / self.SATS_PER_BAIT,
            "total_burned_bait": self.total_burned / self.SATS_PER_BAIT,
            "holders": len(self.balances),
            "events": len(self.event_log),
        }
