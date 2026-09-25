"""Deterministic admission checks for externally mined block candidates.

This module is intentionally side-effect free. It validates a candidate against
an existing chain state but never appends the block, updates UTXOs, pays a
miner, or broadcasts anything. Applying a candidate remains an explicit later
step in the sync/reorg layer.
"""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Optional

from baitcoin_core.blockchain.block import Block
from baitcoin_core.blockchain.tx_verifier import TransactionVerifier


@dataclass(frozen=True)
class BlockValidationResult:
    valid: bool
    reason: str = ""
    fees_sats: int = 0

    def __bool__(self) -> bool:
        return self.valid


class CandidateBlockValidator:
    """Validate a candidate without mutating the chain or consensus state."""

    MAX_FUTURE_SECONDS = 2 * 60 * 60

    def __init__(self, blockchain, *, require_pow: bool = True):
        self.blockchain = blockchain
        self.require_pow = require_pow

    def validate(self, block: Block) -> BlockValidationResult:
        chain = self.blockchain
        if not isinstance(block, Block):
            return BlockValidationResult(False, "candidate is not a Block")
        if block.index != chain.height + 1:
            return BlockValidationResult(False, "candidate height is not the next height")
        if block.header.prev_block_hash != chain.last_block.block_hash:
            return BlockValidationResult(False, "candidate parent does not match current tip")
        if block.header.timestamp < chain.last_block.header.timestamp:
            return BlockValidationResult(False, "candidate timestamp precedes parent")
        if block.header.timestamp > time.time() + self.MAX_FUTURE_SECONDS:
            return BlockValidationResult(False, "candidate timestamp is too far in the future")
        if block.header.version < 1:
            return BlockValidationResult(False, "unsupported block version")
        if len(block.header.prev_block_hash) != 32 or len(block.header.merkle_root) != 32:
            return BlockValidationResult(False, "invalid header hash length")
        if block.header.merkle_root != block.compute_merkle_root():
            return BlockValidationResult(False, "invalid merkle root")

        coinbases = [tx for tx in block.transactions if tx.is_coinbase]
        if len(coinbases) != 1:
            return BlockValidationResult(False, "candidate must contain exactly one coinbase")
        if block.transactions[0] is not coinbases[0]:
            return BlockValidationResult(False, "coinbase must be the first transaction")
        if not coinbases[0].outputs or any(out.amount_sats < 0 for out in coinbases[0].outputs):
            return BlockValidationResult(False, "coinbase outputs are invalid")
        if len({tx.tx_id for tx in block.transactions}) != len(block.transactions):
            return BlockValidationResult(False, "duplicate transaction id")

        fees_sats = self._validate_transactions(block)
        if fees_sats is None:
            return BlockValidationResult(False, "candidate contains an invalid transaction")
        reward_limit = chain.get_block_reward(block.index) + fees_sats
        coinbase_value = sum(out.amount_sats for out in coinbases[0].outputs)
        if coinbase_value > reward_limit:
            return BlockValidationResult(False, "coinbase exceeds reward plus fees")

        if self.require_pow and not self._validate_pow(block):
            return BlockValidationResult(False, "invalid proof of work")
        return BlockValidationResult(True, fees_sats=fees_sats)

    def _validate_transactions(self, block: Block) -> Optional[int]:
        verifier = TransactionVerifier(
            copy.deepcopy(self.blockchain.utxo_set),
            self.blockchain.height,
        )
        fees = 0
        for tx in block.transactions:
            if tx.is_coinbase:
                continue
            result = verifier.verify(tx)
            if not result.valid:
                return None
            fees += result.fee
        return fees

    def _validate_pow(self, block: Block) -> bool:
        consensus = self.blockchain.consensus
        if block.header.bits != consensus.target_bits:
            return False
        if len(block.header.tensor_commitment) != 32 or len(block.header.zkml_proof_hash) != 32:
            return False

        # The legacy miner derives commitments from a stable header hash with
        # nonce zero and varies the nonce only in the proof input. Preserve that
        # rule explicitly until the versioned external-mining header is frozen.
        header = copy.deepcopy(block.header)
        header.nonce = 0
        header.tensor_commitment = b"\x00" * 32
        header.zkml_proof_hash = b"\x00" * 32
        base_block = Block(index=block.index, header=header, transactions=block.transactions)
        base_hash = base_block.block_hash
        return consensus.validate_proof(
            base_hash,
            block.header.tensor_commitment,
            block.header.zkml_proof_hash,
            block.header.nonce,
        )


def validate_candidate_block(blockchain, block: Block, *, require_pow: bool = True) -> BlockValidationResult:
    """Convenience wrapper for read-only candidate validation."""
    return CandidateBlockValidator(blockchain, require_pow=require_pow).validate(block)
