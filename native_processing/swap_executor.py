"""Executor seguro de intenções BTC/BAIT.

O executor não cria nem guarda chaves. Ele valida uma intenção assinada,
observa um depósito através de um leitor de Bitcoin Core, espera confirmações
e chama um adaptador BAIT idempotente. A liquidação continua desativada por
padrão.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Protocol

from .parity_gate import ParityAttestation, ParityError, ParityGate


class ExecutorError(ValueError):
    pass


class OrderState(str, Enum):
    PENDING = "pending"
    INTENT_VALIDATED = "intent_validated"
    BTC_OBSERVED = "btc_observed"
    BTC_CONFIRMED = "btc_confirmed"
    BAIT_SUBMITTED = "bait_submitted"
    SETTLED = "settled"
    RECONCILING = "reconciling"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class SwapIntent:
    """Compatibilidade para intents HMAC de testes legados.

    Intents de produção usam ``native_processing.swap_protocol.SwapIntent``
    com Ed25519 e são aceitos diretamente pelo executor.
    """

    order_id: str
    quote_id: str
    side: str
    btc_sats: int
    bait_units: int
    maker_id: str
    created_at: float
    expires_at: float
    nonce: str
    signature: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SwapIntent":
        try:
            intent = cls(
                order_id=str(value["order_id"]), quote_id=str(value["quote_id"]),
                side=str(value["side"]), btc_sats=int(value["btc_sats"]),
                bait_units=int(value["bait_units"]), maker_id=str(value["maker_id"]),
                created_at=float(value["created_at"]), expires_at=float(value["expires_at"]),
                nonce=str(value["nonce"]), signature=str(value["signature"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ExecutorError("malformed swap intent") from exc
        if not intent.order_id or not intent.quote_id or not intent.maker_id or not intent.nonce:
            raise ExecutorError("intent identifiers must be non-empty")
        if intent.side not in {"buy_bait", "sell_bait"}:
            raise ExecutorError("unsupported swap side")
        if type(intent.btc_sats) is not int or type(intent.bait_units) is not int:
            raise ExecutorError("intent amounts must be integers")
        if intent.btc_sats <= 0 or intent.bait_units <= 0:
            raise ExecutorError("amounts must be positive")
        if not math.isfinite(intent.created_at) or not math.isfinite(intent.expires_at) or intent.expires_at <= intent.created_at:
            raise ExecutorError("intent expiration must follow creation")
        return intent

    def canonical_payload(self) -> bytes:
        payload = {
            "order_id": self.order_id, "quote_id": self.quote_id, "side": self.side,
            "btc_sats": self.btc_sats, "bait_units": self.bait_units,
            "maker_id": self.maker_id, "created_at": self.created_at,
            "expires_at": self.expires_at, "nonce": self.nonce,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_payload()).hexdigest()


@dataclass(frozen=True)
class Deposit:
    txid: str
    btc_sats: int
    confirmations: int
    recipient: str = ""
    network: str = ""
    block_hash: str = ""
    vout: int = -1
    script_pubkey_hex: str = ""
    validated_hex: bool = False

    def validate(self, *, require_hex: bool = False) -> None:
        if not self.txid or len(self.txid) > 128:
            raise ExecutorError("invalid Bitcoin txid")
        if require_hex and not re.fullmatch(r"[0-9a-fA-F]{64}", self.txid):
            raise ExecutorError("Bitcoin txid must be exactly 32 bytes in HEX")
        if type(self.btc_sats) is not int or self.btc_sats <= 0:
            raise ExecutorError("invalid Bitcoin deposit amount")
        if type(self.confirmations) is not int or self.confirmations < 0:
            raise ExecutorError("invalid Bitcoin confirmations")
        if type(self.vout) is not int or self.vout < -1:
            raise ExecutorError("invalid Bitcoin output index")
        if require_hex:
            if self.vout < 0 or not self.validated_hex:
                raise ExecutorError("Bitcoin outpoint was not validated in HEX")
            if not self.script_pubkey_hex or len(self.script_pubkey_hex) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", self.script_pubkey_hex):
                raise ExecutorError("invalid Bitcoin scriptPubKey HEX")


class BitcoinReader(Protocol):
    def find_deposit(self, order_id: str, intent: Any) -> Optional[Deposit]: ...


class BaitSettlement(Protocol):
    def submit(self, intent: Any, deposit: Deposit) -> str: ...
    def status(self, external_id: str) -> str: ...


class SwapExecutor:
    """Máquina idempotente; ``enable_settlement=False`` é o padrão seguro."""

    def __init__(
        self,
        db_path: str,
        bitcoin: BitcoinReader,
        bait: BaitSettlement,
        verify_signature: Optional[Callable[[Any], bool]] = None,
        *,
        required_confirmations: int = 3,
        enable_settlement: bool = False,
        clock: Callable[[], float] = time.time,
        parity_gate: Optional[ParityGate] = None,
    ):
        if required_confirmations < 1:
            raise ExecutorError("required_confirmations must be positive")
        self.db = sqlite3.connect(db_path, timeout=30, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS orders ("
            "order_id TEXT PRIMARY KEY, intent_json TEXT NOT NULL, state TEXT NOT NULL, "
            "intent_digest TEXT NOT NULL, deposit_json TEXT, external_id TEXT, updated_at REAL NOT NULL, "
            "parity_digest TEXT NOT NULL DEFAULT '' )"
        )
        try:
            self.db.execute("ALTER TABLE orders ADD COLUMN parity_digest TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
        self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS orders_unique_btc_outpoint "
            "ON orders(json_extract(deposit_json, '$.network'), json_extract(deposit_json, '$.txid'), "
            "json_extract(deposit_json, '$.vout')) WHERE deposit_json IS NOT NULL"
        )
        self.bitcoin = bitcoin
        self.bait = bait
        self.verify_signature = verify_signature
        self.required_confirmations = required_confirmations
        self.enable_settlement = enable_settlement
        self.clock = clock
        self.parity_gate = parity_gate
        if self.enable_settlement and self.parity_gate is None:
            raise ExecutorError("settlement requires a verified BAIT/USDT parity gate")

    def close(self) -> None:
        self.db.close()

    @staticmethod
    def _intent_digest(intent: Any) -> str:
        if hasattr(intent, "signing_bytes") and hasattr(intent, "signature_b64"):
            raw = intent.signing_bytes() + str(intent.signature_b64).encode("ascii")
            return hashlib.sha256(raw).hexdigest()
        if hasattr(intent, "digest"):
            return str(intent.digest())
        return hashlib.sha256(intent.canonical_payload()).hexdigest()

    @staticmethod
    def _intent_dict(intent: Any) -> dict[str, Any]:
        if hasattr(intent, "to_dict"):
            return dict(intent.to_dict())
        return dict(intent.__dict__)

    @staticmethod
    def _from_stored_mapping(raw: Mapping[str, Any]) -> Any:
        if "signature_b64" in raw:
            from .swap_protocol import SwapIntent as SignedSwapIntent
            return SignedSwapIntent.from_dict(raw)
        return SwapIntent.from_mapping(raw)

    def admit(self, intent: Any) -> OrderState:
        try:
            if hasattr(intent, "verify") and hasattr(intent, "signature_b64"):
                intent.verify(now=self.clock())
            elif self.verify_signature is None or not self.verify_signature(intent):
                raise ExecutorError("invalid intent signature")
        except ExecutorError:
            raise
        except Exception as exc:
            raise ExecutorError("invalid intent signature") from exc
        parity_digest = ""
        if self.enable_settlement:
            try:
                raw_parity = json.loads(str(getattr(intent, "parity_attestation_json", "")))
                parity = ParityAttestation.from_mapping(raw_parity)
                parity_digest = self.parity_gate.validate(parity, now=self.clock())  # type: ignore[union-attr]
            except (ParityError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ExecutorError("intent has no valid BAIT/USDT parity attestation") from exc
        if self.clock() >= float(intent.expires_at):
            raise ExecutorError("expired intent")
        encoded = json.dumps(self._intent_dict(intent), sort_keys=True, separators=(",", ":"), allow_nan=False)
        digest = self._intent_digest(intent)
        row = self.db.execute("SELECT intent_digest,state FROM orders WHERE order_id=?", (intent.order_id,)).fetchone()
        if row:
            if row[0] != digest:
                raise ExecutorError("order_id conflict: payload changed")
            return OrderState(row[1])
        self.db.execute(
            "INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)",
            (intent.order_id, encoded, OrderState.INTENT_VALIDATED.value, digest, None, None, self.clock(), parity_digest),
        )
        return OrderState.INTENT_VALIDATED

    def _get(self, order_id: str) -> tuple:
        row = self.db.execute(
            "SELECT intent_json,state,intent_digest,deposit_json,external_id FROM orders WHERE order_id=?",
            (order_id,),
        ).fetchone()
        if not row:
            raise ExecutorError("unknown order")
        return row

    def process(self, order_id: str) -> OrderState:
        encoded, state_value, _, prior_deposit_json, external_id = self._get(order_id)
        intent = self._from_stored_mapping(json.loads(encoded))
        state = OrderState(state_value)
        if state in {OrderState.SETTLED, OrderState.REFUNDED, OrderState.RECONCILING}:
            return state

        deposit = self.bitcoin.find_deposit(order_id, intent)
        if deposit is None:
            return state
        try:
            deposit.validate(require_hex=self.enable_settlement)
        except ExecutorError:
            self.db.execute(
                "UPDATE orders SET state=?,updated_at=? WHERE order_id=?",
                (OrderState.RECONCILING.value, self.clock(), order_id),
            )
            return OrderState.RECONCILING

        if prior_deposit_json:
            prior = json.loads(prior_deposit_json)
            if prior.get("txid") != deposit.txid or (
                prior.get("vout", -1) >= 0 and prior.get("vout") != deposit.vout
            ):
                self._set_state(order_id, OrderState.RECONCILING, deposit)
                return OrderState.RECONCILING
        expected_network = getattr(intent, "network", "")
        if expected_network and deposit.network and expected_network != deposit.network:
            self._set_state(order_id, OrderState.RECONCILING, deposit)
            return OrderState.RECONCILING
        expected_recipient = getattr(intent, "btc_deposit_address", "")
        if expected_recipient and deposit.recipient and expected_recipient != deposit.recipient:
            self._set_state(order_id, OrderState.RECONCILING, deposit)
            return OrderState.RECONCILING
        if deposit.btc_sats != int(intent.btc_sats):
            self._set_state(order_id, OrderState.RECONCILING, deposit)
            return OrderState.RECONCILING

        if state == OrderState.INTENT_VALIDATED:
            if not self._set_state(order_id, OrderState.BTC_OBSERVED, deposit):
                return OrderState.RECONCILING
            state = OrderState.BTC_OBSERVED
        if deposit.confirmations < self.required_confirmations:
            return state
        if state == OrderState.BTC_OBSERVED:
            self._set_state(order_id, OrderState.BTC_CONFIRMED, deposit)
            state = OrderState.BTC_CONFIRMED
        if state == OrderState.BTC_CONFIRMED:
            if not self.enable_settlement:
                return state
            # The BAIT adapter must make submit(order_id) idempotent. The
            # executor persists its returned id before polling status.
            external_id = self.bait.submit(intent, deposit)
            if not isinstance(external_id, str) or not external_id:
                raise ExecutorError("BAIT settlement returned an invalid external id")
            self.db.execute(
                "UPDATE orders SET state=?,external_id=?,deposit_json=?,updated_at=? WHERE order_id=?",
                (OrderState.BAIT_SUBMITTED.value, external_id, json.dumps(deposit.__dict__, sort_keys=True), self.clock(), order_id),
            )
            state = OrderState.BAIT_SUBMITTED
        if state == OrderState.BAIT_SUBMITTED and external_id:
            status = self.bait.status(external_id)
            if status == "confirmed":
                self.db.execute(
                    "UPDATE orders SET state=?,updated_at=? WHERE order_id=?",
                    (OrderState.SETTLED.value, self.clock(), order_id),
                )
                return OrderState.SETTLED
            if status in {"failed", "rejected", "unknown"}:
                self.db.execute(
                    "UPDATE orders SET state=?,updated_at=? WHERE order_id=?",
                    (OrderState.RECONCILING.value, self.clock(), order_id),
                )
                return OrderState.RECONCILING
        return state

    def _set_state(self, order_id: str, state: OrderState, deposit: Deposit) -> bool:
        try:
            self.db.execute(
                "UPDATE orders SET state=?,deposit_json=?,updated_at=? WHERE order_id=?",
                (state.value, json.dumps(deposit.__dict__, sort_keys=True), self.clock(), order_id),
            )
            return True
        except sqlite3.IntegrityError:
            self.db.execute(
                "UPDATE orders SET state=?,updated_at=? WHERE order_id=?",
                (OrderState.RECONCILING.value, self.clock(), order_id),
            )
            return False

    def get_state(self, order_id: str) -> OrderState:
        return OrderState(self._get(order_id)[1])

    def get_order(self, order_id: str) -> Optional[dict[str, Any]]:
        row = self.db.execute(
            "SELECT order_id,state,intent_json,deposit_json,external_id,updated_at FROM orders WHERE order_id=?",
            (order_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "order_id": row[0], "state": row[1], "intent": json.loads(row[2]),
            "deposit": json.loads(row[3]) if row[3] else None,
            "external_id": row[4], "updated_at": row[5],
        }


def hmac_verifier(secret: bytes) -> Callable[[SwapIntent], bool]:
    """Verificador de compatibilidade para ambiente controlado; não é custódia."""
    def verify(intent: SwapIntent) -> bool:
        expected = hmac.new(secret, intent.canonical_payload(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, intent.signature)
    return verify
