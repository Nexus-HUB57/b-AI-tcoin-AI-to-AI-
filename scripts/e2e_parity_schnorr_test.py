#!/usr/bin/env python3
"""E2E: substitui lambda _: True por chaves Schnorr reais de teste.

Valida o caminho completo:
  keygen → sign attestation → ParityGate.validate → admit intent

Não usa rede, Bitcoin Core nem fundos reais.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from native_processing.parity_gate import ParityGate, ParityAttestation  # noqa: E402
from native_processing.schnorr_keypair import SchnorrKeyPair  # noqa: E402
from native_processing.schnorr_parity_verifier import make_schnorr_verify_proof  # noqa: E402
from native_processing.parity_attestation_builder import build_signed_attestation  # noqa: E402


def run() -> dict:
    # 1. Gerar 3 oráculos de teste (em memória — nunca persistir em CI)
    oracles = {
        "oracle-a": SchnorrKeyPair.generate(),
        "oracle-b": SchnorrKeyPair.generate(),
        "oracle-c": SchnorrKeyPair.generate(),
    }
    authorized = {oid: kp.pub_bytes for oid, kp in oracles.items()}

    # 2. Gate real (não é mais lambda _: True)
    gate = ParityGate(
        make_schnorr_verify_proof(authorized),
        min_quorum=3,
        tolerance_bps=50,
        max_age_seconds=120,
        clock=time.time,
    )

    # 3. Attestation assinada
    att = build_signed_attestation(oracles, bait_usdt=1.0, ttl_seconds=90)
    digest = gate.validate(att)
    assert digest == att.digest()

    # 4. Falha esperada: preço fora da banda
    try:
        bad = ParityAttestation(
            pair="BAIT/USDT",
            bait_usdt_ppm=1_100_000,  # +10% — fora de 50 bps
            usdt_usd_ppm=1_000_000,
            usd_brl_ppm=5_000_000,
            observed_at=att.observed_at,
            expires_at=att.expires_at,
            round_id=att.round_id,
            source_ids=att.source_ids,
            quorum=3,
            proof_b64=att.proof_b64,  # proof antigo (digest diferente)
        )
        gate.validate(bad)
        band_ok = False
    except Exception:
        band_ok = True

    # 5. Falha esperada: quorum insuficiente (só 2 chaves autorizadas)
    gate2 = ParityGate(
        make_schnorr_verify_proof({
            "oracle-a": oracles["oracle-a"].pub_bytes,
            "oracle-b": oracles["oracle-b"].pub_bytes,
        }),
        min_quorum=3,
        clock=time.time,
    )
    try:
        gate2.validate(att)
        quorum_ok = False
    except Exception:
        quorum_ok = True

    return {
        "digest": digest,
        "pubkeys": {k: v.public_key_hex for k, v in oracles.items()},
        "band_rejection": band_ok,
        "quorum_rejection": quorum_ok,
        "status": "PASS" if (band_ok and quorum_ok) else "FAIL",
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
