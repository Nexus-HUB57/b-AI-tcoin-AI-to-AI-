#!/usr/bin/env python3
"""Two-person, order-bound approval verification for live settlements."""
from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class ApprovalError(RuntimeError):
    pass


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def approval_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


@dataclass(frozen=True)
class Approval:
    payload: dict[str, Any]
    signature_b64: str


class ApprovalGate:
    """Require two distinct, trusted operators to approve one exact order."""

    def __init__(self, db_path: str, trusted_operators: dict[str, dict[str, Any]], *, now: Callable[[], float] = time.time, max_age_seconds: int = 300):
        self.db = sqlite3.connect(db_path, timeout=30.0)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.trusted_operators = trusted_operators
        self.now = now
        self.max_age_seconds = max_age_seconds
        with self.db:
            self.db.execute("""CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, operator_id TEXT NOT NULL,
                payload_hash TEXT NOT NULL, expires_at INTEGER NOT NULL, accepted_at INTEGER NOT NULL
            )""")

    def close(self) -> None:
        self.db.close()

    def _verify_one(self, approval: Approval, *, order_id: str, invoice_sha256: str, amount_sats: int, config_sha256: str) -> str:
        payload = approval.payload
        operator_id = payload.get("operator_id")
        operator = self.trusted_operators.get(operator_id)
        if not isinstance(operator, dict) or operator.get("status") != "active" or operator.get("role") != "settlement-approver":
            raise ApprovalError("operator is unknown, inactive, or has an invalid role")
        if payload.get("purpose") != "lightning-mainnet-settlement":
            raise ApprovalError("invalid approval purpose")
        if payload.get("order_id") != order_id or payload.get("invoice_sha256") != invoice_sha256:
            raise ApprovalError("approval order or invoice mismatch")
        if int(payload.get("amount_sats", -1)) != int(amount_sats):
            raise ApprovalError("approval amount mismatch")
        if payload.get("config_sha256") != config_sha256:
            raise ApprovalError("approval config hash mismatch")
        issued_at = int(payload.get("issued_at", 0))
        expires_at = int(payload.get("expires_at", 0))
        now = int(self.now())
        if issued_at > now + 30 or expires_at <= now or expires_at - issued_at > self.max_age_seconds:
            raise ApprovalError("approval is expired, future-dated, or valid for too long")
        try:
            public_key = base64.b64decode(operator["public_key_b64"], validate=True)
            signature = base64.b64decode(approval.signature_b64, validate=True)
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, canonical_json(payload))
        except (KeyError, ValueError, InvalidSignature) as exc:
            raise ApprovalError("invalid approval signature") from exc
        approval_id = str(payload.get("approval_id", ""))
        if not approval_id:
            raise ApprovalError("missing approval_id")
        payload_hash = approval_digest(payload)
        with self.db:
            existing = self.db.execute("SELECT payload_hash FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if existing and existing[0] != payload_hash:
                raise ApprovalError("approval_id reused with a different payload")
            if not existing:
                self.db.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?)", (approval_id, order_id, operator_id, payload_hash, expires_at, now))
        return str(operator_id)

    def require_two(self, *, order_id: str, invoice_sha256: str, amount_sats: int, config_sha256: str, approvals: list[Approval]) -> None:
        if len(approvals) < 2:
            raise ApprovalError("two approvals are required")
        operators: set[str] = set()
        for approval in approvals:
            operator_id = self._verify_one(approval, order_id=order_id, invoice_sha256=invoice_sha256, amount_sats=amount_sats, config_sha256=config_sha256)
            if operator_id in operators:
                raise ApprovalError("the same operator cannot approve twice")
            operators.add(operator_id)
        if len(operators) != 2:
            raise ApprovalError("approvals must come from two distinct operators")


__all__ = ["Approval", "ApprovalError", "ApprovalGate", "approval_digest", "canonical_json"]
