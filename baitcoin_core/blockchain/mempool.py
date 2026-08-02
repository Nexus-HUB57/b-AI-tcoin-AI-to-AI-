r"""
Mempool b'AI'tcoin - Pool de transações pendentes.

Gerencia transações aguardando inclusão em blocos.
Implementa priorização por gas price e validação antecipada.
"""

import time
import bisect
from typing import List, Optional, Dict
from collections import defaultdict
from baitcoin_core.blockchain.block import Transaction


class Mempool:
    """Pool de transações pendentes do b'AI'tcoin.

    Funcionalidades:
    - FIFO com priorização por gas price
    - Limite de tamanho configurável
    - Dedupe por tx_id
    - Taxa de entrada/saída por agente
    - Evicção de transações expiradas
    """

    MAX_SIZE = 50_000
    MAX_TX_SIZE_BYTES = 100_000
    TX_EXPIRY_SECONDS = 3600

    def __init__(self):
        self._transactions: Dict[str, Transaction] = {}
        self._by_agent: Dict[str, List[str]] = defaultdict(list)
        self._by_fee: List[str] = []
        self._by_fee_neg_fees: List[int] = []  # Negated fees para bisect (ordem decrescente)
        self._total_fees_sats = 0
        self._stats = {"added": 0, "removed": 0, "expired": 0}

    @property
    def size(self) -> int:
        return len(self._transactions)

    @property
    def total_fees(self) -> int:
        return self._total_fees_sats
    def add_transaction(self, tx: Transaction) -> bool:
        """Adiciona transação ao mempool."""
        tx_id = tx.tx_id.hex()
        if tx_id in self._transactions:
            return False
        if self.size >= self.MAX_SIZE:
            self._evict_lowest_fee()
        if len(tx.payload) > self.MAX_TX_SIZE_BYTES:
            return False
        self._transactions[tx_id] = tx
        self._by_agent[tx.agent_id].append(tx_id)
        self._insert_by_fee(tx_id, tx.gas_price * tx.gas_limit)
        self._total_fees_sats += tx.gas_price * tx.gas_limit
        self._stats["added"] += 1
        return True

    def _insert_by_fee(self, tx_id: str, fee: int) -> None:
        r"""Insere na lista ordenada por fee (maior primeiro) via binary search."""
        # Negate fee para ordem decrescente com bisect
        neg_fee = -fee
        pos = bisect.bisect_left(self._by_fee_neg_fees, neg_fee)
        self._by_fee.insert(pos, tx_id)
        self._by_fee_neg_fees.insert(pos, neg_fee)

    def get_transactions(self, max_count: int = 1000, min_fee_rate: int = 0) -> List[Transaction]:
        """Retorna transações priorizadas por fee."""
        result = []
        for tx_id in self._by_fee:
            tx = self._transactions[tx_id]
            effective_fee = tx.gas_price * tx.gas_limit / max(len(tx.payload), 1)
            if effective_fee >= min_fee_rate:
                result.append(tx)
            if len(result) >= max_count:
                break
        return result

    def remove_transactions(self, tx_ids: List[str]) -> None:
        """Remove transações do mempool após inclusão em bloco."""
        for tx_id in tx_ids:
            tx = self._transactions.pop(tx_id, None)
            if tx:
                idx = self._by_fee.index(tx_id) if tx_id in self._by_fee else -1
                if idx >= 0:
                    self._by_fee.pop(idx)
                    self._by_fee_neg_fees.pop(idx)
                self._by_agent[tx.agent_id].remove(tx_id)
                self._total_fees_sats -= tx.gas_price * tx.gas_limit
                self._stats["removed"] += 1

    def _evict_lowest_fee(self) -> None:
        """Remove a transação com menor fee."""
        if self._by_fee:
            lowest = self._by_fee.pop()  # Ultimo = menor fee
            self._by_fee_neg_fees.pop()  # Sincronizar
            tx = self._transactions.pop(lowest, None)
            if tx:
                self._by_agent[tx.agent_id].remove(lowest)
                self._stats["removed"] += 1

    def purge_expired(self) -> int:
        """Remove transações expiradas."""
        now = time.time()
        expired = [
            tid for tid, tx in self._transactions.items()
            if now - tx.timestamp > self.TX_EXPIRY_SECONDS
        ]
        self.remove_transactions(expired)
        self._stats["expired"] += len(expired)
        return len(expired)

    def get_agent_txs(self, agent_id: str) -> List[Transaction]:
        """Retorna todas transações de um agente."""
        return [self._transactions[tid] for tid in self._by_agent.get(agent_id, [])]

    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "total_fees_sats": self._total_fees_sats,
            "max_size": self.MAX_SIZE,
            "agents": len(self._by_agent),
            "stats": self._stats,
        }
