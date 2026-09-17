"""Motor determinístico de cotação e ordens BTC/BAIT.

Este componente não movimenta fundos nem altera o ledger existente. Ele produz
ordens de intenção idempotentes para que um executor/bridge já existente faça a
liquidação após as confirmações necessárias.
"""
from __future__ import annotations

import hashlib
import hmac
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional


class SwapError(ValueError):
    pass


SATOSHI = Decimal("0.00000001")


def _units(value: Decimal, asset: str) -> int:
    if value <= 0:
        raise SwapError(f"{asset} amount must be positive")
    return int((value / SATOSHI).to_integral_value(rounding=ROUND_DOWN))


@dataclass(frozen=True)
class SwapQuote:
    quote_id: str
    side: str
    btc_sats: int
    bait_units: int
    fee_bps: int
    expires_at: float

    def to_dict(self) -> dict:
        return {"quote_id": self.quote_id, "side": self.side, "btc_sats": self.btc_sats,
                "bait_units": self.bait_units, "fee_bps": self.fee_bps, "expires_at": self.expires_at}


@dataclass(frozen=True)
class SwapOrder:
    order_id: str
    quote_id: str
    client_order_id: str
    status: str
    created_at: float

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class SwapEngine:
    """Quote/order state machine using integer base units and SQLite durability."""

    def __init__(self, db_path: str, fee_bps: int = 30, quote_ttl_seconds: int = 30):
        if not 0 <= fee_bps <= 10_000 or quote_ttl_seconds <= 0:
            raise ValueError("invalid swap parameters")
        self.fee_bps = fee_bps
        self.quote_ttl_seconds = quote_ttl_seconds
        self.db = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self._lock = threading.RLock()
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS swap_orders (order_id TEXT PRIMARY KEY, quote_id TEXT NOT NULL, client_order_id TEXT UNIQUE NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL)")

    def close(self) -> None:
        with self._lock:
            self.db.close()

    def quote(self, side: str, btc_sats: int, bait_units: int, now: Optional[float] = None) -> SwapQuote:
        if side not in {"buy_bait", "sell_bait"}:
            raise SwapError("side must be buy_bait or sell_bait")
        if not isinstance(btc_sats, int) or not isinstance(bait_units, int) or btc_sats <= 0 or bait_units <= 0:
            raise SwapError("amounts must be positive integers")
        now = time.time() if now is None else float(now)
        return SwapQuote(uuid.uuid4().hex, side, btc_sats, bait_units, self.fee_bps, now + self.quote_ttl_seconds)

    def place_order(self, quote: SwapQuote, client_order_id: str, now: Optional[float] = None) -> SwapOrder:
        now = time.time() if now is None else float(now)
        if quote.expires_at <= now:
            raise SwapError("quote expired")
        if not client_order_id or len(client_order_id) > 128:
            raise SwapError("invalid client_order_id")
        order_id = hashlib.sha256(f"{quote.quote_id}:{client_order_id}".encode()).hexdigest()
        with self._lock, self.db:
            existing = self.db.execute("SELECT order_id,quote_id,status,created_at FROM swap_orders WHERE client_order_id=?", (client_order_id,)).fetchone()
            if existing:
                if existing[1] != quote.quote_id:
                    raise SwapError("client_order_id already used with another quote")
                return SwapOrder(existing[0], existing[1], client_order_id, existing[2], existing[3])
            self.db.execute("INSERT INTO swap_orders VALUES(?,?,?,?,?)", (order_id, quote.quote_id, client_order_id, "pending", now))
        return SwapOrder(order_id, quote.quote_id, client_order_id, "pending", now)

    def get_order(self, client_order_id: str) -> Optional[SwapOrder]:
        row = self.db.execute("SELECT order_id,quote_id,client_order_id,status,created_at FROM swap_orders WHERE client_order_id=?", (client_order_id,)).fetchone()
        return SwapOrder(*row) if row else None
