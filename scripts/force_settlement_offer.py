#!/usr/bin/env python3
"""Safely preflight one pending swap settlement.

Despite the historical filename, this tool does NOT force, sign, broadcast, or
mutate a settlement. It reads the local SwapExecutor SQLite database and emits
a deterministic plan. The execution path is intentionally fail-closed until an
external signer, PSBT workflow, broadcaster, allowlist and independent approval
are integrated.

Usage:
    python3 scripts/force_settlement_offer.py --db executor.sqlite --order-id ID --dry-run

The default mode is dry-run. ``--execute`` is rejected by design so an operator
cannot accidentally move funds by invoking this helper.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

BLOCKED_STATES = {"settled", "refunded", "reconciling"}
REQUIRED_INTENT_FIELDS = ("order_id", "quote_id", "btc_sats", "created_at", "expires_at")


@dataclass
class Preflight:
    order_id: str
    db: str
    state: str
    decision: str
    reasons: list[str]
    evidence: dict[str, Any]
    actions_not_performed: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _json_object(raw: str | None, name: str) -> tuple[dict[str, Any] | None, str | None]:
    if not raw:
        return None, f"{name} is missing"
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        return None, f"{name} is invalid JSON: {exc}"
    if not isinstance(value, dict):
        return None, f"{name} is not a JSON object"
    return value, None


def load_order(db_path: Path, order_id: str) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    if not db_path.exists():
        raise FileNotFoundError(f"database does not exist: {db_path}")
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT intent_json,state,intent_digest,deposit_json,external_id "
            "FROM orders WHERE order_id=?",
            (order_id,),
        ).fetchone()
    if row is None:
        raise LookupError(f"order not found: {order_id}")
    intent, intent_error = _json_object(row[0], "intent_json")
    if intent is None:
        raise ValueError(intent_error)
    deposit, deposit_error = _json_object(row[3], "deposit_json")
    record = {
        "state": row[1],
        "intent_digest": row[2],
        "external_id": row[4],
        "intent_error": intent_error,
        "deposit_error": deposit_error,
    }
    return record, intent, deposit


def preflight(db_path: Path, order_id: str, now: float | None = None) -> Preflight:
    record, intent, deposit = load_order(db_path, order_id)
    state = str(record["state"])
    reasons: list[str] = []
    evidence: dict[str, Any] = {
        "intent_digest": record.get("intent_digest"),
        "external_id_present": bool(record.get("external_id")),
        "intent_fields_present": sorted(intent),
        "deposit_present": deposit is not None,
    }

    missing = [key for key in REQUIRED_INTENT_FIELDS if key not in intent]
    if missing:
        reasons.append(f"intent missing fields: {', '.join(missing)}")
    if state in BLOCKED_STATES:
        reasons.append(f"terminal or reconciliation state: {state}")
    if state not in {"pending", "intent_validated", "btc_observed", "btc_confirmed", "bait_submitted"}:
        reasons.append(f"unsupported executor state: {state}")

    if now is not None and isinstance(intent.get("expires_at"), (int, float)) and now >= float(intent["expires_at"]):
        reasons.append("intent is expired")
    if deposit is None:
        reasons.append("no persisted and validated deposit is available for settlement")
    if deposit is not None:
        evidence.update({
            "deposit_txid": deposit.get("txid"),
            "deposit_vout": deposit.get("vout"),
            "deposit_network": deposit.get("network"),
            "deposit_confirmations": deposit.get("confirmations"),
            "deposit_btc_sats": deposit.get("btc_sats"),
        })
        if not deposit.get("txid") or not isinstance(deposit.get("vout"), int):
            reasons.append("deposit lacks a complete txid:vout")
        if intent.get("btc_sats") is not None and deposit.get("btc_sats") != intent.get("btc_sats"):
            reasons.append("deposit amount does not match intent")
        if intent.get("network") and deposit.get("network") and intent["network"] != deposit["network"]:
            reasons.append("deposit network does not match intent network")
        if intent.get("btc_deposit_address") and deposit.get("recipient") and intent["btc_deposit_address"] != deposit["recipient"]:
            reasons.append("deposit recipient does not match intent")

    evidence["requested_network"] = intent.get("network")
    evidence["btc_sats"] = intent.get("btc_sats")
    evidence["btc_deposit_address_present"] = bool(intent.get("btc_deposit_address"))
    evidence["parity_attestation_present"] = bool(intent.get("parity_attestation_json"))
    if not intent.get("parity_attestation_json"):
        reasons.append("BAIT/USDT parity attestation is absent")

    decision = "READY_FOR_MANUAL_REVIEW" if not reasons else "BLOCKED"
    return Preflight(
        order_id=order_id,
        db=str(db_path),
        state=state,
        decision=decision,
        reasons=reasons,
        evidence=evidence,
        actions_not_performed=[
            "executor.process()",
            "BAIT signing",
            "Bitcoin signing or PSBT finalization",
            "mempool or chain broadcast",
            "database mutation",
            "master_pool update",
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="SwapExecutor SQLite database")
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Explicitly select read-only preflight mode")
    parser.add_argument("--execute", action="store_true", help="Rejected; real settlement is not implemented here")
    parser.add_argument("--now", type=float, help="Reference Unix time for deterministic expiry checks")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    if args.execute:
        print("REFUSED: live settlement is intentionally disabled; use the PSBT/HSM runbook.", file=sys.stderr)
        return 2
    if not args.dry_run:
        print("REFUSED: pass --dry-run; this helper never mutates or broadcasts.", file=sys.stderr)
        return 2

    try:
        result = preflight(args.db, args.order_id, args.now)
    except (FileNotFoundError, LookupError, ValueError, sqlite3.Error) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1

    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Decision: {result.decision}")
        print(f"Order: {result.order_id}")
        print(f"State: {result.state}")
        if result.reasons:
            for reason in result.reasons:
                print(f"- BLOCK: {reason}")
        print("No signing, broadcast, executor.process(), or database mutation performed.")
    return 0 if result.decision == "READY_FOR_MANUAL_REVIEW" else 1


if __name__ == "__main__":
    sys.exit(main())
