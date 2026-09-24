"""FrostVerifier + wiring ParityGate para group key (FROST / multi-sig).

Dois modos de verify_proof:

1. ConcatSchnorrVerifier (v1 atual)
   - proof_b64 = Base64(sig0||sig1||…||sigN)  — N×64 bytes
   - authorized_pubkeys = { oracle-a: PKa, … }

2. FrostVerifier (v2)
   - proof_b64 = Base64(σ)  — 64 bytes únicos
   - authorized_pubkeys = { "frost-group": group_PK }

Uso com load_parity_gate:

  from native_processing.parity_gate_factory import load_parity_gate
  gate = load_parity_gate("secrets/oracles-staging/parity_gate_config.staging.json")

  # ou explícito:
  from native_processing.frost_verifier import make_frost_verify_proof
  verify = make_frost_verify_proof(group_pubkey_xonly)
  gate = ParityGate(verify, min_quorum=1)
"""
from __future__ import annotations

import base64
import logging
from typing import Callable, Dict, Mapping, Optional, Union

from native_processing.schnorr_parity_verifier import (
    attestation_message_bytes,
    bip340_verify,
    make_schnorr_verify_proof,
)

logger = logging.getLogger("baitcoin.parity.frost")


def _as_bytes32(pub: Union[str, bytes]) -> bytes:
    if isinstance(pub, str):
        pub = bytes.fromhex(pub)
    if len(pub) == 33 and pub[0] in (2, 3):
        pub = pub[1:]
    if len(pub) != 32:
        raise ValueError("pubkey must be 32-byte x-only (or 33-byte compressed)")
    return pub


def make_frost_verify_proof(
    group_pubkey: Union[str, bytes],
    *,
    source_id: str = "frost-group",
) -> Callable:
    """verify_proof para uma única assinatura BIP-340 sobre a group key FROST.

    Compatível com proof gerado por frost-secp256k1 (64 bytes).
    O campo source_ids da attestation pode conter [source_id] ou a lista lógica
    dos oráculos; a verificação usa apenas group_pubkey + proof de 64 bytes.
    """
    pk = _as_bytes32(group_pubkey)

    def verify_proof(attestation) -> bool:
        proof_b64 = getattr(attestation, "proof_b64", "") or ""
        if not proof_b64:
            logger.warning("frost proof missing proof_b64")
            return False
        try:
            proof = base64.b64decode(proof_b64, validate=True)
        except Exception:
            logger.warning("frost proof_b64 invalid base64")
            return False
        if len(proof) != 64:
            logger.warning(
                "frost proof length %d (expected 64 for aggregated sig)", len(proof)
            )
            return False
        try:
            message = attestation_message_bytes(attestation)
        except Exception as exc:
            logger.warning("attestation message build failed: %s", exc)
            return False
        ok = bip340_verify(pk, message, proof)
        if not ok:
            logger.warning("frost BIP-340 verify failed for %s", source_id)
        return ok

    return verify_proof


def make_verifier_from_authorized(
    authorized_pubkeys: Mapping[str, Union[str, bytes]],
    *,
    scheme: str = "auto",
) -> Callable:
    """Escolhe Concat vs Frost com base no config.

    scheme:
      - "concat" | "multi-sig" → multi-sig concatenada
      - "frost" | "frost-pedersen-dkg" → group key
      - "auto" → se só existe "frost-group" (ou 1 key), usa Frost; senão Concat
    """
    pubs = {k: _as_bytes32(v) for k, v in authorized_pubkeys.items()}
    scheme_l = (scheme or "auto").lower()

    if scheme_l in ("frost", "frost-pedersen-dkg", "musig2"):
        if "frost-group" in pubs:
            return make_frost_verify_proof(pubs["frost-group"])
        if len(pubs) == 1:
            return make_frost_verify_proof(next(iter(pubs.values())))
        raise ValueError("frost scheme requires frost-group pubkey")

    if scheme_l in ("concat", "multi-sig", "schnorr-concat"):
        return make_schnorr_verify_proof(pubs)

    # auto
    if "frost-group" in pubs and len(pubs) == 1:
        return make_frost_verify_proof(pubs["frost-group"])
    if "frost-group" in pubs:
        # hybrid config: prefer frost-group if present alone-ish
        return make_frost_verify_proof(pubs["frost-group"])
    return make_schnorr_verify_proof(pubs)
