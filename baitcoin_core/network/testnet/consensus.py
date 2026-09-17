r"""Testnet Consensus — Deterministic consensus for local test network.

Implements a simplified, deterministic consensus protocol designed
specifically for testnet environments where reliability and speed
matter more than Byzantine fault tolerance:

- **Round-Robin Validation**: Each validator takes turns producing blocks
  in a deterministic rotation order, eliminating competition and orphan blocks.
- **Instant Finality**: A block is finalized immediately upon production
  since there is only one producer per slot. No reorgs, no confirmations needed.
- **Reduced Difficulty**: Mining difficulty is set to minimum, allowing blocks
  to be produced at the configured interval (default 2s) without real PoW.
- **Virtual PoUW**: While PoW is not required, the consensus engine records
  a simulated PoUW hash to maintain compatibility with the mainnet block format.
- **Supermajority Liveness**: Requires >2/3 of validators online to produce
  blocks, preventing single-node forks.

This design mirrors the approach of testnets like Goerli (Ethereum) and
Signet (Bitcoin) which also use deterministic block production for
testing reliability.

Mathematical Model:
    Given N validators, block at slot s is produced by validator:
        producer(s) = s mod N
    Finality is instant because:
        P(fork) = 0  (single producer per slot)

Usage::

    consensus = TestnetConsensus(
        validator_ids=["v0", "v1", "v2", "v3", "v4"],
        block_interval=2.0,
    )
    block = consensus.produce_block()
    print(block[\"height\"])  # 0
    block = consensus.produce_block()
    print(block[\"height\"])  # 1
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TestnetBlock:
    r"""A block produced by testnet consensus.

    Maintains the same structure as mainnet blocks for compatibility
    but uses simplified fields where mainnet would require PoW.
    """
    height: int
    prev_hash: str
    timestamp: float
    producer_id: str
    txs: List[dict] = field(default_factory=list)
    hash: str = ""
    zkml_proof_hash: str = ""
    pouw_work_hash: str = ""
    tensor_commitment: str = ""
    nonce: int = 0
    merkle_root: str = ""

    def compute_hash(self) -> str:
        r"""Compute deterministic SHA-256d block hash."""
        header = json.dumps({
            "height": self.height,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "producer_id": self.producer_id,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "zkml_proof_hash": self.zkml_proof_hash,
            "pouw_work_hash": self.pouw_work_hash,
            "tensor_commitment": self.tensor_commitment,
        }, sort_keys=True)
        return hashlib.sha256(
            hashlib.sha256(header.encode()).hexdigest().encode()
        ).hexdigest()

    def compute_merkle_root(self) -> str:
        r"""Compute binary Merkle root of transaction hashes."""
        if not self.txs:
            return hashlib.sha256(b"empty").hexdigest()

        tx_hashes = [tx.get("tx_id", hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()) for tx in self.txs]

        while len(tx_hashes) > 1:
            next_level = []
            for i in range(0, len(tx_hashes), 2):
                left = tx_hashes[i]
                right = tx_hashes[i + 1] if i + 1 < len(tx_hashes) else left
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                next_level.append(combined)
            tx_hashes = next_level

        return tx_hashes[0]

    def to_dict(self) -> dict:
        r"""Serialize block to dictionary."""
        return {
            "height": self.height,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "timestamp": self.timestamp,
            "producer_id": self.producer_id,
            "transactions": self.txs,
            "tx_count": len(self.txs),
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "zkml_proof_hash": self.zkml_proof_hash,
            "pouw_work_hash": self.pouw_work_hash,
            "tensor_commitment": self.tensor_commitment,
            "size_bytes": 0,
        }


@dataclass
class ValidatorState:
    r"""Tracks the state of a validator in the testnet."""
    validator_id: str
    blocks_produced: int = 0
    last_production_time: float = 0.0
    is_active: bool = True
    missed_slots: int = 0
    total_txs_included: int = 0


class TestnetConsensus:
    r"""Deterministic testnet consensus engine.

    Implements round-robin block production with instant finality.
    Each slot is assigned to exactly one validator, eliminating
    the possibility of forks entirely.

    Parameters
    ----------
    validator_ids : List[str]
        Ordered list of validator agent IDs (determines rotation)
    block_interval : float
        Target seconds between blocks (default 2.0)
    min_active_validators : float
        Fraction of validators that must be active (default 0.67 = 2/3)
    """

    def __init__(
        self,
        validator_ids: List[str],
        block_interval: float = 2.0,
        min_active_validators: float = 0.67,
    ):
        self.validator_ids = validator_ids
        self.block_interval = block_interval
        self.min_active_fraction = min_active_validators
        self.min_active_count = max(1, int(len(validator_ids) * min_active_validators))

        # Chain state
        self.current_height: int = -1
        self.tip_hash: str = hashlib.sha256(b"testnet-genesis").hexdigest()
        self.chain: List[TestnetBlock] = []
        self._block_by_hash: Dict[str, TestnetBlock] = {}

        # Mempool (testnet simplified)
        self.mempool: List[dict] = []
        self.max_txs_per_block: int = 100

        # Validator tracking
        self.validators: Dict[str, ValidatorState] = {
            vid: ValidatorState(validator_id=vid) for vid in validator_ids
        }

        # Metrics
        self._total_slots = 0
        self._total_missed = 0
        self._start_time = time.time()

    def produce_block(self) -> Optional[dict]:
        r"""Produce the next block in the chain.

        The producer is determined by round-robin: producer = height mod N.
        If the assigned validator is inactive, the slot is skipped
        (height advances but no block is produced).

        Returns
        -------
        dict or None
            Block data dict if produced, None if slot skipped.
        """
        # Check liveness requirement
        active_count = sum(1 for v in self.validators.values() if v.is_active)
        if active_count < self.min_active_count:
            self._total_missed += 1
            self._total_slots += 1
            return None

        # Try to find an active producer (scan up to N slots)
        for attempt in range(len(self.validator_ids)):
            self._total_slots += 1
            next_height = self.current_height + 1

            # Determine producer (round-robin)
            producer_idx = next_height % len(self.validator_ids)
            producer_id = self.validator_ids[producer_idx]
            validator = self.validators[producer_id]

            if not validator.is_active:
                validator.missed_slots += 1
                self._total_missed += 1
                self.current_height = next_height  # Advance height even on skip
                continue

            # Select transactions from mempool
            block_txs = self.mempool[:self.max_txs_per_block]
            self.mempool = self.mempool[self.max_txs_per_block:]

            # Create block
            block = TestnetBlock(
                height=next_height,
                prev_hash=self.tip_hash,
                timestamp=time.time(),
                producer_id=producer_id,
                txs=block_txs,
                nonce=next_height,  # Deterministic nonce
            )

            # Compute merkle root and hash
            block.merkle_root = block.compute_merkle_root()
            block.zkml_proof_hash = hashlib.sha256(
                f"zkml-testnet-{next_height}".encode()
            ).hexdigest()
            block.pouw_work_hash = hashlib.sha256(
                f"pouw-testnet-{next_height}".encode()
            ).hexdigest()
            block.tensor_commitment = hashlib.sha256(
                f"tensor-testnet-{next_height}".encode()
            ).hexdigest()
            block.hash = block.compute_hash()

            # Update state
            self.chain.append(block)
            self._block_by_hash[block.hash] = block
            self.tip_hash = block.hash
            self.current_height = next_height

            # Update validator metrics
            validator.blocks_produced += 1
            validator.last_production_time = time.time()
            validator.total_txs_included += len(block_txs)

            return block.to_dict()

        return None  # All validators inactive in this round

    def add_transaction(self, tx_data: dict) -> bool:
        r"""Add a transaction to the testnet mempool.

        Deduplicates by tx_id. Returns True if added, False if duplicate.
        """
        tx_id = tx_data.get("tx_id", "")
        if not tx_id:
            tx_id = hashlib.sha256(
                json.dumps(tx_data, sort_keys=True).encode()
            ).hexdigest()
            tx_data["tx_id"] = tx_id

        for existing in self.mempool:
            if existing.get("tx_id") == tx_id:
                return False
        self.mempool.append(tx_data)
        return True

    def get_block(self, height: int = None, block_hash: str = None) -> Optional[dict]:
        r"""Retrieve a block by height or hash."""
        if block_hash:
            block = self._block_by_hash.get(block_hash)
            return block.to_dict() if block else None
        if height is not None:
            if 0 <= height < len(self.chain):
                return self.chain[height].to_dict()
        return None

    def get_block_range(self, start: int, end: int) -> List[dict]:
        r"""Get a range of blocks [start, end)."""
        return [
            self.chain[i].to_dict()
            for i in range(max(0, start), min(end, len(self.chain)))
        ]

    def set_validator_active(self, validator_id: str, active: bool) -> None:
        r"""Activate or deactivate a validator."""
        if validator_id in self.validators:
            self.validators[validator_id].is_active = active

    def get_validator_status(self) -> Dict[str, dict]:
        r"""Get status of all validators."""
        return {
            vid: {
                "blocks_produced": v.blocks_produced,
                "is_active": v.is_active,
                "missed_slots": v.missed_slots,
                "total_txs_included": v.total_txs_included,
                "last_production_time": v.last_production_time,
                "participation_rate": (
                    v.blocks_produced / max(1, self._total_slots) * 100
                ),
            }
            for vid, v in self.validators.items()
        }

    def to_dict(self) -> dict:
        r"""Export consensus state."""
        return {
            "current_height": self.current_height,
            "tip_hash": self.tip_hash,
            "total_blocks": len(self.chain),
            "mempool_size": len(self.mempool),
            "validators": len(self.validators),
            "active_validators": sum(
                1 for v in self.validators.values() if v.is_active
            ),
            "total_slots": self._total_slots,
            "missed_slots": self._total_missed,
            "participation_rate": (
                (self._total_slots - self._total_missed)
                / max(1, self._total_slots) * 100
            ),
            "block_interval": self.block_interval,
            "uptime_seconds": time.time() - self._start_time,
        }
