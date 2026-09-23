"""Strict structural PSBT envelope checks, without signing or extraction."""
from __future__ import annotations

import base64
import binascii


PSBT_MAGIC = b"psbt\xff"
MAX_PSBT_BYTES = 100 * 1024 * 1024


class PsbtFormatError(ValueError):
    """PSBT is not a valid bounded envelope."""


def decode_psbt_base64(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise PsbtFormatError("PSBT base64 is required")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PsbtFormatError("invalid PSBT base64") from exc
    if len(raw) < len(PSBT_MAGIC) or len(raw) > MAX_PSBT_BYTES:
        raise PsbtFormatError("PSBT size is outside bounds")
    if raw[: len(PSBT_MAGIC)] != PSBT_MAGIC:
        raise PsbtFormatError("invalid PSBT magic")
    return raw


def psbt_payload_sha256(value: str) -> str:
    import hashlib
    return hashlib.sha256(decode_psbt_base64(value)).hexdigest()


__all__ = ["MAX_PSBT_BYTES", "PSBT_MAGIC", "PsbtFormatError", "decode_psbt_base64", "psbt_payload_sha256"]
