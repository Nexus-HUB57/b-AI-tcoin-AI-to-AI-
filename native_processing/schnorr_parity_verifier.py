"""Verificador Schnorr BIP-340 para ParityAttestation (ParityGate.verify_proof).

Implementação fail-closed alinhada ao baitcoin_core.cryptography.schnorr (BIP-340).

Formato do proof_b64
--------------------
Base64( concatenated signatures )

Cada assinatura é 64 bytes (r || s) no formato BIP-340.
A ordem das assinaturas corresponde à ordem de source_ids na attestation.

  proof = sig[0] || sig[1] || ... || sig[n-1]
  n == len(source_ids)

Mensagem assinada
-----------------
  message = SHA256( "bait.swap.parity.v1\\n" || canonical_json(attestation.unsigned_dict()) )

Isso é exatamente o mesmo digest usado por ParityAttestation.digest(),
convertido de hex para bytes.

Uso
---
  from native_processing.schnorr_parity_verifier import make_schnorr_verify_proof
  from native_processing.parity_gate import ParityGate

  authorized = {
      "oracle-coingecko": bytes.fromhex("...32-byte-xonly-pubkey..."),
      "oracle-binance":   bytes.fromhex("..."),
      "oracle-internal":  bytes.fromhex("..."),
  }
  verify_proof = make_schnorr_verify_proof(authorized)
  gate = ParityGate(verify_proof, min_quorum=3, tolerance_bps=50)
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Callable, Dict, Mapping, Optional

logger = logging.getLogger("baitcoin.parity.schnorr")

# ---------------------------------------------------------------------------
# BIP-340 primitives (self-contained, compatible with baitcoin_core)
# ---------------------------------------------------------------------------

try:
    import ecdsa
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "ecdsa is required for Schnorr BIP-340 verification: pip install ecdsa"
    ) from exc

_CURVE = ecdsa.SECP256k1
_P = _CURVE.curve.p()
_N = _CURVE.order
_G = _CURVE.generator
_INFINITE = ecdsa.ellipticcurve.INFINITY


def _tagged_hash(tag: str, message: bytes) -> bytes:
    tag_hash = hashlib.sha256(tag.encode("ascii")).digest()
    return hashlib.sha256(tag_hash + tag_hash + message).digest()


def _bytes32(value: int) -> bytes:
    return value.to_bytes(32, byteorder="big")


def _lift_x(x: int, even_y: bool = True):
    if not isinstance(x, int) or x < 0 or x >= _P:
        return None
    y_sq = (pow(x, 3, _P) + 7) % _P
    y = pow(y_sq, (_P + 1) // 4, _P)
    if pow(y, 2, _P) != y_sq:
        return None
    if (y & 1) != (0 if even_y else 1):
        y = _P - y
    return ecdsa.ellipticcurve.PointJacobi(_CURVE.curve, x, y, 1)


def _affine(point):
    if point is None or point == _INFINITE:
        return None
    try:
        affine = point.to_affine()
        if affine == _INFINITE:
            return None
        return affine
    except Exception:
        return None


def bip340_verify(pubkey_xonly: bytes, message: bytes, signature_64: bytes) -> bool:
    """Verifica uma assinatura BIP-340 (r||s = 64 bytes) sobre message.

    pubkey_xonly: 32 bytes (coordenada x da chave pública).
    """
    if not isinstance(pubkey_xonly, bytes) or len(pubkey_xonly) != 32:
        return False
    if not isinstance(message, bytes):
        return False
    if not isinstance(signature_64, bytes) or len(signature_64) != 64:
        return False

    r_bytes = signature_64[:32]
    s = int.from_bytes(signature_64[32:], "big")
    if s < 0 or s >= _N:
        return False
    r = int.from_bytes(r_bytes, "big")
    if r >= _P:
        return False

    P = _lift_x(int.from_bytes(pubkey_xonly, "big"), even_y=True)
    if P is None:
        return False

    e = int.from_bytes(
        _tagged_hash("BIP0340/challenge", r_bytes + pubkey_xonly + message), "big"
    ) % _N

    # R = s*G - e*P  (implemented as s*G + (n-e)*P)
    R = s * _G + (_N - e) * P
    R_affine = _affine(R)
    if R_affine is None:
        return False
    if R_affine.y() & 1:  # must be even y
        return False
    return R_affine.x() == r


# ---------------------------------------------------------------------------
# Attestation message (must match ParityAttestation.digest())
# ---------------------------------------------------------------------------

def attestation_message_bytes(attestation) -> bytes:
    """Reconstrói a mensagem que deve ser assinada.

    Compatível com:
      hashlib.sha256(b"bait.swap.parity.v1\\n" + canonical_json).hexdigest()
    """
    unsigned = {
        "version": 1,
        "pair": attestation.pair,
        "bait_usdt_ppm": attestation.bait_usdt_ppm,
        "usdt_usd_ppm": attestation.usdt_usd_ppm,
        "usd_brl_ppm": attestation.usd_brl_ppm,
        "observed_at": attestation.observed_at,
        "expires_at": attestation.expires_at,
        "round_id": attestation.round_id,
        "source_ids": list(attestation.source_ids),
        "quorum": attestation.quorum,
    }
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(b"bait.swap.parity.v1\n" + encoded).digest()


# ---------------------------------------------------------------------------
# Factory: make_schnorr_verify_proof
# ---------------------------------------------------------------------------

def make_schnorr_verify_proof(
    authorized_pubkeys: Mapping[str, bytes],
    *,
    require_all_present: bool = False,
) -> Callable:
    """Cria um verify_proof Schnorr BIP-340 para uso no ParityGate.

    Args:
        authorized_pubkeys: dict source_id → 32-byte x-only pubkey.
        require_all_present: se True, todas as sources da attestation
                             devem estar na allowlist (mais restritivo).

    Returns:
        Callable[[ParityAttestation], bool] pronto para ParityGate(...).
    """
    if not authorized_pubkeys:
        raise ValueError("authorized_pubkeys must not be empty")

    normalized: Dict[str, bytes] = {}
    for source_id, pub in authorized_pubkeys.items():
        if not isinstance(source_id, str) or not source_id:
            raise ValueError(f"invalid source_id: {source_id!r}")
        if isinstance(pub, str):
            pub = bytes.fromhex(pub)
        if not isinstance(pub, bytes) or len(pub) != 32:
            raise ValueError(f"pubkey for {source_id!r} must be 32 bytes (x-only)")
        normalized[source_id] = pub

    def verify_proof(attestation) -> bool:
        # 1. proof_b64 obrigatório
        proof_b64 = getattr(attestation, "proof_b64", "") or ""
        if not proof_b64:
            logger.warning("parity proof missing proof_b64")
            return False

        # 2. Decode
        try:
            proof = base64.b64decode(proof_b64, validate=True)
        except Exception:
            logger.warning("parity proof_b64 is not valid base64")
            return False

        source_ids = list(getattr(attestation, "source_ids", ()))
        quorum = int(getattr(attestation, "quorum", 0))
        n = len(source_ids)

        if n == 0 or quorum < 1:
            return False

        # 3. proof deve conter exatamente n assinaturas de 64 bytes
        expected_len = n * 64
        if len(proof) != expected_len:
            logger.warning(
                "parity proof length mismatch: got %d, expected %d (%d sigs)",
                len(proof), expected_len, n,
            )
            return False

        # 4. Mensagem a ser verificada
        try:
            message = attestation_message_bytes(attestation)
        except Exception as exc:
            logger.warning("failed to build attestation message: %s", exc)
            return False

        # 5. Verificar cada assinatura
        valid = 0
        for i, source_id in enumerate(source_ids):
            if source_id not in normalized:
                if require_all_present:
                    logger.warning("source %r not in authorized set", source_id)
                    return False
                continue

            sig = proof[i * 64 : (i + 1) * 64]
            pubkey = normalized[source_id]

            if bip340_verify(pubkey, message, sig):
                valid += 1
            else:
                logger.debug("invalid BIP-340 signature from source %r", source_id)

        if valid < quorum:
            logger.warning(
                "parity quorum not met: valid=%d required=%d", valid, quorum
            )
            return False

        return True

    return verify_proof


# ---------------------------------------------------------------------------
# Helpers de teste / geração de proof (apenas para ambiente controlado)
# ---------------------------------------------------------------------------

def build_proof_b64(
    attestation,
    signers: Mapping[str, "object"],
) -> str:
    """Constrói proof_b64 a partir de signers (source_id → objeto com .sign(msg)).

    Cada signer deve implementar:
        sign(message: bytes) -> object com atributo .raw (64 bytes)
    Compatível com SchnorrKeyPair.sign() do baitcoin_core.
    """
    message = attestation_message_bytes(attestation)
    parts = []
    for source_id in attestation.source_ids:
        if source_id not in signers:
            raise KeyError(f"no signer for source_id {source_id!r}")
        sig = signers[source_id].sign(message)
        raw = sig.raw if hasattr(sig, "raw") else bytes(sig)
        if len(raw) != 64:
            raise ValueError(f"signature from {source_id!r} is not 64 bytes")
        parts.append(raw)
    return base64.b64encode(b"".join(parts)).decode("ascii")


def make_test_verify_proof_always_true() -> Callable:
    """Apenas para regtest / dry-run. NÃO usar em produção."""
    return lambda _: True
