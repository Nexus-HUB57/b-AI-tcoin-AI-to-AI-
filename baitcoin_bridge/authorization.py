"""Cryptographic authorization of relayer proofs before BridgeManager mutation."""
from __future__ import annotations

import base64
import json
from typing import Iterable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class AuthorizationError(ValueError):
    """Invalid signer, envelope, or signature."""


def proof_signing_bytes(event_id: str, transfer_id: str, chain_id: int, amount_sats: int, proof: Iterable[str]) -> bytes:
    if not isinstance(event_id, str) or not event_id:
        raise AuthorizationError("invalid event_id")
    if not isinstance(transfer_id, str) or not transfer_id:
        raise AuthorizationError("invalid transfer_id")
    if type(chain_id) is not int or chain_id <= 0:
        raise AuthorizationError("invalid chain_id")
    if type(amount_sats) is not int or amount_sats <= 0:
        raise AuthorizationError("invalid amount_sats")
    proof = list(proof)
    if any(not isinstance(item, str) for item in proof):
        raise AuthorizationError("invalid Merkle proof")
    envelope = {
        "version": 1,
        "event_id": event_id,
        "transfer_id": transfer_id,
        "chain_id": chain_id,
        "amount_sats": amount_sats,
        "proof": proof,
    }
    return b"bait.bridge.proof.v1\n" + json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class RelayerAuthorization:
    """Trusted public-key registry that verifies every relayer signature."""

    def __init__(self, public_keys: Mapping[str, str | bytes]) -> None:
        if not isinstance(public_keys, Mapping) or not public_keys:
            raise AuthorizationError("at least one relayer public key is required")
        self._keys: dict[str, Ed25519PublicKey] = {}
        for signer_id, encoded in public_keys.items():
            if not isinstance(signer_id, str) or not signer_id:
                raise AuthorizationError("invalid signer_id")
            try:
                raw = base64.b64decode(encoded, validate=True) if isinstance(encoded, str) else bytes(encoded)
                if len(raw) != 32:
                    raise ValueError("public key length")
                self._keys[signer_id] = Ed25519PublicKey.from_public_bytes(raw)
            except Exception as exc:
                raise AuthorizationError(f"invalid public key for {signer_id}") from exc

    @staticmethod
    def sign(private_key: Ed25519PrivateKey, event_id: str, transfer_id: str, chain_id: int, amount_sats: int, proof: Iterable[str]) -> str:
        return base64.b64encode(private_key.sign(proof_signing_bytes(event_id, transfer_id, chain_id, amount_sats, proof))).decode("ascii")

    def verify_one(self, *, event_id: str, transfer_id: str, chain_id: int, amount_sats: int, proof: Iterable[str], signer_id: str, signature_b64: str) -> tuple[str, str]:
        if not isinstance(signer_id, str) or not signer_id:
            raise AuthorizationError("invalid signer_id")
        key = self._keys.get(signer_id)
        if key is None:
            raise AuthorizationError(f"unknown signer: {signer_id}")
        if not isinstance(signature_b64, str):
            raise AuthorizationError(f"invalid signature for {signer_id}")
        try:
            signature = base64.b64decode(signature_b64, validate=True)
            if len(signature) != 64:
                raise ValueError("signature length")
            key.verify(signature, proof_signing_bytes(event_id, transfer_id, chain_id, amount_sats, proof))
        except (ValueError, InvalidSignature) as exc:
            raise AuthorizationError(f"invalid signature for {signer_id}") from exc
        return signer_id, signature_b64

    def verify(self, event_id: str, transfer_id: str, chain_id: int, amount_sats: int, proof: Iterable[str], signatures: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
        verified = []
        seen: set[str] = set()
        for signer_id, signature_b64 in signatures:
            if signer_id in seen:
                raise AuthorizationError(f"duplicate signer: {signer_id}")
            seen.add(signer_id)
            verified.append(self.verify_one(event_id=event_id, transfer_id=transfer_id, chain_id=chain_id, amount_sats=amount_sats, proof=proof, signer_id=signer_id, signature_b64=signature_b64))
        if not verified:
            raise AuthorizationError("at least one signature is required")
        return verified


__all__ = ["AuthorizationError", "RelayerAuthorization", "proof_signing_bytes"]
