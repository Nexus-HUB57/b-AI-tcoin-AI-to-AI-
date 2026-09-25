"""Versioned mining work templates and idempotent external submissions.

This module only creates work, verifies shares and admits block candidates for
later application. It never appends blocks, mints rewards, signs payouts or
broadcasts to peers.
"""
from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional

from baitcoin_core.blockchain.block import Block, BlockHeader, Transaction, TransactionOutput
from baitcoin_core.consensus.block_validation import BlockValidationResult, CandidateBlockValidator


@dataclass(frozen=True)
class WorkTemplate:
    template_id: str
    network: str
    chain_id: str
    height: int
    prev_hash: str
    bits: int
    target: int
    share_target: int
    base_hash: str
    coinbase_value_sats: int
    created_at: float
    expires_at: float
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "network": self.network,
            "chain_id": self.chain_id,
            "height": self.height,
            "prev_hash": self.prev_hash,
            "bits": hex(self.bits),
            "target": hex(self.target),
            "share_target": hex(self.share_target),
            "base_hash": self.base_hash,
            "coinbase_value_sats": self.coinbase_value_sats,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "version": self.version,
        }


@dataclass(frozen=True)
class ShareSubmission:
    template_id: str
    miner_id: str
    nonce: int
    extra_nonce: str = ""
    tensor_commitment: str = ""
    proof_hash: str = ""

    def idempotency_key(self) -> str:
        raw = f"{self.template_id}:{self.miner_id}:{self.nonce}:{self.extra_nonce}"
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class ShareResult:
    status: str
    reason: str = ""
    share_id: str = ""
    is_block_solution: bool = False


@dataclass(frozen=True)
class BlockSubmissionResult:
    status: str
    reason: str = ""
    validation: Optional[BlockValidationResult] = None


@dataclass
class _TemplateState:
    template: WorkTemplate
    block: Block
    accepted_shares: set[str]
    accepted_blocks: set[str]


class WorkTemplateManager:
    """Create and verify short-lived work without applying candidates."""

    def __init__(
        self,
        blockchain,
        *,
        network: str = "baitcoin-testnet",
        chain_id: str = "local-chain",
        template_ttl_seconds: int = 60,
        share_target: Optional[int] = None,
        clock=time.time,
    ):
        self.blockchain = blockchain
        self.network = network
        self.chain_id = chain_id
        self.template_ttl_seconds = template_ttl_seconds
        self.share_target = share_target
        self.clock = clock
        self._templates: Dict[str, _TemplateState] = {}
        self._validator = CandidateBlockValidator(blockchain)

    def create_template(self, miner_id: str, payout_script: bytes, *, now: Optional[float] = None) -> WorkTemplate:
        if not miner_id:
            raise ValueError("miner_id is required")
        if not payout_script:
            raise ValueError("payout_script is required")
        now = self.clock() if now is None else now
        height = self.blockchain.height + 1
        reward = self.blockchain.get_block_reward(height)
        tx = Transaction(
            tx_type="coinbase",
            outputs=[TransactionOutput(amount_sats=reward, script_pubkey=payout_script)],
            agent_id=miner_id,
            timestamp=now,
        )
        block = Block(
            index=height,
            header=BlockHeader(
                prev_block_hash=self.blockchain.last_block.block_hash,
                bits=self.blockchain.consensus.target_bits,
                timestamp=now,
                agent_validator=miner_id,
            ),
            transactions=[tx],
        )
        block.finalize()
        template_id = uuid.uuid4().hex
        template = WorkTemplate(
            template_id=template_id,
            network=self.network,
            chain_id=self.chain_id,
            height=height,
            prev_hash=block.header.prev_block_hash.hex(),
            bits=block.header.bits,
            target=self.blockchain.consensus.target,
            share_target=self.share_target or self.blockchain.consensus.target,
            base_hash=block.block_hash.hex(),
            coinbase_value_sats=reward,
            created_at=now,
            expires_at=now + self.template_ttl_seconds,
        )
        self._templates[template_id] = _TemplateState(template, block, set(), set())
        return template

    def submit_share(self, submission: ShareSubmission, *, now: Optional[float] = None) -> ShareResult:
        state = self._templates.get(submission.template_id)
        if state is None:
            return ShareResult("rejected", "unknown template")
        now = self.clock() if now is None else now
        if now >= state.template.expires_at:
            return ShareResult("rejected", "template expired")
        if not submission.miner_id or not 0 <= submission.nonce <= 0xFFFFFFFFFFFFFFFF:
            return ShareResult("rejected", "invalid miner or nonce")
        share_id = submission.idempotency_key()
        if share_id in state.accepted_shares:
            return ShareResult("duplicate", "share already accepted", share_id=share_id)

        consensus = self.blockchain.consensus
        base_hash = bytes.fromhex(state.template.base_hash)
        expected_tensor = consensus.generate_tensor_commitment(base_hash, submission.nonce)
        expected_proof = consensus.generate_zk_proof(base_hash, expected_tensor, submission.nonce)
        if submission.tensor_commitment != expected_tensor.hex() or submission.proof_hash != expected_proof.hex():
            return ShareResult("rejected", "commitment does not match template", share_id=share_id)
        if int.from_bytes(expected_proof, "big") > state.template.share_target:
            return ShareResult("rejected", "share does not meet share target", share_id=share_id)

        state.accepted_shares.add(share_id)
        return ShareResult(
            "accepted",
            share_id=share_id,
            is_block_solution=int.from_bytes(expected_proof, "big") <= state.template.target,
        )

    def submit_block(self, template_id: str, block: Block, *, now: Optional[float] = None) -> BlockSubmissionResult:
        state = self._templates.get(template_id)
        if state is None:
            return BlockSubmissionResult("rejected", "unknown template")
        template = state.template
        now = self.clock() if now is None else now
        if now >= template.expires_at:
            return BlockSubmissionResult("rejected", "template expired")
        if block.index != template.height or block.header.prev_block_hash.hex() != template.prev_hash:
            return BlockSubmissionResult("rejected", "block does not match template")
        if block.header.bits != template.bits:
            return BlockSubmissionResult("rejected", "block bits do not match template")
        if block.header.agent_validator != state.block.header.agent_validator:
            return BlockSubmissionResult("rejected", "block validator does not match template")
        if not block.transactions or block.transactions[0].tx_id != state.block.transactions[0].tx_id:
            return BlockSubmissionResult("rejected", "coinbase does not match template")
        block_id = block.block_hash.hex()
        if block_id in state.accepted_blocks:
            return BlockSubmissionResult("duplicate", "block already admitted")
        result = self._validator.validate(block)
        if not result.valid:
            return BlockSubmissionResult("rejected", result.reason, result)
        state.accepted_blocks.add(block_id)
        return BlockSubmissionResult("accepted", validation=result)

    def get_template(self, template_id: str) -> Optional[WorkTemplate]:
        state = self._templates.get(template_id)
        return state.template if state else None

    def expire(self, *, now: Optional[float] = None) -> int:
        now = self.clock() if now is None else now
        expired = [key for key, state in self._templates.items() if now >= state.template.expires_at]
        for key in expired:
            del self._templates[key]
        return len(expired)
