"""Gate econômico fail-closed para swaps BAIT/USDT.

O módulo não busca preços nem inventa um oráculo. O operador deve injetar um
verificador que valide a assinatura/attestation das fontes autorizadas. Sem
esse verificador, nenhum settlement pode ser habilitado.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional


class ParityError(ValueError):
    pass


@dataclass(frozen=True)
class ParityAttestation:
    pair: str
    bait_usdt_ppm: int
    usdt_usd_ppm: int
    usd_brl_ppm: int
    observed_at: float
    expires_at: float
    round_id: str
    source_ids: tuple[str, ...]
    quorum: int
    proof_b64: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "pair": self.pair,
            "bait_usdt_ppm": self.bait_usdt_ppm,
            "usdt_usd_ppm": self.usdt_usd_ppm,
            "usd_brl_ppm": self.usd_brl_ppm,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "round_id": self.round_id,
            "source_ids": list(self.source_ids),
            "quorum": self.quorum,
        }

    def digest(self) -> str:
        encoded = json.dumps(self.unsigned_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(b"bait.swap.parity.v1\n" + encoded).hexdigest()

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ParityAttestation":
        try:
            attestation = cls(
                pair=str(raw["pair"]),
                bait_usdt_ppm=int(raw["bait_usdt_ppm"]),
                usdt_usd_ppm=int(raw["usdt_usd_ppm"]),
                usd_brl_ppm=int(raw["usd_brl_ppm"]),
                observed_at=float(raw["observed_at"]),
                expires_at=float(raw["expires_at"]),
                round_id=str(raw["round_id"]),
                source_ids=tuple(str(item) for item in raw["source_ids"]),
                quorum=int(raw["quorum"]),
                proof_b64=str(raw.get("proof_b64", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ParityError("malformed parity attestation") from exc
        if raw.get("version", 1) != 1:
            raise ParityError("unsupported parity attestation version")
        return attestation

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "proof_b64": self.proof_b64}


class ParityGate:
    """Valida uma attestation BAIT/USDT antes de cotar ou liquidar."""

    def __init__(
        self,
        verify_proof: Optional[Callable[[ParityAttestation], bool]],
        *,
        tolerance_bps: int = 50,
        max_age_seconds: int = 60,
        min_quorum: int = 3,
        clock: Callable[[], float] = time.time,
    ):
        if verify_proof is None:
            raise ParityError("an external attestation verifier is required")
        if tolerance_bps < 0 or tolerance_bps > 10_000 or max_age_seconds <= 0 or min_quorum < 1:
            raise ParityError("invalid parity gate configuration")
        self.verify_proof = verify_proof
        self.tolerance_bps = tolerance_bps
        self.max_age_seconds = max_age_seconds
        self.min_quorum = min_quorum
        self.clock = clock

    def validate(self, attestation: ParityAttestation, now: Optional[float] = None) -> str:
        now = self.clock() if now is None else float(now)
        if not math.isfinite(now):
            raise ParityError("invalid parity clock")
        if attestation.pair != "BAIT/USDT":
            raise ParityError("only BAIT/USDT parity is accepted")
        if not attestation.round_id or not attestation.proof_b64:
            raise ParityError("parity proof and round are required")
        if len(attestation.source_ids) < self.min_quorum or attestation.quorum < self.min_quorum:
            raise ParityError("parity quorum is insufficient")
        if attestation.quorum > len(attestation.source_ids) or len(set(attestation.source_ids)) != len(attestation.source_ids):
            raise ParityError("invalid parity source quorum")
        if any(value <= 0 for value in (attestation.bait_usdt_ppm, attestation.usdt_usd_ppm, attestation.usd_brl_ppm)):
            raise ParityError("parity prices must be positive")
        if attestation.expires_at <= attestation.observed_at or attestation.expires_at < now:
            raise ParityError("parity attestation is expired")
        if attestation.observed_at > now or now - attestation.observed_at > self.max_age_seconds:
            raise ParityError("parity attestation is stale or from the future")
        tolerance = 1_000_000 * self.tolerance_bps // 10_000
        if abs(attestation.bait_usdt_ppm - 1_000_000) > tolerance:
            raise ParityError("BAIT is outside the configured USDT parity band")
        try:
            verified = bool(self.verify_proof(attestation))
        except Exception as exc:
            raise ParityError("parity proof verification failed") from exc
        if not verified:
            raise ParityError("parity proof was not verified")
        return attestation.digest()
