r"""Bridge Watcher — Monitors external chain events.

Watches for lock and burn events on external chains (ETH, SOL)
and routes them to the BridgeManager for processing.

In production, the watcher would connect to:
    - Ethereum: WebSocket subscription to bridge contract events
    - Solana: gRPC subscription to bridge program logs

For the test/SDK layer, the watcher provides:
    - Event simulation (for testing)
    - Event queuing and deduplication
    - Confirmation tracking
    - Health monitoring

Event Flow::

    External Chain
        |
        | (lock/burn event)
        v
    BridgeWatcher.event_queue
        |
        | (confirmed events)
        v
    BridgeManager.lock_bait() / burn_wrapped()

Usage::

    watcher = BridgeWatcher()
    watcher.simulate_lock_event(agent_id, amount_sats, chain_id, recipient)
    events = watcher.get_pending_events()
"""
import hashlib
import time
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class ExternalEvent:
    r"""An event detected on an external chain."""
    event_id: str
    event_type: str  # "lock", "burn", "mint", "release"
    chain_id: int
    tx_hash: str
    block_number: int
    agent_id: str
    amount_sats: int
    recipient: str
    timestamp: float
    confirmations: int = 0
    required_confirmations: int = 12
    processed: bool = False

    def is_confirmed(self) -> bool:
        return self.confirmations >= self.required_confirmations

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "chain_id": self.chain_id,
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "agent_id": self.agent_id,
            "amount_sats": self.amount_sats,
            "amount_bait": self.amount_sats / 100_000_000,
            "recipient": self.recipient,
            "timestamp": self.timestamp,
            "confirmations": self.confirmations,
            "required_confirmations": self.required_confirmations,
            "confirmed": self.is_confirmed(),
            "processed": self.processed,
        }


class BridgeWatcher:
    r"""Watches external chain events for the bridge.

    In production, this connects to blockchain RPCs via WebSocket.
    In the SDK layer, it provides event simulation for testing.

    Parameters
    ----------
    confirmations : Dict[int, int]
        Chain ID -> required confirmations
    """

    def __init__(
        self,
        confirmations: Optional[Dict[int, int]] = None,
    ):
        self.confirmations = confirmations or {
            1: 12,  # Ethereum mainnet
            11155111: 3,  # Sepolia testnet
            1399811149: 1,  # Solana mainnet
            1399811150: 1,  # Solana devnet
        }
        self._event_queue: List[ExternalEvent] = []
        self._processed_ids: set = set()
        self._callbacks: List[Callable] = []
        self._total_detected = 0
        self._total_processed = 0

    def on_event(self, callback: Callable) -> None:
        r"""Register a callback for confirmed events."""
        self._callbacks.append(callback)

    def simulate_lock_event(
        self,
        agent_id: str,
        amount_sats: int,
        chain_id: int,
        recipient: str,
    ) -> dict:
        r"""Simulate a lock event on an external chain (for testing).

        Creates a fake lock event and adds it to the queue with
        full confirmations (ready for processing).
        """
        event_id = f"ext_{uuid.uuid4().hex[:12]}"
        now = time.time()
        tx_hash = hashlib.sha256(
            f"lock:{event_id}:{now}".encode()
        ).hexdigest()

        required = self.confirmations.get(chain_id, 1)

        event = ExternalEvent(
            event_id=event_id,
            event_type="lock",
            chain_id=chain_id,
            tx_hash=tx_hash,
            block_number=int(now),
            agent_id=agent_id,
            amount_sats=amount_sats,
            recipient=recipient,
            timestamp=now,
            confirmations=required,  # Auto-confirmed for simulation
            required_confirmations=required,
        )

        self._event_queue.append(event)
        self._total_detected += 1

        # Auto-trigger callbacks for simulated events
        for cb in self._callbacks:
            try:
                cb(event.to_dict())
            except Exception:
                pass

        return event.to_dict()

    def simulate_burn_event(
        self,
        agent_id: str,
        amount_sats: int,
        chain_id: int,
    ) -> dict:
        r"""Simulate a burn event on an external chain."""
        event_id = f"ext_{uuid.uuid4().hex[:12]}"
        now = time.time()
        tx_hash = hashlib.sha256(
            f"burn:{event_id}:{now}".encode()
        ).hexdigest()

        required = self.confirmations.get(chain_id, 1)

        event = ExternalEvent(
            event_id=event_id,
            event_type="burn",
            chain_id=chain_id,
            tx_hash=tx_hash,
            block_number=int(now),
            agent_id=agent_id,
            amount_sats=amount_sats,
            recipient=f"bait:{agent_id}",
            timestamp=now,
            confirmations=required,
            required_confirmations=required,
        )

        self._event_queue.append(event)
        self._total_detected += 1

        for cb in self._callbacks:
            try:
                cb(event.to_dict())
            except Exception:
                pass

        return event.to_dict()

    def get_pending_events(self) -> List[dict]:
        r"""Get unprocessed confirmed events."""
        return [
            e.to_dict()
            for e in self._event_queue
            if e.is_confirmed() and not e.processed
        ]

    def process_next(self, callback: Callable = None) -> Optional[dict]:
        r"""Process the next pending event.

        Returns the event data and marks it as processed.
        """
        for event in self._event_queue:
            if event.is_confirmed() and not event.processed:
                event.processed = True
                self._total_processed += 1
                self._processed_ids.add(event.event_id)

                data = event.to_dict()
                if callback:
                    callback(data)
                return data
        return None

    def add_confirmations(self, event_id: str, count: int = 1) -> dict:
        r"""Add confirmations to an event (simulates block production)."""
        for event in self._event_queue:
            if event.event_id == event_id:
                event.confirmations = min(
                    event.confirmations + count,
                    event.required_confirmations,
                )
                return event.to_dict()
        return {"error": "event_not_found"}

    def get_stats(self) -> dict:
        r"""Get watcher statistics."""
        pending = sum(
            1 for e in self._event_queue
            if e.is_confirmed() and not e.processed
        )
        waiting = sum(
            1 for e in self._event_queue
            if not e.is_confirmed() and not e.processed
        )
        return {
            "total_detected": self._total_detected,
            "total_processed": self._total_processed,
            "pending_confirmed": pending,
            "waiting_confirmations": waiting,
            "queue_size": len(self._event_queue),
            "callbacks_registered": len(self._callbacks),
        }
