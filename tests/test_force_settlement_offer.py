from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from scripts.force_settlement_offer import preflight

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "force_settlement_offer.py"


def create_db(path: Path, *, state: str, intent: dict, deposit: dict | None = None) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE orders ("
            "order_id TEXT PRIMARY KEY, intent_json TEXT NOT NULL, state TEXT NOT NULL, "
            "intent_digest TEXT NOT NULL, deposit_json TEXT, external_id TEXT, updated_at REAL NOT NULL, "
            "parity_digest TEXT NOT NULL DEFAULT '')"
        )
        db.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                intent["order_id"],
                json.dumps(intent),
                state,
                "digest-for-test",
                json.dumps(deposit) if deposit is not None else None,
                None,
                1000.0,
                "parity-for-test" if intent.get("parity_attestation_json") else "",
            ),
        )


def valid_intent() -> dict:
    return {
        "order_id": "order-1",
        "quote_id": "quote-1",
        "btc_sats": 100_000,
        "created_at": 1000.0,
        "expires_at": 2000.0,
        "network": "regtest",
        "btc_deposit_address": "bcrt1qexample",
        "parity_attestation_json": json.dumps({"quorum": 3, "round_id": "r1"}),
    }


def valid_deposit() -> dict:
    return {
        "txid": "a" * 64,
        "vout": 0,
        "network": "regtest",
        "recipient": "bcrt1qexample",
        "btc_sats": 100_000,
        "confirmations": 3,
    }


def test_valid_record_is_only_ready_for_manual_review(tmp_path: Path):
    db = tmp_path / "executor.sqlite"
    create_db(db, state="btc_confirmed", intent=valid_intent(), deposit=valid_deposit())
    result = preflight(db, "order-1", now=1500.0)
    assert result.decision == "READY_FOR_MANUAL_REVIEW"
    assert result.evidence["deposit_txid"] == "a" * 64
    assert "mempool or chain broadcast" in result.actions_not_performed


def test_missing_deposit_and_parity_are_blocked(tmp_path: Path):
    db = tmp_path / "executor.sqlite"
    intent = valid_intent()
    intent["parity_attestation_json"] = ""
    create_db(db, state="intent_validated", intent=intent)
    result = preflight(db, "order-1", now=1500.0)
    assert result.decision == "BLOCKED"
    assert any("deposit" in reason for reason in result.reasons)
    assert any("parity" in reason for reason in result.reasons)


def test_mismatch_and_terminal_state_are_blocked(tmp_path: Path):
    db = tmp_path / "executor.sqlite"
    deposit = valid_deposit()
    deposit["btc_sats"] = 99_999
    create_db(db, state="settled", intent=valid_intent(), deposit=deposit)
    result = preflight(db, "order-1", now=1500.0)
    assert result.decision == "BLOCKED"
    assert any("terminal" in reason for reason in result.reasons)
    assert any("amount" in reason for reason in result.reasons)


def test_cli_rejects_execute_and_does_not_create_mutation(tmp_path: Path):
    db = tmp_path / "executor.sqlite"
    create_db(db, state="btc_confirmed", intent=valid_intent(), deposit=valid_deposit())
    before = db.read_bytes()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--db", str(db), "--order-id", "order-1", "--execute"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "REFUSED" in proc.stderr
    assert db.read_bytes() == before


def test_cli_dry_run_json_is_read_only(tmp_path: Path):
    db = tmp_path / "executor.sqlite"
    create_db(db, state="btc_confirmed", intent=valid_intent(), deposit=valid_deposit())
    before = db.read_bytes()
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--db",
            str(db),
            "--order-id",
            "order-1",
            "--dry-run",
            "--now",
            "1500",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["decision"] == "READY_FOR_MANUAL_REVIEW"
    assert db.read_bytes() == before
