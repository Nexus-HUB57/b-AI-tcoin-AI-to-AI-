"""Fail-closed, read-only composition of custody sweep and BAITHex.

This module never imports private keys, signs transactions, broadcasts transactions,
or changes custody. It produces an auditable preparation record only.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from baith_exchange.service import BaithExchange
from baith_policy.engine import TransactionIntent


class AtomicCycleError(ValueError):
    """Raised when a unified-fund cycle cannot be proven safe to prepare."""


@dataclass(frozen=True)
class CustodyAsset:
    symbol: str
    network: str
    address: str
    verified_on_chain: bool = False

    def validate(self) -> None:
        if self.symbol not in {"BTC", "ETH", "BAIT"}:
            raise AtomicCycleError(f"unsupported custody asset: {self.symbol}")
        if not self.network:
            raise AtomicCycleError(f"missing network for {self.symbol}")
        if not self.address or self.address.startswith("<"):
            raise AtomicCycleError(f"unresolved custody address for {self.symbol}")
        if self.symbol == "ETH" and not re.fullmatch(r"0x[0-9a-fA-F]{40}", self.address):
            raise AtomicCycleError("ETH custody address is not a valid EVM address")
        if self.symbol == "BTC" and len(self.address) < 26:
            raise AtomicCycleError("BTC custody address is too short")


@dataclass(frozen=True)
class FundManifest:
    fund_id: str
    environment: str
    assets: tuple[CustodyAsset, ...]
    multisig_threshold: str
    signer_external: bool
    broadcast_enabled: bool = False

    def validate(self) -> None:
        if self.environment not in {"testnet", "mainnet"}:
            raise AtomicCycleError("environment must be testnet or mainnet")
        if self.fund_id != "funddecana-my":
            raise AtomicCycleError("unexpected fund identifier")
        if not self.assets:
            raise AtomicCycleError("fund has no custody assets")
        symbols = {asset.symbol for asset in self.assets}
        if symbols != {"BTC", "ETH", "BAIT"}:
            raise AtomicCycleError("BTC, ETH and BAIT custody assets are all required")
        for asset in self.assets:
            asset.validate()
        if not re.fullmatch(r"[2-9]-of-[2-9]", self.multisig_threshold):
            raise AtomicCycleError("multisig_threshold must use N-of-M notation")
        if not self.signer_external:
            raise AtomicCycleError("signer must remain external to the repository")
        if self.broadcast_enabled:
            raise AtomicCycleError("read-only coordinator cannot enable broadcast")


class FundReadOnlyCoordinator:
    """Prepare, hash and reconcile a fund cycle without external side effects."""

    def __init__(self, exchange: BaithExchange) -> None:
        self.exchange = exchange

    def prepare_cycle(
        self,
        manifest: FundManifest,
        *,
        sweep_observation: Mapping[str, Any],
        btc_intent: TransactionIntent | None = None,
    ) -> dict[str, Any]:
        manifest.validate()
        if not isinstance(sweep_observation, Mapping):
            raise AtomicCycleError("sweep_observation must be a mapping")
        prepared_btc = None
        if btc_intent is not None:
            if manifest.environment != "mainnet":
                raise AtomicCycleError("BAITHex intent preparation is mainnet-only")
            prepared_btc = self.exchange.validate_and_prepare(btc_intent)
        payload = {
            "status": "prepared_read_only",
            "fund_id": manifest.fund_id,
            "environment": manifest.environment,
            "assets": [asdict(asset) for asset in manifest.assets],
            "sweep_observation": dict(sweep_observation),
            "baith_hex": prepared_btc,
            "signing_performed": False,
            "broadcast_performed": False,
            "capital_moved": False,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        payload["audit_sha256"] = hashlib.sha256(canonical).hexdigest()
        return payload


__all__ = ["AtomicCycleError", "CustodyAsset", "FundManifest", "FundReadOnlyCoordinator"]
