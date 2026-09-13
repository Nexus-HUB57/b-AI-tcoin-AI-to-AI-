import pytest

from native_processing.parity_gate import ParityAttestation, ParityError, ParityGate
from native_processing.swap_executor import Deposit, ExecutorError


def attestation(**overrides):
    value = {
        "version": 1,
        "pair": "BAIT/USDT",
        "bait_usdt_ppm": 1_000_000,
        "usdt_usd_ppm": 1_000_000,
        "usd_brl_ppm": 5_000_000,
        "observed_at": 1000.0,
        "expires_at": 1060.0,
        "round_id": "round-1",
        "source_ids": ["source-a", "source-b", "source-c"],
        "quorum": 3,
        "proof_b64": "verified-proof",
    }
    value.update(overrides)
    return ParityAttestation.from_mapping(value)


def test_parity_gate_accepts_only_verified_fresh_parity():
    gate = ParityGate(lambda proof: proof.proof_b64 == "verified-proof", clock=lambda: 1002.0)
    assert gate.validate(attestation())
    with pytest.raises(ParityError, match="parity band"):
        gate.validate(attestation(bait_usdt_ppm=1_100_000))
    with pytest.raises(ParityError, match="stale|expired"):
        gate.validate(attestation(observed_at=900.0, expires_at=960.0))
    with pytest.raises(ParityError, match="verified"):
        gate.validate(attestation(proof_b64="untrusted"))


def test_parity_gate_rejects_duplicate_quorum_sources():
    gate = ParityGate(lambda _proof: True, clock=lambda: 1002.0)
    with pytest.raises(ParityError, match="quorum"):
        gate.validate(attestation(source_ids=["source-a", "source-a", "source-b"]))


def test_deposit_requires_strict_hex_for_settlement():
    deposit = Deposit("not-a-txid", 100_000, 1, "addr", "regtest", vout=0)
    with pytest.raises(ExecutorError, match="32 bytes in HEX"):
        deposit.validate(require_hex=True)

    valid = Deposit(
        "a" * 64, 100_000, 1, "addr", "regtest", vout=0,
        script_pubkey_hex="51", validated_hex=True,
    )
    valid.validate(require_hex=True)
