"""Adapter from BAITHex intents to the provider-neutral HSM/MPC boundary."""
from __future__ import annotations

from typing import Protocol

from baitcoin_security.hsm_mpc import HsmMpcSigner, SigningRequest
from baith_policy.engine import TransactionIntent


class HsmIntentSigner(Protocol):
    def sign(self, intent: TransactionIntent) -> dict[str, object]: ...


class BaithHsmMpcAdapter:
    """Translate a validated BAITHex intent into a complete-signing request."""

    def __init__(self, signer: HsmMpcSigner) -> None:
        self.signer = signer

    def sign(self, intent: TransactionIntent) -> dict[str, object]:
        destination = next(o.address for o in intent.outputs if o.kind == "destination")
        request = SigningRequest(
            unsigned_tx_hex=intent.unsigned_tx_hex,
            network=intent.network,
            destination=destination,
            amount_sats=intent.amount_sats,
            policy_id=intent.policy_id,
            idempotency_key=intent.request_id,
            input_count=len(intent.inputs),
        )
        return self.signer.sign(request)


__all__ = ["BaithHsmMpcAdapter", "HsmIntentSigner"]
