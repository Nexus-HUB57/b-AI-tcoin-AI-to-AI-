"""Mainnet-only deterministic policy engine for BAITHex.

This module is clean-room and provider-neutral. It validates intent metadata and
unsigned payload shape before any external signer or broadcaster is contacted.
It never derives keys, signs, or transmits transactions.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable


class PolicyError(ValueError):
    """Intent rejected by policy."""


@dataclass(frozen=True)
class OutputIntent:
    address: str
    value_sats: int
    kind: str = "destination"


@dataclass(frozen=True)
class TransactionIntent:
    request_id: str
    network: str
    inputs: tuple[str, ...]
    outputs: tuple[OutputIntent, ...]
    fee_sats: int
    fee_rate_sat_vb: int
    unsigned_tx_hex: str
    policy_id: str

    @property
    def amount_sats(self) -> int:
        return sum(o.value_sats for o in self.outputs if o.kind == "destination")

    @property
    def payload_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.unsigned_tx_hex)).hexdigest()


@dataclass(frozen=True)
class MainnetPolicy:
    policy_id: str
    allowed_destinations: frozenset[str]
    allowed_change_addresses: frozenset[str]
    max_amount_sats: int
    max_fee_sats: int
    max_fee_rate_sat_vb: int
    min_confirmations: int = 1
    max_inputs: int = 100

    def validate(self, intent: TransactionIntent) -> None:
        if intent.network != "bitcoin-mainnet":
            raise PolicyError("BAITHex is Mainnet-only: network rejected")
        if intent.policy_id != self.policy_id:
            raise PolicyError("policy_id mismatch")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", intent.request_id):
            raise PolicyError("invalid request_id")
        if not intent.inputs or len(intent.inputs) > self.max_inputs:
            raise PolicyError("invalid input count")
        if any(not isinstance(i, str) or not re.fullmatch(r"[0-9a-f]{64}:[0-9]+", i) for i in intent.inputs):
            raise PolicyError("inputs must be txid:vout")
        if not intent.outputs or any(o.value_sats <= 0 for o in intent.outputs):
            raise PolicyError("outputs must have positive values")
        destinations = [o for o in intent.outputs if o.kind == "destination"]
        changes = [o for o in intent.outputs if o.kind == "change"]
        if len(destinations) != 1:
            raise PolicyError("exactly one destination output is required")
        if destinations[0].address not in self.allowed_destinations:
            raise PolicyError("destination is not allowlisted")
        if any(o.address not in self.allowed_change_addresses for o in changes):
            raise PolicyError("change address is not allowlisted")
        if intent.amount_sats <= 0 or intent.amount_sats > self.max_amount_sats:
            raise PolicyError("destination amount exceeds policy")
        if intent.fee_sats < 0 or intent.fee_sats > self.max_fee_sats:
            raise PolicyError("fee exceeds policy")
        if intent.fee_rate_sat_vb <= 0 or intent.fee_rate_sat_vb > self.max_fee_rate_sat_vb:
            raise PolicyError("fee rate exceeds policy")
        if not isinstance(intent.unsigned_tx_hex, str) or len(intent.unsigned_tx_hex) == 0:
            raise PolicyError("unsigned transaction is required")
        if len(intent.unsigned_tx_hex) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", intent.unsigned_tx_hex):
            raise PolicyError("unsigned transaction must be even-length hex")


def make_mainnet_policy(policy_id: str, destination: str, change: str, *, max_amount_sats: int = 240_700_000) -> MainnetPolicy:
    return MainnetPolicy(
        policy_id=policy_id,
        allowed_destinations=frozenset({destination}),
        allowed_change_addresses=frozenset({change}),
        max_amount_sats=max_amount_sats,
        max_fee_sats=5_000_000,
        max_fee_rate_sat_vb=500,
    )


__all__ = ["MainnetPolicy", "OutputIntent", "PolicyError", "TransactionIntent", "make_mainnet_policy"]
