#!/usr/bin/env python3
"""Fail-closed LND Mainnet settlement adapter.

This module is an explicit live adapter, separate from the dry-run executor. It
requires dependency-injected generated LND stubs and an external macaroon
loader. It never reads seeds/private keys and never stores a macaroon in YAML.

Required generated modules (generated from LND's lightning.proto and
routerrpc/router.proto): ``lnrpc.rpc_pb2``, ``lnrpc.rpc_pb2_grpc``,
``routerrpc.router_pb2`` and ``routerrpc.router_pb2_grpc``.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Protocol

try:
    from .approval_gate import ApprovalError
    from .macaroon_provider import MacaroonProvider, MacaroonProviderError
except ImportError:  # direct script/module execution
    from approval_gate import ApprovalError  # type: ignore
    from macaroon_provider import MacaroonProvider, MacaroonProviderError  # type: ignore

try:
    import grpc
except ImportError:  # pragma: no cover
    grpc = None  # type: ignore[assignment]


class MainnetAdapterError(RuntimeError):
    """A fail-closed operational or validation error."""


class SettlementPaused(MainnetAdapterError):
    pass


class LightningStub(Protocol):
    def GetInfo(self, request: Any, timeout: float | None = None) -> Any: ...
    def DecodePayReq(self, request: Any, timeout: float | None = None) -> Any: ...


class RouterStub(Protocol):
    def SendPaymentV2(self, request: Any, timeout: float | None = None) -> Iterable[Any]: ...


@dataclass(frozen=True)
class SettlementReceipt:
    order_id: str
    external_payment_hash: str
    status: str
    fee_msat: int
    settled_at: float
    network: str


@dataclass(frozen=True)
class LndAdapterConfig:
    host: str
    port: int
    ca_cert_path: str
    tls_server_name: str
    macaroon_scope: str
    max_order_sats: int
    daily_limit_sats: int
    max_fee_msat: int
    authorization_reference: str
    manual_unlock: bool
    two_person_approval: bool
    timeout_seconds: int = 60
    required_network: str = "mainnet"


class MainnetSettlementAdapter:
    """LND payment adapter with local idempotency, limits and pause control.

    The adapter only settles an order containing a BOLT11 ``payment_request``.
    On-chain locking and ISP/BAIT confirmation must be completed by the caller
    before ``settle`` is called and represented by the order's state fields.
    """

    def __init__(
        self,
        config: LndAdapterConfig,
        lightning_stub: LightningStub,
        router_stub: RouterStub,
        state_db: str | Path,
        *,
        lightning_message_module: Any,
        router_message_module: Any,
        approval_gate: Any,
        approvals_loader: Callable[[str], list[Any]],
        config_sha256: str,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.config = config
        self.lightning = lightning_stub
        self.router = router_stub
        self.lightning_message_module = lightning_message_module
        self.router_message_module = router_message_module
        self.approval_gate = approval_gate
        self.approvals_loader = approvals_loader
        self.config_sha256 = config_sha256
        self.now = now
        if config.required_network != "mainnet":
            raise MainnetAdapterError("MainnetSettlementAdapter requires required_network=mainnet")
        if not 1 <= int(config.port) <= 65535:
            raise MainnetAdapterError("invalid LND gRPC port")
        if min(config.max_order_sats, config.daily_limit_sats, config.max_fee_msat) <= 0:
            raise MainnetAdapterError("live settlement limits must be positive")
        scope = {item.strip() for item in config.macaroon_scope.split(",") if item.strip()}
        forbidden = {"admin", "invoice:write", "wallet:write", "channel:write", "onchain:write"}
        if "send_payment" not in scope or scope & forbidden:
            raise MainnetAdapterError("macaroon scope must be limited to send_payment and read-only capabilities")
        if not config.authorization_reference or not config.manual_unlock or not config.two_person_approval:
            raise MainnetAdapterError("live settlement requires authorization reference, manual unlock and two-person approval")
        if approval_gate is None or not callable(approvals_loader) or len(config_sha256) != 64:
            raise MainnetAdapterError("ApprovalGate, approvals_loader and a SHA-256 config hash are required")
        self._lock = threading.RLock()
        self.db = sqlite3.connect(str(state_db), check_same_thread=False, timeout=30.0)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS adapter_control (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            self.db.execute("""CREATE TABLE IF NOT EXISTS settlements (
                order_id TEXT PRIMARY KEY,
                request_hash TEXT NOT NULL,
                payment_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                btc_sats INTEGER NOT NULL,
                fee_msat INTEGER NOT NULL,
                settled_at REAL,
                network TEXT NOT NULL
            )""")
            self.db.execute("CREATE INDEX IF NOT EXISTS settlements_day ON settlements(status, settled_at)")

    def close(self) -> None:
        with self._lock:
            self.db.close()

    def pause(self) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT INTO adapter_control(key,value) VALUES('paused','true') ON CONFLICT(key) DO UPDATE SET value='true'")

    def resume(self) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT INTO adapter_control(key,value) VALUES('paused','false') ON CONFLICT(key) DO UPDATE SET value='false'")

    def _ensure_not_paused(self) -> None:
        row = self.db.execute("SELECT value FROM adapter_control WHERE key='paused'").fetchone()
        if row and row[0] == "true":
            raise SettlementPaused("settlement adapter is paused")

    @staticmethod
    def _enum_name(value: Any) -> str:
        if isinstance(value, str):
            return value.upper()
        if isinstance(value, int):
            return {0: "UNKNOWN", 1: "IN_FLIGHT", 2: "SUCCEEDED", 3: "FAILED"}.get(value, str(value))
        descriptor = getattr(value, "DESCRIPTOR", None)
        if descriptor is not None:
            return getattr(descriptor, "name", str(value)).upper()
        return str(value).upper()

    @staticmethod
    def _field(obj: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            if hasattr(obj, name):
                return getattr(obj, name)
        return default

    def _assert_mainnet_node(self) -> str:
        try:
            info = self.lightning.GetInfo(self.lightning_message_module.GetInfoRequest(), timeout=10)
        except Exception as exc:
            raise MainnetAdapterError("LND GetInfo preflight failed") from exc
        chains = self._field(info, "chains", default=[])
        networks = {str(self._field(item, "network", default="")).lower() for item in chains}
        if self.config.required_network not in networks:
            raise MainnetAdapterError("connected LND node is not on the required network")
        return self.config.required_network

    def preflight(self, order: dict[str, Any]) -> None:
        self._ensure_not_paused()
        required = ("order_id", "payment_request", "btc_sats", "state", "counterparty_allowlisted")
        missing = [key for key in required if key not in order]
        if missing:
            raise MainnetAdapterError(f"order missing required fields: {','.join(missing)}")
        if order["state"] != "bait_confirmed":
            raise MainnetAdapterError("settlement requires state=bait_confirmed")
        if order["counterparty_allowlisted"] is not True:
            raise MainnetAdapterError("counterparty is not allowlisted")
        sats = int(order["btc_sats"])
        if sats <= 0 or sats > self.config.max_order_sats:
            raise MainnetAdapterError("order exceeds configured settlement limit")
        if not isinstance(order["payment_request"], str) or not order["payment_request"].lower().startswith("lnbc"):
            raise MainnetAdapterError("only a Bitcoin mainnet BOLT11 invoice is accepted")
        network = self._assert_mainnet_node()
        try:
            decoded = self.lightning.DecodePayReq(self.lightning_message_module.PayReqString(pay_req=order["payment_request"]), timeout=10)
        except Exception as exc:
            raise MainnetAdapterError("LND DecodePayReq failed") from exc
        invoice_network = str(self._field(decoded, "network", default="")).lower()
        if invoice_network and invoice_network != network:
            raise MainnetAdapterError("invoice network does not match LND network")
        invoice_sats = int(self._field(decoded, "num_satoshis", "value", default=0) or 0)
        if invoice_sats != sats:
            raise MainnetAdapterError("invoice amount does not exactly match order amount")
        expiry = int(self._field(decoded, "timestamp", default=0) or 0) + int(self._field(decoded, "expiry", default=0) or 0)
        if expiry and expiry <= int(self.now()):
            raise MainnetAdapterError("invoice is expired")

    def _daily_total(self) -> int:
        start = self.now() - 86400
        row = self.db.execute("SELECT COALESCE(SUM(btc_sats),0) FROM settlements WHERE status='SUCCEEDED' AND settled_at>=?", (start,)).fetchone()
        return int(row[0] or 0)

    def settle(self, order: dict[str, Any]) -> SettlementReceipt:
        """Execute one real payment after all caller-side state checks.

        This is the only method that invokes SendPaymentV2. The caller must use
        a restricted macaroon and an external signer/custodian; this method does
        not sign on-chain transactions.
        """
        if "order_id" not in order or "payment_request" not in order:
            raise MainnetAdapterError("order_id and payment_request are required")
        order_id = str(order["order_id"])
        request = str(order["payment_request"])
        request_hash = hashlib.sha256(request.encode("utf-8")).hexdigest()
        with self._lock:
            prior = self.db.execute("SELECT payment_hash,status,fee_msat,settled_at,network FROM settlements WHERE order_id=? AND request_hash=?", (order_id, request_hash)).fetchone()
            if prior:
                return SettlementReceipt(order_id, prior[0], prior[1], int(prior[2]), float(prior[3] or 0), prior[4])
            self.preflight(order)
            if self._daily_total() + int(order["btc_sats"]) > self.config.daily_limit_sats:
                raise MainnetAdapterError("configured daily settlement limit reached")
            try:
                self.approval_gate.require_two(
                    order_id=order_id,
                    invoice_sha256=request_hash,
                    amount_sats=int(order["btc_sats"]),
                    config_sha256=self.config_sha256,
                    approvals=self.approvals_loader(order_id),
                )
            except (ApprovalError, KeyError, TypeError, ValueError) as exc:
                raise MainnetAdapterError("two-person approval rejected") from exc
            try:
                stream = self.router.SendPaymentV2(
                    self.router_message_module.SendPaymentRequest(payment_request=request, timeout_seconds=self.config.timeout_seconds, fee_limit_msat=self.config.max_fee_msat, no_inflight_updates=True),
                    timeout=self.config.timeout_seconds + 5,
                )
                final = None
                for update in stream:
                    final = update
                    status = self._enum_name(self._field(update, "status", default=""))
                    if status in {"SUCCEEDED", "FAILED"}:
                        break
            except Exception as exc:
                raise MainnetAdapterError("LND SendPaymentV2 failed before a terminal receipt") from exc
            if final is None:
                raise MainnetAdapterError("LND returned no payment update")
            status = self._enum_name(self._field(final, "status", default=""))
            payment_hash = str(self._field(final, "payment_hash", default=""))
            fee_msat = int(self._field(final, "fee_msat", "fee", default=0) or 0)
            if status != "SUCCEEDED":
                with self.db:
                    self.db.execute("INSERT OR REPLACE INTO settlements VALUES(?,?,?,?,?,?,?,?)", (order_id, request_hash, payment_hash or "unknown", status, int(order["btc_sats"]), fee_msat, None, self.config.required_network))
                raise MainnetAdapterError(f"LND payment did not succeed: {status}")
            if fee_msat > self.config.max_fee_msat:
                raise MainnetAdapterError("successful payment exceeded configured fee limit")
            settled_at = self.now()
            with self.db:
                self.db.execute("INSERT INTO settlements VALUES(?,?,?,?,?,?,?,?)", (order_id, request_hash, payment_hash, status, int(order["btc_sats"]), fee_msat, settled_at, self.config.required_network))
            return SettlementReceipt(order_id, payment_hash, status, fee_msat, settled_at, self.config.required_network)

    def reconcile(self, order_id: str) -> Optional[SettlementReceipt]:
        row = self.db.execute("SELECT payment_hash,status,fee_msat,settled_at,network FROM settlements WHERE order_id=?", (order_id,)).fetchone()
        if not row:
            return None
        return SettlementReceipt(order_id, row[0], row[1], int(row[2]), float(row[3] or 0), row[4])


def _empty_request(stub: Any) -> Any:
    module = getattr(stub, "request_module", None)
    if module is not None:
        return module.GetInfoRequest()
    return _message_from_stub(stub, "GetInfoRequest")


def _payreq_request(stub: Any, payment_request: str) -> Any:
    cls = _message_from_stub(stub, "PayReqString")
    return cls(pay_req=payment_request)


def _send_request(stub: Any, payment_request: str, timeout_seconds: int, max_fee_msat: int) -> Any:
    cls = _message_from_stub(stub, "SendPaymentRequest")
    return cls(payment_request=payment_request, timeout_seconds=timeout_seconds, fee_limit_msat=max_fee_msat, no_inflight_updates=True)


def _message_from_stub(stub: Any, name: str) -> Any:
    module = getattr(stub, "message_module", None)
    if module is None:
        raise MainnetAdapterError(f"generated protobuf message module is required for {name}")
    cls = getattr(module, name, None)
    if cls is None:
        raise MainnetAdapterError(f"protobuf message {name} is unavailable")
    return cls()


def create_secure_lnd_channel(host: str, port: int, ca_cert_path: str, tls_server_name: str, macaroon_provider: MacaroonProvider):
    """Create TLS + macaroon gRPC channel; caller supplies generated stubs.

    ``macaroon_provider`` must obtain a short-lived, least-privilege macaroon
    from an external secret manager or a tightly permissioned mounted file. Its
    bytes are never placed in this config file.
    """
    if grpc is None:
        raise MainnetAdapterError("grpcio is required to connect to LND")
    if not 1 <= int(port) <= 65535:
        raise MainnetAdapterError("invalid gRPC port")
    ca = Path(ca_cert_path).read_bytes()
    if not ca:
        raise MainnetAdapterError("empty TLS CA certificate")
    try:
        macaroon = macaroon_provider.load()
    except MacaroonProviderError as exc:
        raise MainnetAdapterError("unable to load macaroon securely") from exc
    ssl_options = (("grpc.ssl_target_name_override", tls_server_name),)
    ssl_credentials = grpc.ssl_channel_credentials(root_certificates=ca)
    call_credentials = grpc.metadata_call_credentials(lambda context, callback: callback((("macaroon", macaroon.hex()),), None))
    credentials = grpc.composite_channel_credentials(ssl_credentials, call_credentials)
    return grpc.secure_channel(f"{host}:{int(port)}", credentials, options=ssl_options)


def build_lnd_stubs(channel: Any, lightning_stub_factory: Callable[[Any], LightningStub], router_stub_factory: Callable[[Any], RouterStub]) -> tuple[LightningStub, RouterStub]:
    """Build generated ``LightningStub`` and ``RouterStub`` instances."""
    if channel is None or not callable(lightning_stub_factory) or not callable(router_stub_factory):
        raise MainnetAdapterError("channel and generated stub factories are required")
    return lightning_stub_factory(channel), router_stub_factory(channel)


__all__ = ["LndAdapterConfig", "MainnetSettlementAdapter", "MainnetAdapterError", "SettlementPaused", "SettlementReceipt", "create_secure_lnd_channel", "build_lnd_stubs"]
