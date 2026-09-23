#!/usr/bin/env python3
"""Local-only HSM integration harness.

The MockHSMSigner models the narrow interface expected from an external HSM:
key material is generated in memory, never returned, and only a signature is
released. No network, RPC, HSM endpoint, or broadcast is used.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from baitcoin_core.blockchain.block import Transaction, TransactionInput, TransactionOutput
from baitcoin_core.blockchain.tx_verifier import TransactionVerifier
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair


@dataclass(frozen=True)
class HSMResult:
    key_id: str
    public_key_hex: str
    signature_hex: str
    broadcast: str
    tx_id: str
    fee_sats: int
    estimated_size_bytes: int
    fee_rate_sat_vb: int


class MockHSMSigner:
    """Test double for an HSM; never use this class for production signing."""

    def __init__(self, key_id: str = "hsm-test-key") -> None:
        self.key_id = key_id
        self._key = SchnorrKeyPair()

    @property
    def public_key(self) -> bytes:
        return self._key.pub_bytes

    def sign_digest(self, digest: bytes) -> bytes:
        if len(digest) != 32:
            raise ValueError("HSM signing API requires a 32-byte digest")
        return self._key.sign(digest, aux_rand=b"\x00" * 32).raw

    def forget(self) -> None:
        # Drop the only in-memory reference; production HSMs retain keys outside
        # the application process. This harness never serializes the key.
        self._key = None  # type: ignore[assignment]


class HSMRejected(RuntimeError):
    """Controlled signer rejection used by the local failure simulation."""


class RejectingMockHSMSigner(MockHSMSigner):
    """HSM test double that rejects every signing request."""

    def sign_digest(self, digest: bytes) -> bytes:
        if len(digest) != 32:
            raise ValueError("HSM signing API requires a 32-byte digest")
        raise HSMRejected("HSM_REJECTED: policy denied test key operation")


def run() -> HSMResult:
    signer = MockHSMSigner()
    prev_tx_id = bytes.fromhex("11" * 32)
    utxo = TransactionOutput(amount_sats=100_000, script_pubkey=signer.public_key)
    utxo_set = {f"{prev_tx_id.hex()}:0": utxo}
    tx = Transaction(
        tx_type="transfer",
        inputs=[TransactionInput(prev_tx_id=prev_tx_id, prev_output_index=0)],
        outputs=[TransactionOutput(amount_sats=99_000, script_pubkey=b"receiver")],
        nonce=1,
        agent_id="hsm-e2e-test",
        payload=b"local-e2e",
    )
    signature = signer.sign_digest(tx.tx_id)
    tx.signature = signature
    verifier = TransactionVerifier(utxo_set, min_fee_rate=1)
    result = verifier.verify(tx, fee_rate=10)
    if not result.valid:
        raise RuntimeError(f"signed transaction rejected: {result.reason}")
    size = verifier._estimate_tx_size(tx)
    signer.forget()
    return HSMResult(
        key_id="hsm-test-key",
        public_key_hex=utxo.script_pubkey.hex(),
        signature_hex=tx.signature.hex(),
        broadcast="blocked: local harness has no RPC/broadcast capability",
        tx_id=tx.tx_id.hex(),
        fee_sats=result.fee,
        estimated_size_bytes=size,
        fee_rate_sat_vb=result.fee // size,
    )


def run_rejection_simulation() -> dict[str, object]:
    """Exercise the orchestrator's fail-closed branch without broadcasting."""
    signer = RejectingMockHSMSigner()
    tx_id = "11" * 32
    state = "unsigned"
    broadcast_attempted = False
    try:
        signer.sign_digest(bytes.fromhex(tx_id))
        state = "signed"
    except HSMRejected as exc:
        state = "signing_rejected"
        return {
            "state": state,
            "error": str(exc),
            "broadcast_attempted": broadcast_attempted,
            "mutation": "none",
            "action": "pause_and_alert",
        }
    finally:
        signer.forget()
    return {
        "state": state,
        "error": "unexpected signer acceptance",
        "broadcast_attempted": broadcast_attempted,
        "mutation": "unexpected",
        "action": "stop",
    }


if __name__ == "__main__":
    print(json.dumps({
        "successful_dry_run": {**run().__dict__, "signature_hex": "<redacted-test-signature>"},
        "rejection_simulation": run_rejection_simulation(),
    }, indent=2, sort_keys=True))
