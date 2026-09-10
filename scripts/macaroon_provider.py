#!/usr/bin/env python3
"""Least-privilege macaroon providers for the LND gRPC channel."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Protocol


class MacaroonProviderError(RuntimeError):
    pass


class MacaroonProvider(Protocol):
    def load(self) -> bytes: ...


def validate_macaroon(value: bytes) -> bytes:
    if not isinstance(value, bytes) or not value or len(value) > 4096:
        raise MacaroonProviderError("macaroon must be non-empty and at most 4096 bytes")
    if b"\n" in value or b"\r" in value or b"\x00" in value:
        raise MacaroonProviderError("macaroon contains forbidden control characters")
    return value


class FileMacaroonProvider:
    """Read a macaroon from a root-owned or executor-owned 0400/0600 file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> bytes:
        try:
            mode = self.path.stat().st_mode
            value = self.path.read_bytes()
        except OSError as exc:
            raise MacaroonProviderError("unable to read macaroon file") from exc
        if mode & 0o077:
            raise MacaroonProviderError("macaroon file must not be readable by group or others")
        return validate_macaroon(value)


class CallableMacaroonProvider:
    """Adapt a secret-manager callback without exposing the returned secret."""

    def __init__(self, loader: Callable[[], bytes]):
        self.loader = loader

    def load(self) -> bytes:
        try:
            value = self.loader()
        except Exception as exc:
            raise MacaroonProviderError("secret manager macaroon load failed") from exc
        return validate_macaroon(value)


__all__ = ["MacaroonProvider", "MacaroonProviderError", "FileMacaroonProvider", "CallableMacaroonProvider", "validate_macaroon"]
