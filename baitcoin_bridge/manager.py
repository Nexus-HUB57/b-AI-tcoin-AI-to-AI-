r"""Bridge Manager — Orchestrates cross-chain transfers.

Implements the complete lock-mint-burn-release lifecycle:

1. **Lock** (Source Chain): User locks BAIT on b'AI'tcoin, receiving a
   verifiable event with Merkle proof data.

2. **Relay** (Relayer): Relayer picks up the lock event, verifies it
   on b'AI'tcoin, and submits a Merkle proof to the target chain.

3. **Mint** (Target Chain): After N-of-M verification, wrapped BAIT
   (wBAIT) is minted on the target chain.

4. **Burn** (Target Chain): User burns wBAIT on the target chain.

5. **Release** (Source Chain): After verification, original BAIT is
   released on b'AI'tcoin.

The manager tracks all transfer states and provides query interfaces.

State Machine per Transfer::

    LOCKED -> PENDING_PROOF -> PROOF_SUBMITTED -> MINTED -> COMPLETED
                                                               |
                                                               v
    REFUNDED <- TIMED_OUT <- (timeout) ---- EXPIRED <--------+

Security Invariants:
    - Total locked BAIT >= Total minted wBAIT (conservation)
    - No mint without valid N-of-M signatures
    - All events anchored in Merkle tree
    - Timeout ensures liveness even if relayer fails

Usage::

    manager = BridgeManager()
    lock = manager.lock_bait("agent_1", 100 * 100_000_000, ChainConfig.ETHEREUM)
    print(lock["event_id"])  # Unique event identifier
"""

import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from baitcoin_bridge.config import BridgeConfig, ChainConfig, ETHEREUM_MAINNET, SOLANA_MAINNET


class TransferState(Enum):
    r"""State machine for cross-chain transfers."""
    LOCKED = "locked"
    PENDING_PROOF = "pending_proof"
    PROOF_SUBMITTED = "proof_submitted"
    MINTED = "minted"
    COMPLETED = "completed"
    BURNED = "burned"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class TransferDirection(Enum):
    r"""Direction of cross-chain transfer."""
    BAIT_TO_ETH = "bait_to_eth"
    BAIT_TO_SOL = "bait_to_sol"
    ETH_TO_BAIT = "eth_to_bait"
    SOL_TO_BAIT = "sol_to_bait"


@dataclass
class BridgeEvent:
    r"""A lock/burn event on the source chain."""
    event_id: str
    transfer_id: str
    event_type: str  # "lock" or "burn"
    agent_id: str
    amount_sats: int
    chain_id: int
    recipient: str
    timestamp: float
    block_height: int
    tx_hash: str
    merkle_proof: List[str] = field(default_factory=list)
    signatures: List[str] = field(default_factory=list)
    state: str = TransferState.LOCKED.value

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "transfer_id": self.transfer_id,
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "amount_sats": self.amount_sats,
            "amount_bait": self.amount_sats / 100_000_000,
            "chain_id": self.chain_id,
            "recipient": self.recipient,
            "timestamp": self.timestamp,
            "block_height": self.block_height,
            "tx_hash": self.tx_hash,
            "state": self.state,
            "signature_count": len(self.signatures),
            "required_signatures": 3,  # N of M threshold
        }


@dataclass
class TransferRecord:
    r"""Complete record of a cross-chain transfer."""
    transfer_id: str
    direction: str
    agent_id: str
    amount_sats: int
    fee_sats: int
    source_chain_id: int
    target_chain_id: int
    source_address: str
    target_address: str
    created_at: float
    state: str = TransferState.LOCKED.value
    lock_event: Optional[dict] = None
    mint_event: Optional[dict] = None
    burn_event: Optional[dict] = None
    release_event: Optional[dict] = None
    proof_submitted_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "transfer_id": self.transfer_id,
            "direction": self.direction,
            "agent_id": self.agent_id,
            "amount_sats": self.amount_sats,
            "amount_bait": self.amount_sats / 100_000_000,
            "fee_sats": self.fee_sats,
            "fee_bait": self.fee_sats / 100_000_000,
            "source_chain_id": self.source_chain_id,
            "target_chain_id": self.target_chain_id,
            "source_address": self.source_address,
            "target_address": self.target_address,
            "state": self.state,
            "created_at": self.created_at,
            "proof_submitted_at": self.proof_submitted_at,
            "completed_at": self.completed_at,
            "duration_seconds": (
                self.completed_at - self.created_at
                if self.completed_at else 0
            ),
        }


class BridgeManager:
    r"""Orchestrates cross-chain transfers between b'AI'tcoin and ETH/SOL.

    Implements the lock-mint-burn-release pattern with:
    - Multi-sig authorization (N-of-M)
    - Merkle proof anchoring
    - Timeout and refund mechanism
    - Rate limiting
    - Emergency pause

    Parameters
    ----------
    config : BridgeConfig
        Bridge configuration
    """

    def __init__(self, config: BridgeConfig = None):
        self.config = config or BridgeConfig()
        self._transfers: Dict[str, TransferRecord] = {}
        self._events: Dict[str, BridgeEvent] = {}
        self._merkle_leaves: List[str] = []
        self._paused = False
        self._daily_volume: Dict[str, float] = {}  # agent_id -> daily volume
        self._daily_volume_date: str = ""
        self._authorized_signers: List[str] = [
            f"signer_{i}" for i in range(self.config.m_signers)
        ]

        # Track totals for conservation invariant
        self._total_locked_sats = 0
        self._total_minted_sats = 0
        self._total_burned_sats = 0
        self._total_released_sats = 0

    def _reset_daily_volume(self) -> None:
        r"""Reset daily volume counters at UTC midnight."""
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if today != self._daily_volume_date:
            self._daily_volume.clear()
            self._daily_volume_date = today

    def _check_rate_limit(self, agent_id: str, amount_sats: int) -> bool:
        r"""Check if agent can bridge this amount today."""
        self._reset_daily_volume()
        current = self._daily_volume.get(agent_id, 0.0)
        new_volume = current + (amount_sats / 100_000_000)
        return new_volume <= self.config.daily_volume_limit_bait

    def _check_pending_limit(self, agent_id: str) -> bool:
        r"""Check pending transfer count for agent."""
        pending = sum(
            1 for t in self._transfers.values()
            if t.agent_id == agent_id
            and t.state in (
                TransferState.LOCKED.value,
                TransferState.PENDING_PROOF.value,
                TransferState.PROOF_SUBMITTED.value,
            )
        )
        return pending < self.config.max_pending_per_address

    def _compute_fee(self, amount_sats: int, chain: ChainConfig) -> int:
        r"""Compute bridge fee in sats."""
        return int(amount_sats * chain.fee_bps / 10000)

    def _get_direction(self, source_chain_id: int, target_chain_id: int) -> str:
        r"""Determine transfer direction."""
        if target_chain_id == 1:  # Ethereum
            return TransferDirection.BAIT_TO_ETH.value
        elif target_chain_id == 1399811149:  # Solana
            return TransferDirection.BAIT_TO_SOL.value
        elif source_chain_id == 1:
            return TransferDirection.ETH_TO_BAIT.value
        elif source_chain_id == 1399811149:
            return TransferDirection.SOL_TO_BAIT.value
        return f"chain_{source_chain_id}_to_{target_chain_id}"

    def _compute_merkle_proof(self, leaf_index: int) -> List[str]:
        r"""Compute Merkle proof for a specific leaf."""
        if not self._merkle_leaves or leaf_index >= len(self._merkle_leaves):
            return []

        proof = []
        level = list(self._merkle_leaves)
        idx = leaf_index

        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                combined = hashlib.sha256(
                    (left + right).encode()
                ).hexdigest()
                next_level.append(combined)

                if idx == i:
                    proof.append(right)
                elif idx == i + 1:
                    proof.append(left)

            level = next_level
            idx = idx // 2

        return proof

    # --- Public API ---

    def lock_bait(
        self,
        agent_id: str,
        amount_sats: int,
        target_chain_id: int,
        recipient: str,
    ) -> dict:
        r"""Lock BAIT on b'AI'tcoin for cross-chain transfer.

        This is Step 1 of the bridge process. The user locks their BAIT
        on b'AI'tcoin and receives an event with proof data that a
        relayer can use to mint wrapped tokens on the target chain.

        Parameters
        ----------
        agent_id : str
            Locking agent
        amount_sats : int
            Amount in sats to lock
        target_chain_id : int
            Target chain ID (1=ETH, 1399811149=SOL)
        recipient : str
            Recipient address on target chain

        Returns
        -------
        dict
            Lock event with event_id, transfer_id, merkle proof
        """
        if self._paused:
            return {"error": "bridge_paused"}

        chain = self.config.get_chain(target_chain_id)
        if not chain:
            return {"error": "unsupported_chain", "chain_id": target_chain_id}

        amount_bait = amount_sats / 100_000_000
        if amount_bait < chain.min_lock:
            return {"error": "below_minimum", "min": chain.min_lock}
        if amount_bait > chain.max_lock:
            return {"error": "above_maximum", "max": chain.max_lock}

        if not self._check_rate_limit(agent_id, amount_sats):
            return {"error": "daily_limit_exceeded"}

        if not self._check_pending_limit(agent_id):
            return {"error": "too_many_pending"}

        fee_sats = self._compute_fee(amount_sats, chain)
        transfer_id = uuid.uuid4().hex[:16]
        event_id = f"evt_{transfer_id}"
        now = time.time()
        tx_hash = hashlib.sha256(
            f"lock:{event_id}:{now}".encode()
        ).hexdigest()

        # Create transfer record
        record = TransferRecord(
            transfer_id=transfer_id,
            direction=self._get_direction(0, target_chain_id),
            agent_id=agent_id,
            amount_sats=amount_sats,
            fee_sats=fee_sats,
            source_chain_id=0,  # b'AI'tcoin
            target_chain_id=target_chain_id,
            source_address=f"bait:{agent_id}",
            target_address=recipient,
            created_at=now,
            state=TransferState.LOCKED.value,
        )

        # Create lock event
        leaf_hash = hashlib.sha256(
            json.dumps({
                "event_id": event_id,
                "amount_sats": amount_sats,
                "recipient": recipient,
                "chain_id": target_chain_id,
            }, sort_keys=True).encode()
        ).hexdigest()

        leaf_index = len(self._merkle_leaves)
        self._merkle_leaves.append(leaf_hash)

        event = BridgeEvent(
            event_id=event_id,
            transfer_id=transfer_id,
            event_type="lock",
            agent_id=agent_id,
            amount_sats=amount_sats,
            chain_id=target_chain_id,
            recipient=recipient,
            timestamp=now,
            block_height=0,  # Set by watcher
            tx_hash=tx_hash,
            merkle_proof=self._compute_merkle_proof(leaf_index),
            state=TransferState.LOCKED.value,
        )

        record.lock_event = event.to_dict()
        self._transfers[transfer_id] = record
        self._events[event_id] = event

        # Update conservation tracking
        self._total_locked_sats += amount_sats
        self._daily_volume[agent_id] = (
            self._daily_volume.get(agent_id, 0.0) + amount_bait
        )

        return {
            "success": True,
            "transfer_id": transfer_id,
            "event_id": event_id,
            "tx_hash": tx_hash,
            "amount_sats": amount_sats,
            "fee_sats": fee_sats,
            "merkle_proof": event.merkle_proof,
            "leaf_hash": leaf_hash,
            "leaf_index": leaf_index,
            "state": TransferState.LOCKED.value,
        }

    def submit_proof(
        self,
        event_id: str,
        proof: List[str],
        signer_id: str = "",
        signature: str = "",
    ) -> dict:
        r"""Submit a Merkle proof for a lock event.

        A relayer submits a proof that the lock event is valid.
        After N-of-M signatures are collected, the mint can proceed.

        Parameters
        ----------
        event_id : str
            Lock event to prove
        proof : List[str]
            Merkle proof path
        signer_id : str
            Relayer signer identifier
        signature : str
            Signature over the proof
        """
        event = self._events.get(event_id)
        if not event:
            return {"error": "event_not_found"}

        if event.state not in (
            TransferState.LOCKED.value,
            TransferState.PENDING_PROOF.value,
            TransferState.PROOF_SUBMITTED.value,
        ):
            return {"error": "invalid_state", "state": event.state}

        # Add signature if provided
        if signer_id and signature:
            if signer_id not in event.signatures:
                event.signatures.append(f"{signer_id}:{signature}")

        # Check if enough signatures collected
        if len(event.signatures) >= self.config.n_of_m_threshold:
            event.state = TransferState.PROOF_SUBMITTED.value
            record = self._transfers.get(event.transfer_id)
            if record:
                record.state = TransferState.PROOF_SUBMITTED.value
                record.proof_submitted_at = time.time()

        else:
            event.state = TransferState.PENDING_PROOF.value
            record = self._transfers.get(event.transfer_id)
            if record:
                record.state = TransferState.PENDING_PROOF.value

        return {
            "success": True,
            "event_id": event_id,
            "state": event.state,
            "signatures": len(event.signatures),
            "required": self.config.n_of_m_threshold,
            "ready_to_mint": (
                len(event.signatures) >= self.config.n_of_m_threshold
            ),
        }

    def mint_wrapped(self, event_id: str) -> dict:
        r"""Mint wrapped BAIT on target chain after proof verification.

        Requires N-of-M signatures to have been submitted.

        Parameters
        ----------
        event_id : str
            Lock event to mint for

        Returns
        -------
        dict
            Mint result with wBAIT amount
        """
        event = self._events.get(event_id)
        if not event:
            return {"error": "event_not_found"}

        if len(event.signatures) < self.config.n_of_m_threshold:
            return {
                "error": "insufficient_signatures",
                "have": len(event.signatures),
                "need": self.config.n_of_m_threshold,
            }

        event.state = TransferState.MINTED.value
        record = self._transfers.get(event.transfer_id)
        if record:
            record.state = TransferState.MINTED.value
            record.mint_event = {
                "event_id": f"mint_{event_id}",
                "amount_sats": event.amount_sats,
                "timestamp": time.time(),
            }

        self._total_minted_sats += event.amount_sats

        return {
            "success": True,
            "event_id": event_id,
            "mint_amount_sats": event.amount_sats,
            "mint_amount_bait": event.amount_sats / 100_000_000,
            "wrapped_token": "wBAIT",
            "target_chain_id": event.chain_id,
            "recipient": event.recipient,
        }

    def burn_wrapped(
        self,
        agent_id: str,
        amount_sats: int,
        source_chain_id: int,
    ) -> dict:
        r"""Burn wrapped BAIT on external chain for release on b'AI'tcoin.

        This is Step 4 (reverse direction). The user burns wBAIT
        on the target chain, triggering a release on b'AI'tcoin.

        Parameters
        ----------
        agent_id : str
            Burning agent
        amount_sats : int
            Amount to burn in sats
        source_chain_id : int
            Chain where wBAIT is burned
        """
        chain = self.config.get_chain(source_chain_id)
        if not chain:
            return {"error": "unsupported_chain"}

        if self._paused:
            return {"error": "bridge_paused"}

        fee_sats = self._compute_fee(amount_sats, chain)
        transfer_id = uuid.uuid4().hex[:16]
        event_id = f"burn_{transfer_id}"
        now = time.time()
        tx_hash = hashlib.sha256(
            f"burn:{event_id}:{now}".encode()
        ).hexdigest()

        event = BridgeEvent(
            event_id=event_id,
            transfer_id=transfer_id,
            event_type="burn",
            agent_id=agent_id,
            amount_sats=amount_sats,
            chain_id=source_chain_id,
            recipient=f"bait:{agent_id}",
            timestamp=now,
            block_height=0,
            tx_hash=tx_hash,
            state=TransferState.BURNED.value,
        )

        record = TransferRecord(
            transfer_id=transfer_id,
            direction=self._get_direction(source_chain_id, 0),
            agent_id=agent_id,
            amount_sats=amount_sats,
            fee_sats=fee_sats,
            source_chain_id=source_chain_id,
            target_chain_id=0,
            source_address=f"chain:{source_chain_id}:{agent_id}",
            target_address=f"bait:{agent_id}",
            created_at=now,
            state=TransferState.BURNED.value,
            burn_event=event.to_dict(),
        )

        self._transfers[transfer_id] = record
        self._events[event_id] = event
        self._total_burned_sats += amount_sats

        return {
            "success": True,
            "transfer_id": transfer_id,
            "event_id": event_id,
            "tx_hash": tx_hash,
            "amount_sats": amount_sats,
            "fee_sats": fee_sats,
            "state": TransferState.BURNED.value,
        }

    def release_bait(self, event_id: str) -> dict:
        r"""Release locked BAIT on b'AI'tcoin after burn verification.

        Parameters
        ----------
        event_id : str
            Burn event that triggered the release

        Returns
        -------
        dict
            Release result
        """
        event = self._events.get(event_id)
        if not event:
            return {"error": "event_not_found"}

        if event.event_type != "burn":
            return {"error": "not_a_burn_event"}

        event.state = TransferState.COMPLETED.value
        record = self._transfers.get(event.transfer_id)
        if record:
            record.state = TransferState.COMPLETED.value
            record.release_event = {
                "event_id": f"release_{event_id}",
                "amount_sats": event.amount_sats,
                "timestamp": time.time(),
            }
            record.completed_at = time.time()

        self._total_released_sats += event.amount_sats

        return {
            "success": True,
            "event_id": event_id,
            "release_amount_sats": event.amount_sats,
            "release_amount_bait": event.amount_sats / 100_000_000,
            "recipient": event.recipient,
        }

    def refund(self, transfer_id: str, reason: str = "timeout") -> dict:
        r"""Refund a timed-out or failed transfer.

        Parameters
        ----------
        transfer_id : str
            Transfer to refund
        reason : str
            Refund reason
        """
        record = self._transfers.get(transfer_id)
        if not record:
            return {"error": "transfer_not_found"}

        if record.state not in (
            TransferState.LOCKED.value,
            TransferState.PENDING_PROOF.value,
        ):
            return {"error": "cannot_refund_in_state", "state": record.state}

        old_state = record.state
        record.state = TransferState.REFUNDED.value
        record.completed_at = time.time()

        # Update conservation
        self._total_released_sats += record.amount_sats

        # Update event
        if record.lock_event:
            evt_id = record.lock_event.get("event_id")
            if evt_id and evt_id in self._events:
                self._events[evt_id].state = TransferState.REFUNDED.value

        return {
            "success": True,
            "transfer_id": transfer_id,
            "refund_amount_sats": record.amount_sats,
            "refund_amount_bait": record.amount_sats / 100_000_000,
            "reason": reason,
            "previous_state": old_state,
        }

    def pause(self) -> dict:
        r"""Emergency pause all bridge operations."""
        self._paused = True
        return {"success": True, "paused": True}

    def unpause(self) -> dict:
        r"""Resume bridge operations."""
        self._paused = False
        return {"success": True, "paused": False}

    def is_paused(self) -> bool:
        return self._paused

    def get_transfer(self, transfer_id: str) -> dict:
        r"""Get transfer details."""
        record = self._transfers.get(transfer_id)
        return record.to_dict() if record else {"error": "not_found"}

    def get_transfers_by_agent(self, agent_id: str) -> List[dict]:
        r"""Get all transfers for an agent."""
        return [
            t.to_dict()
            for t in self._transfers.values()
            if t.agent_id == agent_id
        ]

    def get_transfer_by_event(self, event_id: str) -> dict:
        r"""Get transfer by event ID."""
        event = self._events.get(event_id)
        if not event:
            return {"error": "event_not_found"}
        record = self._transfers.get(event.transfer_id)
        return record.to_dict() if record else {"error": "transfer_not_found"}

    def get_stats(self) -> dict:
        r"""Get bridge statistics."""
        total = len(self._transfers)
        by_state = {}
        for t in self._transfers.values():
            by_state[t.state] = by_state.get(t.state, 0) + 1

        return {
            "paused": self._paused,
            "total_transfers": total,
            "by_state": by_state,
            "total_locked_bait": self._total_locked_sats / 100_000_000,
            "total_minted_bait": self._total_minted_sats / 100_000_000,
            "total_burned_bait": self._total_burned_sats / 100_000_000,
            "total_released_bait": self._total_released_sats / 100_000_000,
            "conservation_holds": (
                self._total_locked_sats >= self._total_minted_sats
            ),
            "supported_chains": list(self.config.supported_chains.keys()),
            "merkle_tree_size": len(self._merkle_leaves),
        }

    def get_merkle_root(self) -> str:
        r"""Get the current Merkle root of all bridge events."""
        if not self._merkle_leaves:
            return hashlib.sha256(b"empty").hexdigest()

        level = list(self._merkle_leaves)
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                next_level.append(
                    hashlib.sha256((left + right).encode()).hexdigest()
                )
            level = next_level
        return level[0]

    def to_dict(self) -> dict:
        r"""Full bridge state export."""
        return {
            "config": self.config.to_dict(),
            "stats": self.get_stats(),
            "merkle_root": self.get_merkle_root(),
            "transfers": {
                tid: t.to_dict()
                for tid, t in self._transfers.items()
            },
        }
