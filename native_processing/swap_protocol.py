"""Protocolo de intenção de swap para propagação entre nós nativos.

A intenção é uma mensagem imutável e assinada pelo participante. Qualquer nó
pode validar a mensagem sem confiar em um coordenador central. Este protocolo
não executa custódia nem confirma uma transação Bitcoin/BAIT por si só.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .swap_engine import SwapError, SwapQuote


class IntentError(SwapError):
    pass


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _decode_b64(value: str, label: str) -> bytes:
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
    except Exception as exc:
        raise IntentError(f"invalid {label}") from exc
    return raw


@dataclass(frozen=True)
class SwapIntent:
    order_id: str
    quote_id: str
    side: str
    btc_sats: int
    bait_units: int
    maker_id: str
    created_at: float
    expires_at: float
    nonce: str
    public_key_b64: str
    signature_b64: str

    def unsigned_dict(self) -> dict[str, Any]:
        return {"version": 1, "order_id": self.order_id, "quote_id": self.quote_id, "side": self.side,
                "btc_sats": self.btc_sats, "bait_units": self.bait_units, "maker_id": self.maker_id,
                "created_at": self.created_at, "expires_at": self.expires_at, "nonce": self.nonce,
                "public_key_b64": self.public_key_b64}

    def signing_bytes(self) -> bytes:
        return b"bait.swap.intent.v1\n" + _canonical(self.unsigned_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "signature_b64": self.signature_b64}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SwapIntent":
        required = ("order_id", "quote_id", "side", "btc_sats", "bait_units", "maker_id", "created_at", "expires_at", "nonce", "public_key_b64", "signature_b64")
        if not isinstance(raw, Mapping) or any(k not in raw for k in required):
            raise IntentError("invalid swap intent envelope")
        try:
            return cls(order_id=str(raw["order_id"]), quote_id=str(raw["quote_id"]), side=str(raw["side"]),
                       btc_sats=int(raw["btc_sats"]), bait_units=int(raw["bait_units"]), maker_id=str(raw["maker_id"]),
                       created_at=float(raw["created_at"]), expires_at=float(raw["expires_at"]), nonce=str(raw["nonce"]),
                       public_key_b64=str(raw["public_key_b64"]), signature_b64=str(raw["signature_b64"]))
        except (TypeError, ValueError) as exc:
            raise IntentError("invalid swap intent field type") from exc

    def verify(self, now: Optional[float] = None, max_skew_seconds: int = 300) -> bool:
        now = time.time() if now is None else float(now)
        if self.side not in {"buy_bait", "sell_bait"} or self.btc_sats <= 0 or self.bait_units <= 0:
            raise IntentError("invalid swap intent amounts")
        if not self.maker_id or not self.nonce or self.expires_at <= self.created_at:
            raise IntentError("invalid swap intent lifetime")
        if self.created_at > now + max_skew_seconds or self.expires_at < now - max_skew_seconds:
            raise IntentError("swap intent expired or from the future")
        public_key = _decode_b64(self.public_key_b64, "public key")
        signature = _decode_b64(self.signature_b64, "signature")
        if len(public_key) != 32 or len(signature) != 64:
            raise IntentError("invalid Ed25519 key or signature length")
        expected = hashlib.sha256(f"{self.quote_id}:{self.nonce}:{self.maker_id}".encode()).hexdigest()
        if not hmac_compare(self.order_id, expected):
            raise IntentError("order_id does not match intent")
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, self.signing_bytes())
        except (InvalidSignature, ValueError) as exc:
            raise IntentError("invalid swap intent signature") from exc
        return True


def hmac_compare(left: str, right: str) -> bool:
    # comparação constante para identificadores derivados
    import hmac
    return hmac.compare_digest(left.encode(), right.encode())


def sign_quote(quote: SwapQuote, maker_id: str, private_key: Ed25519PrivateKey, client_order_id: str, now: Optional[float] = None) -> SwapIntent:
    if not maker_id or not client_order_id:
        raise IntentError("maker_id and client_order_id are required")
    now = time.time() if now is None else float(now)
    if quote.expires_at <= now:
        raise IntentError("quote expired")
    public_key_b64 = base64.b64encode(private_key.public_key().public_bytes_raw()).decode()
    nonce = hashlib.sha256(f"{maker_id}:{client_order_id}:{quote.quote_id}".encode()).hexdigest()[:32]
    order_id = hashlib.sha256(f"{quote.quote_id}:{nonce}:{maker_id}".encode()).hexdigest()
    unsigned = SwapIntent(order_id, quote.quote_id, quote.side, quote.btc_sats, quote.bait_units, maker_id,
                          now, quote.expires_at, nonce, public_key_b64, "")
    signature_b64 = base64.b64encode(private_key.sign(unsigned.signing_bytes())).decode()
    return SwapIntent(**{**unsigned.__dict__, "signature_b64": signature_b64})
