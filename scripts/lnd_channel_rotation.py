#!/usr/bin/env python3
"""Atomic LND gRPC session rotation with post-activation node validation."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable

from .macaroon_rotation import MacaroonRotationError, RotatingMacaroonProvider


class LndChannelRotationError(RuntimeError):
    pass


@dataclass(frozen=True)
class LndConnection:
    channel: Any
    lightning: Any
    router: Any
    network: str
    identity_pubkey: str


class LndGrpcConnectionManager:
    """Rotate credentials and replace the live gRPC session only after validation."""

    def __init__(self, provider: RotatingMacaroonProvider, connection_factory: Callable[[RotatingMacaroonProvider], LndConnection], *, required_network: str = "mainnet"):
        self.provider = provider
        self.connection_factory = connection_factory
        self.required_network = required_network
        self._lock = threading.RLock()
        self._connection: LndConnection | None = None

    @staticmethod
    def _field(obj: Any, name: str, default: Any = None) -> Any:
        return getattr(obj, name, default)

    def _validate(self, connection: LndConnection) -> LndConnection:
        try:
            response = connection.lightning.GetInfo(timeout=10)
        except Exception as exc:
            raise LndChannelRotationError("LND GetInfo failed during channel validation") from exc
        chains = self._field(response, "chains", [])
        networks = {str(self._field(item, "network", "")).lower() for item in chains}
        if self.required_network not in networks:
            raise LndChannelRotationError("recreated channel is not connected to the required network")
        identity = str(self._field(response, "identity_pubkey", ""))
        if not identity:
            raise LndChannelRotationError("recreated channel returned no node identity")
        return LndConnection(connection.channel, connection.lightning, connection.router, self.required_network, identity)

    @staticmethod
    def _close(connection: LndConnection | None) -> None:
        if connection is not None:
            close = getattr(connection.channel, "close", None)
            if callable(close):
                close()

    def initialize(self) -> LndConnection:
        with self._lock:
            if self._connection is not None:
                return self._connection
            try:
                self._connection = self._validate(self.connection_factory(self.provider))
            except Exception as exc:
                raise LndChannelRotationError("initial LND channel validation failed") from exc
            return self._connection

    def current(self) -> LndConnection:
        with self._lock:
            if self._connection is None:
                return self.initialize()
            return self._connection

    def activate_and_reconnect(self, new_macaroon: bytes) -> LndConnection:
        """Stage/activate, rebuild channel, validate, then atomically swap sessions."""
        with self._lock:
            old = self._connection
            try:
                self.provider.stage(new_macaroon)
                self.provider.activate()
                candidate = self._validate(self.connection_factory(self.provider))
            except (MacaroonRotationError, LndChannelRotationError, OSError) as exc:
                try:
                    self.provider.rollback()
                except MacaroonRotationError as rollback_exc:
                    raise LndChannelRotationError("rotation failed and rollback also failed") from rollback_exc
                # Keep the old validated connection active; close no candidate if factory failed before return.
                raise LndChannelRotationError("macaroon rotation/reconnection failed; previous credential restored") from exc
            except Exception as exc:
                try:
                    self.provider.rollback()
                except MacaroonRotationError as rollback_exc:
                    raise LndChannelRotationError("rotation failed and rollback also failed") from rollback_exc
                raise LndChannelRotationError("unexpected rotation/reconnection failure") from exc
            self._connection = candidate
            self._close(old)
            return candidate

    def close(self) -> None:
        with self._lock:
            self._close(self._connection)
            self._connection = None


__all__ = ["LndConnection", "LndGrpcConnectionManager", "LndChannelRotationError"]
