"""
b'AI'tcoin Relayer Network (Phase C)

Provides a meta-transaction relayer network that enables:

- Users sign transactions offline; relayers submit and pay gas on-chain.
- Cross-chain message forwarding (``relay_to`` field).
- A leaderboard tracking relayer performance.

A minimum stake of 100 BAIT (satoshis) is required to register as a relayer.
Meta-transactions are validated (signature, nonce, balance, fee) before
being accepted into the pending queue.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_RELAYER_STAKE_SATS: int = 100  # 100 BAIT satoshis

# For testing / simple deployments we use HMAC-based signature verification.
# In production, Schnorr/BIP-340 signatures would be verified against
# the sender's public key.


def _verify_signature(sender: str, message: str, signature_hex: str) -> bool:
    """Verify that *signature_hex* is an HMAC-SHA256 of *message* by *sender*.

    This is a simplified verification suitable for the testnet.  The real
    mainnet will use Schnorr/BIP-340.

    The expected signature is ``HMAC-SHA256(key=sender, msg=message)``
    encoded as hex.
    """
    try:
        expected = hmac.new(
            sender.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature_hex.lower())
    except Exception:
        return False


def _sign_message(sender: str, message: str) -> str:
    """Create an HMAC-SHA256 signature for testing purposes."""
    return hmac.new(
        sender.encode(), message.encode(), hashlib.sha256
    ).hexdigest()


def _meta_tx_message(
    sender: str,
    recipient: str,
    amount_sats: int,
    nonce: int,
    fee_sats: int,
    relay_to: str,
) -> str:
    """Build the canonical message string for a meta-transaction."""
    return f"{sender}:{recipient}:{amount_sats}:{nonce}:{fee_sats}:{relay_to}"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class RelayerNode:
    """A registered relayer node."""

    node_id: str
    stake_amount: int = 0
    registered_at: float = 0.0
    tx_count: int = 0
    fee_earned: int = 0
    active: bool = True


def _default_balances() -> dict[str, int]:
    """Factory for default empty balance map (avoids mutable default)."""
    return {}


@dataclass
class MetaTransaction:
    """A meta-transaction waiting to be relayed."""

    meta_tx_id: str
    sender: str
    recipient: str
    amount_sats: int
    nonce: int
    fee_sats: int
    signature_hex: str
    relay_to: str
    submitted_at: float = 0.0
    status: str = "pending"  # pending | executed | failed


# ---------------------------------------------------------------------------
# Relayer Network
# ---------------------------------------------------------------------------


class RelayerNetwork:
    """Manages the relayer network and meta-transaction lifecycle.

    Relayers must stake a minimum amount to participate.  Meta-transactions
    are validated on submission and held in a pending queue until a relayer
    executes them.

    The network maintains an in-memory ledger of balances (separate from the
    main blockchain) for testing purposes.  In production the relayer would
    interact directly with the chain's UTXO set or state trie.
    """

    def __init__(self) -> None:
        self._relayers: dict[str, RelayerNode] = {}
        self._pending: dict[str, MetaTransaction] = {}
        self._executed: dict[str, MetaTransaction] = {}
        # Simple balance ledger for meta-tx validation
        self._balances: dict[str, int] = _default_balances()
        # Per-sender nonce tracker
        self._nonces: dict[str, int] = {}
        logger.info("RelayerNetwork initialised (min_stake=%d sats)", MIN_RELAYER_STAKE_SATS)

    # -- balance helpers (for testing / standalone use) --

    def set_balance(self, address: str, amount_sats: int) -> None:
        """Set an account balance (useful for testing)."""
        self._balances[address] = amount_sats

    def get_balance(self, address: str) -> int:
        """Return the balance of an address."""
        return self._balances.get(address, 0)

    def _deduct(self, address: str, amount: int) -> bool:
        """Atomically deduct *amount* from *address* balance."""
        current = self._balances.get(address, 0)
        if current < amount:
            return False
        self._balances[address] = current - amount
        return True

    def _credit(self, address: str, amount: int) -> None:
        """Credit *amount* to *address* balance."""
        self._balances[address] = self._balances.get(address, 0) + amount

    # -- relayer registration --

    def register_relayer(self, node_id: str, stake_sats: int) -> dict[str, Any]:
        """Register a new relayer node.

        Parameters
        ----------
        node_id:
            Unique identifier for the relayer.
        stake_sats:
            Amount of BAIT (in satoshis) to stake. Must be >=
            ``MIN_RELAYER_STAKE_SATS``.

        Returns
        -------
        dict
            ``{success, node_id, error?}``
        """
        if node_id in self._relayers:
            return {
                "success": False,
                "node_id": node_id,
                "error": "Relayer already registered",
            }

        if stake_sats < MIN_RELAYER_STAKE_SATS:
            return {
                "success": False,
                "node_id": node_id,
                "error": (
                    f"Insufficient stake: {stake_sats} < minimum "
                    f"{MIN_RELAYER_STAKE_SATS} sats"
                ),
            }

        node = RelayerNode(
            node_id=node_id,
            stake_amount=stake_sats,
            registered_at=time.time(),
        )
        self._relayers[node_id] = node

        logger.info(
            "Relayer '%s' registered with stake=%d sats", node_id, stake_sats
        )
        return {"success": True, "node_id": node_id}

    # -- meta-transaction submission --

    def submit_meta_tx(
        self,
        sender: str,
        recipient: str,
        amount_sats: int,
        nonce: int,
        fee_sats: int,
        signature_hex: str,
        relay_to: str = "",
    ) -> dict[str, Any]:
        """Submit a signed meta-transaction for relaying.

        Validation steps:
        1. Verify the signature against the canonical message.
        2. Check that the nonce matches the sender's expected next nonce.
        3. Verify the sender has sufficient balance (amount + fee).

        If all checks pass the transaction enters the pending queue.

        Returns
        -------
        dict
            ``{success, meta_tx_id, error?}``
        """
        # 1. Build and verify signature
        message = _meta_tx_message(
            sender, recipient, amount_sats, nonce, fee_sats, relay_to
        )
        if not _verify_signature(sender, message, signature_hex):
            logger.warning("Meta-tx from %s: invalid signature", sender)
            return {
                "success": False,
                "meta_tx_id": "",
                "error": "Invalid signature",
            }

        # 2. Nonce check
        expected_nonce = self._nonces.get(sender, 0)
        if nonce != expected_nonce:
            logger.warning(
                "Meta-tx from %s: nonce mismatch (got %d, expected %d)",
                sender, nonce, expected_nonce,
            )
            return {
                "success": False,
                "meta_tx_id": "",
                "error": f"Invalid nonce: expected {expected_nonce}",
            }

        # 3. Balance check
        total_cost = amount_sats + fee_sats
        if self.get_balance(sender) < total_cost:
            logger.warning(
                "Meta-tx from %s: insufficient balance (%d < %d)",
                sender, self.get_balance(sender), total_cost,
            )
            return {
                "success": False,
                "meta_tx_id": "",
                "error": "Insufficient balance",
            }

        # All checks passed – enqueue
        meta_tx_id = uuid.uuid4().hex[:16]
        meta_tx = MetaTransaction(
            meta_tx_id=meta_tx_id,
            sender=sender,
            recipient=recipient,
            amount_sats=amount_sats,
            nonce=nonce,
            fee_sats=fee_sats,
            signature_hex=signature_hex,
            relay_to=relay_to,
            submitted_at=time.time(),
        )
        self._pending[meta_tx_id] = meta_tx

        # Reserve balance by deducting immediately
        self._deduct(sender, total_cost)

        logger.info(
            "Meta-tx %s submitted: %s -> %s, amount=%d, fee=%d",
            meta_tx_id, sender[:12], recipient[:12], amount_sats, fee_sats,
        )
        return {"success": True, "meta_tx_id": meta_tx_id}

    # -- meta-transaction execution --

    def execute_meta_tx(
        self, meta_tx_id: str, relayer_id: str
    ) -> dict[str, Any]:
        """Execute a pending meta-transaction via a registered relayer.

        The relayer earns the transaction fee.  The amount is transferred
        to the recipient.

        Returns
        -------
        dict
            ``{success, meta_tx_id, relayer_id, sender, recipient,
            amount, fee, error?}``
        """
        # Validate relayer
        if relayer_id not in self._relayers:
            return {
                "success": False,
                "meta_tx_id": meta_tx_id,
                "relayer_id": relayer_id,
                "error": "Relayer not registered",
            }
        relayer = self._relayers[relayer_id]
        if not relayer.active:
            return {
                "success": False,
                "meta_tx_id": meta_tx_id,
                "relayer_id": relayer_id,
                "error": "Relayer is inactive",
            }

        # Validate meta-tx
        meta_tx = self._pending.pop(meta_tx_id, None)
        if meta_tx is None:
            return {
                "success": False,
                "meta_tx_id": meta_tx_id,
                "relayer_id": relayer_id,
                "error": "Meta-transaction not found or already executed",
            }

        # Execute the transfer
        self._credit(meta_tx.recipient, meta_tx.amount_sats)
        self._credit(relayer_id, meta_tx.fee_sats)

        # Advance sender nonce
        self._nonces[meta_tx.sender] = meta_tx.nonce + 1

        # Update relayer stats
        relayer.tx_count += 1
        relayer.fee_earned += meta_tx.fee_sats

        # Move to executed
        meta_tx.status = "executed"
        self._executed[meta_tx_id] = meta_tx

        logger.info(
            "Meta-tx %s executed by relayer '%s': fee=%d earned",
            meta_tx_id, relayer_id, meta_tx.fee_sats,
        )
        return {
            "success": True,
            "meta_tx_id": meta_tx_id,
            "relayer_id": relayer_id,
            "sender": meta_tx.sender,
            "recipient": meta_tx.recipient,
            "amount": meta_tx.amount_sats,
            "fee": meta_tx.fee_sats,
            "relay_to": meta_tx.relay_to,
        }

    # -- queries --

    def get_pending_meta_txs(self) -> list[dict[str, Any]]:
        """Return the queue of pending meta-transactions."""
        return [
            {
                "meta_tx_id": tx.meta_tx_id,
                "sender": tx.sender,
                "recipient": tx.recipient,
                "amount_sats": tx.amount_sats,
                "fee_sats": tx.fee_sats,
                "relay_to": tx.relay_to,
                "submitted_at": tx.submitted_at,
            }
            for tx in sorted(self._pending.values(), key=lambda t: t.submitted_at)
        ]

    def get_relayer_leaderboard(self) -> list[dict[str, Any]]:
        """Return relayers ranked by transaction count (desc), then fees."""
        nodes = sorted(
            self._relayers.values(),
            key=lambda n: (n.tx_count, n.fee_earned),
            reverse=True,
        )
        return [
            {
                "node_id": n.node_id,
                "stake_amount": n.stake_amount,
                "tx_count": n.tx_count,
                "fee_earned": n.fee_earned,
                "active": n.active,
            }
            for n in nodes
        ]

    def get_relayer_info(self, node_id: str) -> Optional[dict[str, Any]]:
        """Return info about a specific relayer, or ``None``."""
        node = self._relayers.get(node_id)
        if node is None:
            return None
        return {
            "node_id": node.node_id,
            "stake_amount": node.stake_amount,
            "registered_at": node.registered_at,
            "tx_count": node.tx_count,
            "fee_earned": node.fee_earned,
            "active": node.active,
        }
