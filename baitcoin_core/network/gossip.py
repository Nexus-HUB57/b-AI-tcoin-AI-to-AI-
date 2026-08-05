r"""
Gossip Protocol for b'AI'tcoin — Block/Transaction propagation.

Implements an efficient gossip-based dissemination protocol with:
- Typed messages: BLOCK, TRANSACTION, PEER_DISCOVERY, PING, PONG,
  SYNC_REQUEST, SYNC_RESPONSE
- JSON serialization/deserialization
- Message deduplication with configurable TTL (seen set)
- Fan-out factor (default 3) to limit propagation overhead
- Optional Schnorr/BIP-340 signature on messages

Usage::

    proto = GossipProtocol(node_id="alpha")
    msg = proto.create_block_message(block_dict)
    raw = proto.serialize(msg)
    received = proto.receive(raw)
"""

import hashlib
import json
import time
import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class GossipMessageType(Enum):
    """Message types for the gossip protocol."""

    BLOCK = "block"
    TRANSACTION = "transaction"
    PEER_DISCOVERY = "peer_discovery"
    PING = "ping"
    PONG = "pong"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"


@dataclass
class GossipMessage:
    """A single gossip message.

    Attributes:
        msg_type: The message type enum value.
        payload: Arbitrary dict payload for the message.
        sender: Node ID of the sender.
        timestamp: Unix timestamp of message creation.
        signature: Optional Schnorr signature bytes.
        nonce: Random nonce for deduplication.
    """

    msg_type: GossipMessageType
    payload: Dict[str, Any]
    sender: str
    timestamp: float = field(default_factory=time.time)
    signature: Optional[bytes] = None
    nonce: str = field(default_factory=lambda: hashlib.sha256(
        os.urandom(32)
    ).hexdigest()[:16])

    @property
    def dedup_key(self) -> str:
        """Unique key for deduplication (sender + nonce)."""
        return f"{self.sender}:{self.nonce}"

    @property
    def type_str(self) -> str:
        """String representation of the message type."""
        return self.msg_type.value


class GossipProtocol:
    """Gossip protocol for efficient block and transaction propagation.

    Manages message broadcasting with:
    - Fan-out factor: each message is sent to at most ``fanout`` peers
    - TTL-based deduplication: messages are tracked for ``seen_ttl`` seconds
    - JSON wire format for interoperability

    Args:
        node_id: Unique identifier for this node.
        fanout: Number of peers to forward each message to (default 3).
        seen_ttl: TTL in seconds for the dedup seen set (default 300).
    """

    DEFAULT_FANOUT = 3
    DEFAULT_SEEN_TTL = 300  # 5 minutes

    def __init__(
        self,
        node_id: str,
        fanout: int = DEFAULT_FANOUT,
        seen_ttl: float = DEFAULT_SEEN_TTL,
    ):
        self.node_id = node_id
        self.fanout = fanout
        self.seen_ttl = seen_ttl
        self._seen: Dict[str, float] = {}  # dedup_key -> timestamp
        self._outbox: List[GossipMessage] = []  # messages pending broadcast
        self._inbound_log: List[GossipMessage] = []  # received messages
        self._peer_ids: List[str] = []  # known peer IDs for fan-out
        self._broadcast_log: List[Dict[str, Any]] = []

    # ── Peers ───────────────────────────────────────────────

    def set_peers(self, peer_ids: List[str]) -> None:
        """Set the list of known peer IDs for fan-out selection.

        Args:
            peer_ids: List of peer node identifiers.
        """
        self._peer_ids = list(peer_ids)

    def add_peer(self, peer_id: str) -> None:
        """Add a single peer to the known peer list."""
        if peer_id not in self._peer_ids:
            self._peer_ids.append(peer_id)

    def remove_peer(self, peer_id: str) -> None:
        """Remove a peer from the known peer list."""
        self._peer_ids = [p for p in self._peer_ids if p != peer_id]

    # ── Serialization ───────────────────────────────────────

    def serialize(self, message: GossipMessage) -> bytes:
        """Serialize a GossipMessage to JSON bytes.

        Args:
            message: The message to serialize.

        Returns:
            UTF-8 encoded JSON bytes.
        """
        data = {
            "type": message.msg_type.value,
            "payload": message.payload,
            "sender": message.sender,
            "timestamp": message.timestamp,
            "nonce": message.nonce,
        }
        if message.signature is not None:
            data["signature"] = message.signature.hex()
        else:
            data["signature"] = None
        return json.dumps(data).encode("utf-8")

    def deserialize(self, raw: bytes) -> Optional[GossipMessage]:
        """Deserialize JSON bytes into a GossipMessage.

        Args:
            raw: UTF-8 encoded JSON bytes.

        Returns:
            A GossipMessage, or None if parsing fails.
        """
        try:
            data = json.loads(raw.decode("utf-8"))
            msg_type = GossipMessageType(data["type"])
            sig_hex = data.get("signature")
            signature = bytes.fromhex(sig_hex) if sig_hex else None
            return GossipMessage(
                msg_type=msg_type,
                payload=data.get("payload", {}),
                sender=data.get("sender", ""),
                timestamp=data.get("timestamp", 0.0),
                signature=signature,
                nonce=data.get("nonce", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError, AttributeError) as exc:
            logger.warning("Failed to deserialize gossip message: %s", exc)
            return None

    # ── Deduplication ───────────────────────────────────────

    def _is_seen(self, message: GossipMessage) -> bool:
        """Check if a message has already been seen.

        Expire old entries from the seen set based on TTL.

        Args:
            message: The message to check.

        Returns:
            True if the message was previously seen (and not expired).
        """
        self._prune_seen()
        key = message.dedup_key
        if key in self._seen:
            return True
        self._seen[key] = time.time()
        return False

    def _prune_seen(self) -> None:
        """Remove expired entries from the dedup seen set."""
        now = time.time()
        expired = [k for k, ts in self._seen.items() if now - ts > self.seen_ttl]
        for k in expired:
            del self._seen[k]

    # ── Fan-out ─────────────────────────────────────────────

    def _select_fanout_peers(self, exclude: Optional[str] = None) -> List[str]:
        """Select peers for fan-out propagation.

        Excludes the sender and selects up to ``fanout`` peers.
        Uses deterministic shuffling based on message nonce for variety.

        Args:
            exclude: Peer ID to exclude (usually the sender).

        Returns:
            List of selected peer IDs.
        """
        candidates = [p for p in self._peer_ids if p != exclude]
        # Deterministic shuffle by sorting; could add random seed per message
        return candidates[: self.fanout]

    # ── Message Creation ─────────────────────────────────────

    def create_block_message(
        self, block_data: Dict[str, Any]
    ) -> GossipMessage:
        """Create a BLOCK gossip message.

        Args:
            block_data: Serialized block dict (index, hash, header, etc.).

        Returns:
            A GossipMessage of type BLOCK.
        """
        return GossipMessage(
            msg_type=GossipMessageType.BLOCK,
            payload={"block": block_data},
            sender=self.node_id,
        )

    def create_tx_message(
        self, tx_data: Dict[str, Any]
    ) -> GossipMessage:
        """Create a TRANSACTION gossip message.

        Args:
            tx_data: Serialized transaction dict.

        Returns:
            A GossipMessage of type TRANSACTION.
        """
        return GossipMessage(
            msg_type=GossipMessageType.TRANSACTION,
            payload={"transaction": tx_data},
            sender=self.node_id,
        )

    def create_ping_message(self) -> GossipMessage:
        """Create a PING message for liveness checks."""
        return GossipMessage(
            msg_type=GossipMessageType.PING,
            payload={},
            sender=self.node_id,
        )

    def create_pong_message(self, ping_nonce: str) -> GossipMessage:
        """Create a PONG response to a PING.

        Args:
            ping_nonce: Nonce from the original PING message.
        """
        return GossipMessage(
            msg_type=GossipMessageType.PONG,
            payload={"ping_nonce": ping_nonce},
            sender=self.node_id,
        )

    def create_peer_discovery_message(
        self, known_peers: List[str]
    ) -> GossipMessage:
        """Create a PEER_DISCOVERY message to share known peers."""
        return GossipMessage(
            msg_type=GossipMessageType.PEER_DISCOVERY,
            payload={"peers": known_peers},
            sender=self.node_id,
        )

    def create_sync_request_message(
        self, from_height: int, to_height: int
    ) -> GossipMessage:
        """Create a SYNC_REQUEST message to request blocks from a range."""
        return GossipMessage(
            msg_type=GossipMessageType.SYNC_REQUEST,
            payload={"from_height": from_height, "to_height": to_height},
            sender=self.node_id,
        )

    def create_sync_response_message(
        self, blocks: List[Dict[str, Any]]
    ) -> GossipMessage:
        """Create a SYNC_RESPONSE message with block data."""
        return GossipMessage(
            msg_type=GossipMessageType.SYNC_RESPONSE,
            payload={"blocks": blocks},
            sender=self.node_id,
        )

    # ── Broadcast / Receive ──────────────────────────────────

    def broadcast(self, message: GossipMessage) -> int:
        """Broadcast a message to fan-out peers.

        Marks the message as seen and adds to the outbox for
        selected peers.

        Args:
            message: The message to broadcast.

        Returns:
            Number of peers the message would be sent to.
        """
        # Mark as seen from this node
        key = message.dedup_key
        if key not in self._seen:
            self._seen[key] = time.time()

        targets = self._select_fanout_peers(exclude=message.sender)
        for target in targets:
            self._broadcast_log.append({
                "direction": "outgoing",
                "target": target,
                "type": message.type_str,
                "nonce": message.nonce,
                "timestamp": time.time(),
            })
        self._outbox.append(message)
        logger.debug(
            "Broadcasting %s to %d peers", message.type_str, len(targets)
        )
        return len(targets)

    def receive(self, raw: bytes) -> List[GossipMessage]:
        """Process an incoming raw message.

        Deserializes, deduplicates, and returns the list of
        messages that should be forwarded (non-duplicate).

        Args:
            raw: UTF-8 encoded JSON bytes.

        Returns:
            List of messages to forward (empty if duplicate).
        """
        message = self.deserialize(raw)
        if message is None:
            return []

        self._inbound_log.append(message)

        if self._is_seen(message):
            logger.debug("Dropping duplicate message %s", message.dedup_key)
            return []

        logger.debug(
            "Received %s from %s", message.type_str, message.sender
        )
        return [message]

    # ── Status / Diagnostics ──────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return protocol statistics."""
        self._prune_seen()
        return {
            "node_id": self.node_id,
            "fanout": self.fanout,
            "seen_ttl": self.seen_ttl,
            "seen_messages": len(self._seen),
            "outbox_size": len(self._outbox),
            "inbound_count": len(self._inbound_log),
            "broadcast_count": len(self._broadcast_log),
            "known_peers": len(self._peer_ids),
        }

    def clear(self) -> None:
        """Clear all internal state (for testing)."""
        self._seen.clear()
        self._outbox.clear()
        self._inbound_log.clear()
        self._broadcast_log.clear()
