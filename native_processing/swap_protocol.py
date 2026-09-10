"""Protocolo de intenção de swap para propagação entre nós nativos.

A intenção é uma mensagem imutável e assinada pelo participante. Qualquer nó
pode validar a mensagem sem confiar em um coordenador central. O protocolo
carrega apenas roteamento público: endereço de depósito BTC, rede explícita e
chave pública do destinatário BAIT. Chaves privadas continuam fora da
mensagem e fora desta camada.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .swap_engine import SwapError, SwapQuote


class IntentError(SwapError):
    pass


SUPPORTED_NETWORKS = {"mainnet", "testnet", "regtest", "signet"}


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


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
    client_order_id: str = ""
    btc_deposit_address: str = ""
    bait_recipient_pubkey_b64: str = ""
    network: str = ""
    parity_attestation_json: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "order_id": self.order_id,
            "quote_id": self.quote_id,
            "side": self.side,
            "btc_sats": self.btc_sats,
            "bait_units": self.bait_units,
            "maker_id": self.maker_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "public_key_b64": self.public_key_b64,
            "client_order_id": self.client_order_id,
            "btc_deposit_address": self.btc_deposit_address,
            "bait_recipient_pubkey_b64": self.bait_recipient_pubkey_b64,
            "network": self.network,
            "parity_attestation_json": self.parity_attestation_json,
        }

    def signing_bytes(self) -> bytes:
        return b"bait.swap.intent.v1\n" + _canonical(self.unsigned_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "signature_b64": self.signature_b64}

    def digest(self) -> str:
        """Identidade criptográfica estável da intenção completa."""
        return hashlib.sha256(
            self.signing_bytes() + self.signature_b64.encode("ascii")
        ).hexdigest()

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SwapIntent":
        required = (
            "order_id", "quote_id", "side", "btc_sats", "bait_units",
            "maker_id", "created_at", "expires_at", "nonce", "public_key_b64",
            "signature_b64",
        )
        if not isinstance(raw, Mapping) or any(k not in raw for k in required):
            raise IntentError("invalid swap intent envelope")
        if raw.get("version") != 1:
            raise IntentError("unsupported swap intent version")
        try:
            return cls(
                order_id=str(raw["order_id"]),
                quote_id=str(raw["quote_id"]),
                side=str(raw["side"]),
                btc_sats=int(raw["btc_sats"]),
                bait_units=int(raw["bait_units"]),
                maker_id=str(raw["maker_id"]),
                created_at=float(raw["created_at"]),
                expires_at=float(raw["expires_at"]),
                nonce=str(raw["nonce"]),
                public_key_b64=str(raw["public_key_b64"]),
                signature_b64=str(raw["signature_b64"]),
                client_order_id=str(raw.get("client_order_id", "")),
                btc_deposit_address=str(raw.get("btc_deposit_address", "")),
                bait_recipient_pubkey_b64=str(raw.get("bait_recipient_pubkey_b64", "")),
                network=str(raw.get("network", "")),
                parity_attestation_json=str(raw.get("parity_attestation_json", "")),
            )
        except (TypeError, ValueError) as exc:
            raise IntentError("invalid swap intent field type") from exc

    def verify(self, now: Optional[float] = None, max_skew_seconds: int = 300) -> bool:
        now = time.time() if now is None else float(now)
        if not math.isfinite(now) or max_skew_seconds < 0:
            raise IntentError("invalid verification clock")
        if self.side not in {"buy_bait", "sell_bait"} or self.btc_sats <= 0 or self.bait_units <= 0:
            raise IntentError("invalid swap intent amounts")
        if not self.order_id or not self.quote_id or not self.maker_id or not self.nonce:
            raise IntentError("invalid swap intent identifiers")
        if self.expires_at <= self.created_at or not math.isfinite(self.created_at) or not math.isfinite(self.expires_at):
            raise IntentError("invalid swap intent lifetime")
        if self.created_at > now + max_skew_seconds or self.expires_at < now - max_skew_seconds:
            raise IntentError("swap intent expired or from the future")
        if self.network and self.network not in SUPPORTED_NETWORKS:
            raise IntentError("unsupported swap network")
        if self.parity_attestation_json:
            try:
                parsed_parity = json.loads(self.parity_attestation_json)
            except (TypeError, ValueError) as exc:
                raise IntentError("invalid parity attestation encoding") from exc
            if not isinstance(parsed_parity, Mapping):
                raise IntentError("invalid parity attestation envelope")

        public_key = _decode_b64(self.public_key_b64, "public key")
        signature = _decode_b64(self.signature_b64, "signature")
        if len(public_key) != 32 or len(signature) != 64:
            raise IntentError("invalid Ed25519 key or signature length")
        if self.bait_recipient_pubkey_b64:
            recipient_key = _decode_b64(self.bait_recipient_pubkey_b64, "BAIT recipient public key")
            if len(recipient_key) != 32:
                raise IntentError("invalid BAIT recipient public key length")

        if self.client_order_id:
            expected = hashlib.sha256(f"{self.quote_id}:{self.client_order_id}".encode()).hexdigest()
        else:
            # Backward-compatible validation for pre-routing intents.
            expected = hashlib.sha256(f"{self.quote_id}:{self.nonce}:{self.maker_id}".encode()).hexdigest()
        if not hmac.compare_digest(self.order_id.encode(), expected.encode()):
            raise IntentError("order_id does not match intent")
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, self.signing_bytes())
        except (InvalidSignature, ValueError) as exc:
            raise IntentError("invalid swap intent signature") from exc
        return True


def sign_quote(
    quote: SwapQuote,
    maker_id: str,
    private_key: Ed25519PrivateKey,
    client_order_id: str,
    now: Optional[float] = None,
    *,
    btc_deposit_address: str = "",
    bait_recipient_pubkey: bytes | str = b"",
    network: str = "",
    parity_attestation: Optional[Mapping[str, Any]] = None,
) -> SwapIntent:
    """Assina uma cotação e, opcionalmente, seu roteamento de liquidação.

    ``bait_recipient_pubkey`` aceita os 32 bytes da chave pública BAIT ou uma
    string Base64. O campo nunca contém material privado.
    """
    if not maker_id or not client_order_id:
        raise IntentError("maker_id and client_order_id are required")
    if network and network not in SUPPORTED_NETWORKS:
        raise IntentError("unsupported swap network")
    parity_json = ""
    if parity_attestation is not None:
        try:
            parity_json = json.dumps(dict(parity_attestation), sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise IntentError("invalid parity attestation") from exc
    now = time.time() if now is None else float(now)
    if not math.isfinite(now) or quote.expires_at <= now:
        raise IntentError("quote expired or invalid signing time")

    if isinstance(bait_recipient_pubkey, bytes):
        recipient_b64 = base64.b64encode(bait_recipient_pubkey).decode() if bait_recipient_pubkey else ""
    else:
        recipient_b64 = bait_recipient_pubkey
    if recipient_b64:
        recipient_raw = _decode_b64(recipient_b64, "BAIT recipient public key")
        if len(recipient_raw) != 32:
            raise IntentError("invalid BAIT recipient public key length")

    public_key_b64 = base64.b64encode(private_key.public_key().public_bytes_raw()).decode()
    nonce = hashlib.sha256(f"{maker_id}:{client_order_id}:{quote.quote_id}".encode()).hexdigest()[:32]
    # Keep the intent identity equal to SwapEngine.place_order().
    order_id = hashlib.sha256(f"{quote.quote_id}:{client_order_id}".encode()).hexdigest()
    unsigned = SwapIntent(
        order_id=order_id,
        quote_id=quote.quote_id,
        side=quote.side,
        btc_sats=quote.btc_sats,
        bait_units=quote.bait_units,
        maker_id=maker_id,
        created_at=now,
        expires_at=quote.expires_at,
        nonce=nonce,
        public_key_b64=public_key_b64,
        signature_b64="",
        client_order_id=client_order_id,
        btc_deposit_address=btc_deposit_address,
        bait_recipient_pubkey_b64=recipient_b64,
        network=network,
        parity_attestation_json=parity_json,
    )
    signature_b64 = base64.b64encode(private_key.sign(unsigned.signing_bytes())).decode()
    return SwapIntent(**{**unsigned.__dict__, "signature_b64": signature_b64})
