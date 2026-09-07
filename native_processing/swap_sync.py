"""Pool persistente e sincronização por sequência para SwapIntent.

A camada separa deduplicação de transporte da identidade econômica. Ela não
liquida fundos; apenas registra intenções assinadas e as replica como deltas.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from typing import Any, Mapping, Optional

from .swap_protocol import IntentError, SwapIntent


class SyncError(IntentError):
    pass


class SwapSyncStore:
    """SQLite WAL store idempotente por order_id e por sequência de origem."""

    def __init__(self, db_path: str, origin_node: str, max_intent_bytes: int = 16_384):
        if not origin_node or max_intent_bytes < 1024:
            raise ValueError("invalid sync store configuration")
        self.origin_node = origin_node
        self.max_intent_bytes = max_intent_bytes
        self.db = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.RLock()
        with self.db:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS swap_sync_meta (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS swap_intents (
                    order_id TEXT PRIMARY KEY, canonical_hash TEXT NOT NULL UNIQUE,
                    maker_id TEXT NOT NULL, intent_nonce TEXT NOT NULL,
                    payload_json TEXT NOT NULL, status TEXT NOT NULL,
                    first_seen_at REAL NOT NULL, origin_node TEXT NOT NULL,
                    origin_seq INTEGER NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_swap_intent_maker_nonce
                    ON swap_intents(maker_id, intent_nonce);
                CREATE TABLE IF NOT EXISTS swap_inbox (
                    sender TEXT NOT NULL, transport_nonce TEXT NOT NULL,
                    payload_hash TEXT NOT NULL, received_at REAL NOT NULL,
                    PRIMARY KEY(sender, transport_nonce)
                );
                CREATE TABLE IF NOT EXISTS swap_sync_log (
                    origin_node TEXT NOT NULL, origin_seq INTEGER NOT NULL,
                    order_id TEXT NOT NULL, payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL, created_at REAL NOT NULL,
                    PRIMARY KEY(origin_node, origin_seq)
                );
                CREATE TABLE IF NOT EXISTS swap_sync_cursors (
                    peer_id TEXT NOT NULL, origin_node TEXT NOT NULL,
                    last_seq INTEGER NOT NULL, updated_at REAL NOT NULL,
                    PRIMARY KEY(peer_id, origin_node)
                );
            """)

    def close(self) -> None:
        with self._lock:
            self.db.close()

    @staticmethod
    def canonical_hash(intent: SwapIntent) -> str:
        return hashlib.sha256(intent.signing_bytes() + intent.signature_b64.encode("ascii")).hexdigest()

    def _next_seq(self) -> int:
        row = self.db.execute("SELECT value FROM swap_sync_meta WHERE key='origin_seq'").fetchone()
        seq = int(row[0]) + 1 if row else 1
        self.db.execute("INSERT INTO swap_sync_meta(key,value) VALUES('origin_seq',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(seq),))
        return seq

    def admit_intent(self, intent: SwapIntent, sender: str, transport_nonce: str, now: Optional[float] = None) -> str:
        now = time.time() if now is None else float(now)
        raw = intent.to_dict()
        encoded = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(encoded.encode("utf-8")) > self.max_intent_bytes:
            raise SyncError("swap intent exceeds size limit")
        intent.verify(now=now)
        digest = self.canonical_hash(intent)
        with self._lock, self.db:
            prior_transport = self.db.execute("SELECT 1 FROM swap_inbox WHERE sender=? AND transport_nonce=?", (sender, transport_nonce)).fetchone()
            if prior_transport:
                return "duplicate"
            self.db.execute("INSERT INTO swap_inbox VALUES(?,?,?,?)", (sender, transport_nonce, digest, now))
            prior = self.db.execute("SELECT canonical_hash FROM swap_intents WHERE order_id=?", (intent.order_id,)).fetchone()
            if prior:
                if prior[0] != digest:
                    return "conflict"
                return "duplicate"
            maker_prior = self.db.execute("SELECT order_id FROM swap_intents WHERE maker_id=? AND intent_nonce=?", (intent.maker_id, intent.nonce)).fetchone()
            if maker_prior and maker_prior[0] != intent.order_id:
                return "conflict"
            seq = self._next_seq()
            self.db.execute("INSERT INTO swap_intents VALUES(?,?,?,?,?,?,?,?,?)", (intent.order_id, digest, intent.maker_id, intent.nonce, encoded, "pending", now, self.origin_node, seq))
            self.db.execute("INSERT INTO swap_sync_log VALUES(?,?,?,?,?,?)", (self.origin_node, seq, intent.order_id, encoded, digest, now))
        return "accepted"

    def get_intent(self, order_id: str) -> Optional[dict[str, Any]]:
        row = self.db.execute("SELECT payload_json,status,origin_node,origin_seq FROM swap_intents WHERE order_id=?", (order_id,)).fetchone()
        if not row:
            return None
        result = json.loads(row[0]); result.update({"status": row[1], "origin_node": row[2], "origin_seq": row[3]})
        return result

    def deltas(self, origin_node: str, from_seq: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 1 or limit > 500 or from_seq < 0:
            raise SyncError("invalid sync range")
        rows = self.db.execute("SELECT origin_seq,order_id,payload_json,payload_hash FROM swap_sync_log WHERE origin_node=? AND origin_seq>? ORDER BY origin_seq LIMIT ?", (origin_node, from_seq, limit)).fetchall()
        return [{"origin_node": origin_node, "origin_seq": row[0], "order_id": row[1], "intent": json.loads(row[2]), "payload_hash": row[3]} for row in rows]

    def apply_deltas(self, peer_id: str, items: list[Mapping[str, Any]], now: Optional[float] = None) -> tuple[int, int, int]:
        accepted = duplicates = conflicts = 0
        for item in items:
            if not isinstance(item, Mapping) or not isinstance(item.get("intent"), Mapping):
                raise SyncError("invalid sync item")
            intent = SwapIntent.from_dict(item["intent"])
            result = self.admit_intent(intent, peer_id, f"sync:{item.get('origin_node')}:{item.get('origin_seq')}", now=now)
            if result == "accepted": accepted += 1
            elif result == "duplicate": duplicates += 1
            else: conflicts += 1
            origin = str(item.get("origin_node", "")); seq = int(item.get("origin_seq", 0))
            if origin and seq > 0:
                with self._lock, self.db:
                    self.db.execute("INSERT INTO swap_sync_cursors VALUES(?,?,?,?) ON CONFLICT(peer_id,origin_node) DO UPDATE SET last_seq=MAX(last_seq,excluded.last_seq), updated_at=excluded.updated_at", (peer_id, origin, seq, time.time()))
        return accepted, duplicates, conflicts

    def cursor(self, peer_id: str, origin_node: str) -> int:
        row = self.db.execute("SELECT last_seq FROM swap_sync_cursors WHERE peer_id=? AND origin_node=?", (peer_id, origin_node)).fetchone()
        return int(row[0]) if row else 0
