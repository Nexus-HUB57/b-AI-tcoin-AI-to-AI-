"""Verificação de webhooks Ed25519 para o nó nativo.

O módulo não importa nem altera os serviços existentes. A integração é feita por
``WebhookAuthenticator.authenticate_and_record`` e pelo adaptador opcional.

Envelope assinado (JSON):
    {
      "version": 1, "event_id": "...", "source_node": "...",
      "event_type": "...", "created_at": 1710000000,
      "expires_at": 1710000300, "sequence": 1, "key_id": "...",
      "payload": {...}, "payload_hash": "sha256 hex",
      "signature": "base64 Ed25519"
    }

A assinatura cobre ``webhook.v1\\n`` + JSON canônico do envelope sem
``signature``. O hash cobre o JSON canônico de ``payload``.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class AuthError(ValueError):
    """Erro de validação; a mensagem é segura para retornar ao chamador."""



def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_payload(payload: Mapping[str, Any]) -> bytes:
    if not isinstance(payload, Mapping):
        raise AuthError("payload must be an object")
    return _canonical(payload)


def payload_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(payload)).hexdigest()


def _b64(value: str, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise AuthError(f"{label} is required")
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise AuthError(f"invalid {label}") from exc
    return raw


@dataclass(frozen=True)
class EventEnvelope:
    version: int
    event_id: str
    source_node: str
    event_type: str
    created_at: float
    expires_at: float
    sequence: int
    key_id: str
    payload: Mapping[str, Any]
    payload_hash: str
    signature: str

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "EventEnvelope":
        if not isinstance(raw, Mapping):
            raise AuthError("envelope must be an object")
        required = ("version", "event_id", "source_node", "event_type", "created_at", "expires_at", "sequence", "key_id", "payload", "payload_hash", "signature")
        missing = [k for k in required if k not in raw]
        if missing:
            raise AuthError("missing envelope fields: " + ", ".join(missing))
        try:
            result = cls(
                version=int(raw["version"]), event_id=str(raw["event_id"]), source_node=str(raw["source_node"]),
                event_type=str(raw["event_type"]), created_at=float(raw["created_at"]), expires_at=float(raw["expires_at"]),
                sequence=int(raw["sequence"]), key_id=str(raw["key_id"]), payload=raw["payload"],
                payload_hash=str(raw["payload_hash"]), signature=str(raw["signature"]),
            )
        except (TypeError, ValueError) as exc:
            raise AuthError("invalid envelope field type") from exc
        if result.version != 1 or not result.event_id or not result.source_node or not result.event_type:
            raise AuthError("invalid envelope identity or version")
        if len(result.event_id) > 256 or len(result.source_node) > 256 or len(result.event_type) > 128:
            raise AuthError("envelope identity field too long")
        return result

    def unsigned_dict(self) -> dict[str, Any]:
        return {"version": self.version, "event_id": self.event_id, "source_node": self.source_node,
                "event_type": self.event_type, "created_at": self.created_at, "expires_at": self.expires_at,
                "sequence": self.sequence, "key_id": self.key_id, "payload": self.payload, "payload_hash": self.payload_hash}

    def signing_bytes(self) -> bytes:
        return b"webhook.v1\n" + _canonical(self.unsigned_dict())


class WebhookAuthenticator:
    """Valida e registra eventos atomicamente em SQLite."""

    def __init__(self, registry_path: str, state_db_path: str, max_skew_seconds: int = 300, max_ttl_seconds: int = 900):
        if max_skew_seconds < 0 or max_ttl_seconds <= 0:
            raise ValueError("invalid time limits")
        self.registry_path = Path(registry_path)
        self.max_skew_seconds = max_skew_seconds
        self.max_ttl_seconds = max_ttl_seconds
        self.db = sqlite3.connect(state_db_path, check_same_thread=False, timeout=30.0)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self._lock = threading.RLock()
        with self.db:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS webhook_auth_state (
                    source_node TEXT PRIMARY KEY, last_sequence INTEGER NOT NULL, updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS webhook_auth_events (
                    event_id TEXT PRIMARY KEY, source_node TEXT NOT NULL, sequence INTEGER NOT NULL,
                    payload_hash TEXT NOT NULL, accepted_at REAL NOT NULL
                );
            """)

    def close(self) -> None:
        with self._lock:
            self.db.close()

    def _registry(self) -> dict[str, Any]:
        try:
            value = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise AuthError("trusted key registry not configured") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthError("invalid trusted key registry") from exc
        if not isinstance(value, dict) or value.get("version") not in (1, None) or not isinstance(value.get("keys"), dict):
            raise AuthError("trusted key registry must contain version and keys")
        return value

    def _entry(self, key_id: str, now: float) -> dict[str, Any]:
        entry = self._registry()["keys"].get(key_id)
        if not isinstance(entry, dict) or entry.get("status") not in ("active", "verify_only"):
            raise AuthError("unknown or inactive key")
        if entry.get("not_before") is not None and now < float(entry["not_before"]):
            raise AuthError("key is not valid yet")
        if entry.get("valid_until") is not None and now >= float(entry["valid_until"]):
            raise AuthError("key expired")
        if not isinstance(entry.get("node_id"), str) or not isinstance(entry.get("public_key_b64"), str):
            raise AuthError("invalid key registry entry")
        return entry

    def authenticate_and_record(self, envelope: EventEnvelope, now: Optional[float] = None) -> tuple[bool, str]:
        now = time.time() if now is None else float(now)
        if envelope.created_at > now + self.max_skew_seconds:
            raise AuthError("event timestamp is in the future")
        if envelope.expires_at <= envelope.created_at or envelope.expires_at < now - self.max_skew_seconds:
            raise AuthError("event expired")
        if envelope.expires_at - envelope.created_at > self.max_ttl_seconds:
            raise AuthError("event TTL exceeds limit")
        if envelope.sequence < 1:
            raise AuthError("sequence must be positive")
        entry = self._entry(envelope.key_id, now)
        if entry["node_id"] != envelope.source_node:
            raise AuthError("key is not registered for source node")
        if envelope.payload_hash != payload_hash(envelope.payload):
            raise AuthError("invalid payload hash")
        public_key = _b64(entry["public_key_b64"], "public key")
        if len(public_key) != 32:
            raise AuthError("Ed25519 public key must be 32 bytes")
        signature = _b64(envelope.signature, "signature")
        if len(signature) != 64:
            raise AuthError("Ed25519 signature must be 64 bytes")
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, envelope.signing_bytes())
        except (InvalidSignature, ValueError) as exc:
            raise AuthError("invalid signature") from exc
        with self._lock, self.db:
            prior = self.db.execute("SELECT payload_hash FROM webhook_auth_events WHERE event_id=?", (envelope.event_id,)).fetchone()
            if prior:
                if prior[0] != envelope.payload_hash:
                    raise AuthError("event_id reused with different payload")
                return True, "duplicate"
            row = self.db.execute("SELECT last_sequence FROM webhook_auth_state WHERE source_node=?", (envelope.source_node,)).fetchone()
            if row and envelope.sequence <= int(row[0]):
                raise AuthError("replayed or out-of-order sequence")
            self.db.execute("INSERT INTO webhook_auth_events VALUES(?,?,?,?,?)", (envelope.event_id, envelope.source_node, envelope.sequence, envelope.payload_hash, now))
            self.db.execute("INSERT INTO webhook_auth_state VALUES(?,?,?) ON CONFLICT(source_node) DO UPDATE SET last_sequence=excluded.last_sequence, updated_at=excluded.updated_at", (envelope.source_node, envelope.sequence, now))
        return True, "accepted"

    def validate(self, envelope: EventEnvelope) -> tuple[bool, str]:
        """Alias compatível com o autenticador anexado."""
        return self.authenticate_and_record(envelope)
