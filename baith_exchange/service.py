"""BAITHex exchange orchestration boundary.

The service prepares and validates Mainnet transaction intents. Signing and
broadcast are explicit external capabilities and are disabled by default.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from baith_policy.engine import MainnetPolicy, PolicyError, TransactionIntent


class ExchangeError(RuntimeError):
    """Exchange orchestration failure."""


class Signer(Protocol):
    def sign(self, intent: TransactionIntent) -> dict[str, str]: ...


class Broadcaster(Protocol):
    def broadcast(self, signed_tx_hex: str, idempotency_key: str) -> str: ...


class UtxoReader(Protocol):
    def get_utxos(self, address: str) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class ExchangeConfig:
    source_address: str
    policy_id: str
    allow_signing: bool = False
    allow_broadcast: bool = False


class BaithExchange:
    def __init__(self, config: ExchangeConfig, policy: MainnetPolicy, *, signer: Signer | None = None, broadcaster: Broadcaster | None = None) -> None:
        self.config = config
        self.policy = policy
        self.signer = signer
        self.broadcaster = broadcaster
        self._seen: set[str] = set()

    def validate_and_prepare(self, intent: TransactionIntent) -> dict[str, Any]:
        if intent.request_id in self._seen:
            raise ExchangeError("duplicate request_id")
        self.policy.validate(intent)
        digest = hashlib.sha256(json.dumps({
            "request_id": intent.request_id,
            "payload_sha256": intent.payload_sha256,
            "policy_id": intent.policy_id,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self._seen.add(intent.request_id)
        return {
            "status": "prepared",
            "request_id": intent.request_id,
            "policy_id": self.policy.policy_id,
            "payload_sha256": intent.payload_sha256,
            "audit_digest": digest,
            "network": intent.network,
            "signing_enabled": self.config.allow_signing and self.signer is not None,
            "broadcast_enabled": self.config.allow_broadcast and self.broadcaster is not None,
        }

    def sign(self, intent: TransactionIntent) -> dict[str, str]:
        self.policy.validate(intent)
        if not self.config.allow_signing or self.signer is None:
            raise ExchangeError("signing is disabled; configure an external threshold signer")
        return self.signer.sign(intent)

    def broadcast(self, signed_tx_hex: str, request_id: str) -> str:
        if not self.config.allow_broadcast or self.broadcaster is None:
            raise ExchangeError("broadcast is disabled")
        if not signed_tx_hex or not all(c in "0123456789abcdefABCDEF" for c in signed_tx_hex) or len(signed_tx_hex) % 2:
            raise ExchangeError("signed transaction must be even-length hex")
        return self.broadcaster.broadcast(signed_tx_hex, request_id)


__all__ = ["BaithExchange", "ExchangeConfig", "ExchangeError", "Broadcaster", "Signer", "UtxoReader"]
