"""Orquestração segura do handoff de SwapIntent para o BridgeManager.

O adaptador não confirma Bitcoin e não assina provas de relayer. Ele valida a
intenção, cria no máximo um lock por order_id e permite concluir proof/mint
somente com as assinaturas fornecidas pelo executor autorizado.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any, Iterable, Mapping, Optional

from baitcoin_bridge.manager import BridgeManager
from baitcoin_bridge.authorization import AuthorizationError, RelayerAuthorization
from .swap_protocol import IntentError, SwapIntent


class BridgeHandoffError(ValueError):
    """Erro de validação, correlação ou estado do handoff."""


class SwapBridgeHandoff:
    """Adapter between a signed SwapIntent and BridgeManager lock/mint APIs."""

    def __init__(self, bridge: BridgeManager, db_path: str = ":memory:", authorizer: RelayerAuthorization | None = None) -> None:
        self.bridge = bridge
        if authorizer is not None and not isinstance(authorizer, RelayerAuthorization):
            raise BridgeHandoffError("authorizer must be a RelayerAuthorization")
        self.authorizer = authorizer
        self.db = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self._lock = threading.RLock()
        with self.db:
            self.db.execute(
                """CREATE TABLE IF NOT EXISTS swap_bridge_handoffs (
                    order_id TEXT PRIMARY KEY,
                    transfer_id TEXT NOT NULL,
                    lock_event_id TEXT NOT NULL,
                    target_chain_id INTEGER NOT NULL,
                    recipient TEXT NOT NULL,
                    amount_sats INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    lock_json TEXT NOT NULL,
                    mint_json TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )

    def close(self) -> None:
        with self._lock:
            self.db.close()

    @staticmethod
    def _intent(raw: SwapIntent | Mapping[str, Any], now: Optional[float]) -> SwapIntent:
        try:
            intent = raw if isinstance(raw, SwapIntent) else SwapIntent.from_dict(raw)
            intent.verify(now=now)
            return intent
        except (IntentError, TypeError, ValueError) as exc:
            raise BridgeHandoffError(f"invalid swap intent: {exc}") from exc

    @staticmethod
    def _validate_args(target_chain_id: int, recipient: str) -> None:
        if type(target_chain_id) is not int or target_chain_id <= 0:
            raise BridgeHandoffError("target_chain_id must be a positive integer")
        if not isinstance(recipient, str) or not recipient or len(recipient) > 256:
            raise BridgeHandoffError("recipient must be a non-empty string")

    def _row(self, order_id: str):
        return self.db.execute(
            "SELECT transfer_id,lock_event_id,target_chain_id,recipient,amount_sats,state,lock_json,mint_json FROM swap_bridge_handoffs WHERE order_id=?",
            (order_id,),
        ).fetchone()

    def start_lock(
        self,
        intent: SwapIntent | Mapping[str, Any],
        *,
        target_chain_id: int,
        recipient: str,
        now: Optional[float] = None,
    ) -> dict[str, Any]:
        """Validate an intent and create or return its idempotent bridge lock."""
        now = time.time() if now is None else float(now)
        self._validate_args(target_chain_id, recipient)
        parsed = self._intent(intent, now)
        with self._lock, self.db:
            row = self._row(parsed.order_id)
            if row:
                if row[2] != target_chain_id or row[3] != recipient or row[4] != parsed.btc_sats:
                    raise BridgeHandoffError("order_id already mapped to different bridge request")
                result = json.loads(row[6])
                result["handoff_state"] = row[5]
                return result
            lock = self.bridge.lock_bait(parsed.maker_id, parsed.btc_sats, target_chain_id, recipient)
            if lock.get("error") or not lock.get("success"):
                raise BridgeHandoffError(f"bridge lock failed: {lock}")
            self.db.execute(
                "INSERT INTO swap_bridge_handoffs VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (parsed.order_id, lock["transfer_id"], lock["event_id"], target_chain_id, recipient,
                 parsed.btc_sats, "locked", json.dumps(lock, sort_keys=True), None, now, now),
            )
            result = dict(lock)
            result.update({"order_id": parsed.order_id, "handoff_state": "locked"})
            return result

    def submit_proof_and_mint(
        self,
        order_id: str,
        *,
        proof: Iterable[str],
        signatures: Iterable[tuple[str, str]],
    ) -> dict[str, Any]:
        """Submit relayer signatures and mint once the bridge threshold is met."""
        with self._lock, self.db:
            row = self._row(order_id)
            if not row:
                raise BridgeHandoffError("unknown order_id")
            if row[5] == "minted":
                return json.loads(row[7])
            latest = None
            proof = list(proof)
            signatures = list(signatures)
            if self.authorizer is not None:
                try:
                    self.authorizer.verify(
                        row[1], row[0], row[2], row[4], proof, signatures
                    )
                except AuthorizationError as exc:
                    raise BridgeHandoffError(f"proof authorization failed: {exc}") from exc
            for signer_id, signature in signatures:
                submitted = self.bridge.submit_proof(row[1], proof, signer_id, signature)
                if submitted.get("error"):
                    raise BridgeHandoffError(f"bridge proof failed: {submitted}")
                latest = submitted
            if latest is None:
                raise BridgeHandoffError("at least one proof signature is required")
            if not latest.get("ready_to_mint"):
                now = time.time()
                self.db.execute(
                    "UPDATE swap_bridge_handoffs SET state='pending_proof', updated_at=? WHERE order_id=?",
                    (now, order_id),
                )
                return dict(latest, order_id=order_id, handoff_state="pending_proof")
            mint = self.bridge.mint_wrapped(row[1])
            if mint.get("error") or not mint.get("success"):
                raise BridgeHandoffError(f"bridge mint failed: {mint}")
            now = time.time()
            self.db.execute(
                "UPDATE swap_bridge_handoffs SET state='minted', mint_json=?, updated_at=? WHERE order_id=?",
                (json.dumps(mint, sort_keys=True), now, order_id),
            )
            return dict(mint, order_id=order_id, handoff_state="minted")

    def get(self, order_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._row(order_id)
            if not row:
                return None
            result = json.loads(row[6])
            result.update({"order_id": order_id, "handoff_state": row[5]})
            result["mint"] = json.loads(row[7]) if row[7] else None
            return result
