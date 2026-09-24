"""ParityGate de teste com chaves Schnorr reais (substitui lambda _: True).

Uso nos scripts E2E:
  from native_processing.test_parity_gate import make_test_parity_gate, make_test_signers

  gate = make_test_parity_gate()          # 3 oráculos em memória
  signers = make_test_signers()           # para assinar attestations
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from native_processing.parity_gate import ParityGate
from native_processing.schnorr_keypair import SchnorrKeyPair
from native_processing.schnorr_parity_verifier import make_schnorr_verify_proof
from native_processing.parity_attestation_builder import build_signed_attestation


def make_test_oracles() -> Dict[str, SchnorrKeyPair]:
    """Gera 3 keypairs efêmeros (não persistidos)."""
    return {
        "oracle-a": SchnorrKeyPair.generate(),
        "oracle-b": SchnorrKeyPair.generate(),
        "oracle-c": SchnorrKeyPair.generate(),
    }


def make_test_parity_gate(
    oracles: Optional[Mapping[str, SchnorrKeyPair]] = None,
    *,
    min_quorum: int = 3,
    tolerance_bps: int = 50,
    max_age_seconds: int = 300,
    clock: Callable[[], float] = time.time,
) -> Tuple[ParityGate, Dict[str, SchnorrKeyPair]]:
    """Retorna (ParityGate com verify_proof Schnorr real, oracles usados)."""
    if oracles is None:
        oracles = make_test_oracles()
    authorized = {oid: kp.pub_bytes for oid, kp in oracles.items()}
    verify = make_schnorr_verify_proof(authorized)
    gate = ParityGate(
        verify,
        min_quorum=min_quorum,
        tolerance_bps=tolerance_bps,
        max_age_seconds=max_age_seconds,
        clock=clock,
    )
    return gate, dict(oracles)


def make_test_signers(
    oracles: Optional[Mapping[str, SchnorrKeyPair]] = None,
) -> Dict[str, Any]:
    """Alias: retorna dict source_id → SchnorrKeyPair para build_signed_attestation."""
    if oracles is None:
        oracles = make_test_oracles()
    return dict(oracles)


def make_test_attestation_json(
    oracles: Optional[Mapping[str, SchnorrKeyPair]] = None,
    *,
    now: Optional[float] = None,
) -> str:
    """Attestation assinada serializada (para injetar em intents de teste)."""
    if oracles is None:
        oracles = make_test_oracles()
    att = build_signed_attestation(oracles, bait_usdt=1.0, ttl_seconds=120, now=now)
    return att.to_dict() if hasattr(att, "to_dict") else {
        "version": 1,
        "pair": att.pair,
        "bait_usdt_ppm": att.bait_usdt_ppm,
        "usdt_usd_ppm": att.usdt_usd_ppm,
        "usd_brl_ppm": att.usd_brl_ppm,
        "observed_at": att.observed_at,
        "expires_at": att.expires_at,
        "round_id": att.round_id,
        "source_ids": list(att.source_ids),
        "quorum": att.quorum,
        "proof_b64": att.proof_b64,
    }
