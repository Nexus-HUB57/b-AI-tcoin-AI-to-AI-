#!/usr/bin/env python3
"""Safe macaroon rotation primitives with atomic activation and rollback."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

try:
    from .macaroon_provider import MacaroonProviderError, validate_macaroon
except ImportError:  # direct script/module execution
    from macaroon_provider import MacaroonProviderError, validate_macaroon  # type: ignore


class MacaroonRotationError(RuntimeError):
    pass


class RotatingMacaroonProvider:
    """Maintain active, staged and previous macaroons without logging secrets."""

    def __init__(self, active_path: str | Path):
        self.active = Path(active_path)
        self.staged = self.active.with_name(self.active.name + ".next")
        self.previous = self.active.with_name(self.active.name + ".previous")
        self.active.parent.mkdir(parents=True, exist_ok=True)

    def _check_mode(self, path: Path) -> None:
        mode = path.stat().st_mode
        if mode & 0o077:
            raise MacaroonRotationError("macaroon file must not be group/world readable")

    def _atomic_write(self, path: Path, value: bytes) -> None:
        validate_macaroon(value)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        temporary_path = Path(temporary)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            self._check_mode(path)
        except (OSError, MacaroonProviderError) as exc:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise MacaroonRotationError("unable to write macaroon rotation file") from exc

    def load(self) -> bytes:
        try:
            self._check_mode(self.active)
            return validate_macaroon(self.active.read_bytes())
        except (OSError, MacaroonProviderError) as exc:
            raise MacaroonRotationError("active macaroon unavailable") from exc

    def stage(self, value: bytes) -> None:
        """Write a candidate without changing the active credential."""
        self._atomic_write(self.staged, value)

    def activate(self) -> None:
        """Atomically promote staged credential and retain previous for rollback."""
        if not self.staged.exists():
            raise MacaroonRotationError("no staged macaroon is available")
        self._check_mode(self.staged)
        # Validate before changing active state.
        validate_macaroon(self.staged.read_bytes())
        try:
            if self.active.exists():
                os.replace(self.active, self.previous)
            os.replace(self.staged, self.active)
            self._check_mode(self.active)
        except OSError as exc:
            raise MacaroonRotationError("macaroon activation failed") from exc

    def rollback(self) -> None:
        """Restore the previous credential, retaining current active as .next."""
        if not self.previous.exists():
            raise MacaroonRotationError("no previous macaroon is available")
        self._check_mode(self.previous)
        validate_macaroon(self.previous.read_bytes())
        try:
            if self.active.exists():
                os.replace(self.active, self.staged)
            os.replace(self.previous, self.active)
            self._check_mode(self.active)
        except OSError as exc:
            raise MacaroonRotationError("macaroon rollback failed") from exc


__all__ = ["RotatingMacaroonProvider", "MacaroonRotationError"]
