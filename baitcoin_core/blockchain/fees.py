r"""
b'AI'tcoin Fee Market — Dynamic gas pricing and mempool prioritization.

Implements a fee market similar to Bitcoin's:
- Minimum fee rate (floor)
- Dynamic fee estimation based on mempool congestion
- Mempool sorting by fee rate (fee per virtual byte)
- Block space limit with fee-based prioritization

Fee calculation:
  base_fee = min_fee_rate * tx_size
  priority_fee = (fee_rate - min_fee_rate) * tx_size
  total_fee = base_fee + priority_fee

The mempool is sorted by fee_rate descending. When mining a block,
transactions are included in fee-rate order until block weight limit is reached.
"""

import time
from typing import List, Optional, Tuple
from baitcoin_core.blockchain.block import Transaction


# Protocol constants
MIN_FEE_RATE = 1           # satoshis per virtual byte (floor)
DEFAULT_FEE_RATE = 10      # satoshis per vbyte (default if not specified)
MAX_FEE_RATE = 1_000_000   # cap to prevent absurd fees
BLOCK_MAX_WEIGHT = 4_000_000  # 4M weight units (= 4MB at 1 weight/byte)
NON_COINBASE_TX_WEIGHT = 500  # approximate weight per non-coinbase tx
BASE_TX_SIZE = 100         # approximate bytes for a simple transfer


class FeeEstimator:
    r"""Estimates appropriate fees based on mempool state."""

    def __init__(self, min_fee_rate: int = MIN_FEE_RATE):
        self.min_fee_rate = min_fee_rate
        # Fee rate history for estimation (last N blocks)
        self._block_fee_rates: List[float] = []
        self._max_history = 20

    def record_block_fees(self, median_fee_rate: float) -> None:
        r"""Record the median fee rate of a mined block for future estimates."""
        self._block_fee_rates.append(median_fee_rate)
        if len(self._block_fee_rates) > self._max_history:
            self._block_fee_rates.pop(0)

    def estimate_fee(self, target_confirmations: int = 1) -> int:
        r"""Estimate fee rate for a given target number of confirmations.

        For target_confirmations=1, use the median of recent block fees.
        For higher targets, use a lower percentile.
        Always returns at least min_fee_rate.
        """
        if not self._block_fee_rates:
            return DEFAULT_FEE_RATE

        sorted_rates = sorted(self._block_fee_rates)
        n = len(sorted_rates)

        if target_confirmations <= 1:
            # Median for next block
            idx = n // 2
        elif target_confirmations <= 3:
            # 25th percentile
            idx = max(0, n // 4)
        else:
            # Minimum observed
            idx = 0

        estimated = int(sorted_rates[idx])
        return max(estimated, self.min_fee_rate)

    def get_fee_histogram(self) -> List[dict]:
        r"""Return fee rate distribution for the mempool UI."""
        if not self._block_fee_rates:
            return []
        return [
            {"block_ago": i + 1, "median_fee_rate": rate}
            for i, rate in enumerate(reversed(self._block_fee_rates))
        ]


class MempoolEntry:
    r"""A transaction in the mempool with fee metadata."""

    def __init__(self, tx: Transaction, fee_rate: int, added_at: float = 0):
        self.tx = tx
        self.fee_rate = max(fee_rate, MIN_FEE_RATE)
        self.added_at = added_at or time.time()
        self.tx_size = self._estimate_size(tx)
        self.total_fee = self.fee_rate * self.tx_size

    @staticmethod
    def _estimate_size(tx: Transaction) -> int:
        r"""Estimate virtual size of a transaction in bytes."""
        # Base size + inputs + outputs
        size = BASE_TX_SIZE
        size += len(tx.inputs) * 148  # each input ~148 bytes (prev_tx + sig)
        size += len(tx.outputs) * 34  # each output ~34 bytes
        size += len(tx.payload)       # payload bytes
        return max(size, BASE_TX_SIZE)

    def __lt__(self, other: 'MempoolEntry') -> bool:
        # Higher fee rate = higher priority (sort descending)
        return self.fee_rate > other.fee_rate

    def __repr__(self) -> str:
        return f"MempoolEntry(tx={self.tx.tx_id.hex()[:16]}..., fee_rate={self.fee_rate}, size={self.tx_size})"


class FeeMarket:
    r"""Manages the mempool with fee-based prioritization.

    Transactions are added with a fee_rate. The mempool is sorted
    by fee_rate descending. When selecting transactions for a block,
    they are picked in order until the block weight limit is reached.
    """

    def __init__(self, min_fee_rate: int = MIN_FEE_RATE,
                 block_max_weight: int = BLOCK_MAX_WEIGHT):
        self.min_fee_rate = min_fee_rate
        self.block_max_weight = block_max_weight
        self.entries: List[MempoolEntry] = []
        self.estimator = FeeEstimator(min_fee_rate)
        self._total_fees_collected = 0
        self._tx_count = 0

    def add_transaction(self, tx: Transaction, fee_rate: int = DEFAULT_FEE_RATE) -> Tuple[bool, str]:
        r"""Add a transaction to the mempool with its fee rate.

        Returns:
            (success, reason) tuple.
        """
        if tx.is_coinbase:
            return False, "Coinbase transactions cannot be in mempool"

        if fee_rate < self.min_fee_rate:
            return False, f"Fee rate {fee_rate} below minimum {self.min_fee_rate}"

        if fee_rate > MAX_FEE_RATE:
            return False, f"Fee rate {fee_rate} exceeds maximum {MAX_FEE_RATE}"

        # Check for duplicate
        for entry in self.entries:
            if entry.tx.tx_id == tx.tx_id:
                return False, "Transaction already in mempool"

        entry = MempoolEntry(tx, fee_rate)
        self.entries.append(entry)
        # Keep sorted by fee_rate descending
        self.entries.sort()

        return True, ""

    def remove_transaction(self, tx_id: bytes) -> Optional[MempoolEntry]:
        r"""Remove a transaction from the mempool (after inclusion in a block)."""
        for i, entry in enumerate(self.entries):
            if entry.tx.tx_id == tx_id:
                return self.entries.pop(i)
        return None

    def select_transactions(self, max_weight: Optional[int] = None) -> Tuple[List[Transaction], int, float]:
        r"""Select transactions for the next block, prioritized by fee rate.

        Returns:
            (transactions, total_fees, median_fee_rate)
        """
        max_w = max_weight or self.block_max_weight
        selected = []
        total_weight = 0
        total_fees = 0
        fee_rates = []

        for entry in self.entries:
            tx_weight = entry.tx_size  # simplified: 1 weight per byte
            if total_weight + tx_weight > max_w:
                continue
            selected.append(entry.tx)
            total_weight += tx_weight
            total_fees += entry.total_fee
            fee_rates.append(entry.fee_rate)

        # Calculate median fee rate
        median_rate = self.min_fee_rate
        if fee_rates:
            sorted_fr = sorted(fee_rates)
            median_rate = sorted_fr[len(sorted_fr) // 2]

        return selected, total_fees, median_rate

    def prune_selected(self, selected_txs: List[Transaction]) -> int:
        r"""Remove selected transactions from mempool and record fees."""
        selected_ids = {tx.tx_id for tx in selected_txs}
        remaining = []
        for entry in self.entries:
            if entry.tx.tx_id in selected_ids:
                self._total_fees_collected += entry.total_fee
                self._tx_count += 1
            else:
                remaining.append(entry)
        self.entries = remaining
        return len(selected_ids)

    def record_block_median(self, median_fee_rate: float) -> None:
        r"""Record block fee data for estimation."""
        self.estimator.record_block_fees(median_fee_rate)

    def estimate_fee(self, target_confirmations: int = 1) -> int:
        r"""Estimate fee rate for desired confirmation speed."""
        return self.estimator.estimate_fee(target_confirmations)

    @property
    def size(self) -> int:
        return len(self.entries)

    @property
    def total_fees_collected(self) -> int:
        return self._total_fees_collected

    def to_dict(self) -> dict:
        r"""Mempool status for API responses."""
        if not self.entries:
            return {
                "size": 0,
                "min_fee_rate": self.min_fee_rate,
                "estimated_fee_1block": self.estimate_fee(1),
                "estimated_fee_3blocks": self.estimate_fee(3),
                "total_fees_collected": self._total_fees_collected,
                "fee_histogram": [],
            }
        fee_rates = [e.fee_rate for e in self.entries]
        return {
            "size": len(self.entries),
            "min_fee_rate": self.min_fee_rate,
            "estimated_fee_1block": self.estimate_fee(1),
            "estimated_fee_3blocks": self.estimate_fee(3),
            "total_fees_collected": self._total_fees_collected,
            "fee_histogram": self.estimator.get_fee_histogram(),
            "current_min": min(fee_rates) if fee_rates else 0,
            "current_max": max(fee_rates) if fee_rates else 0,
            "current_median": sorted(fee_rates)[len(fee_rates) // 2] if fee_rates else 0,
        }
