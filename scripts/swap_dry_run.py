#!/usr/bin/env python3
"""Safe dry-run executor for the repository's deterministic SwapEngine.

This command validates the YAML configuration before every run, creates a local
idempotent order, applies configured limits, and records simulated state events.
It has no Lightning, Bitcoin RPC, wallet, signer, or network side effects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
import uuid
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required: python3 -m pip install --user pyyaml", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from native_processing.swap_engine import SwapEngine, SwapError  # noqa: E402
from validate_lightning_config import UniqueKeyLoader, Validator  # noqa: E402

SATOSHIS_PER_BTC = Decimal("100000000")


class DryRunError(ValueError):
    pass


def load_config(path: Path, allow_placeholders: bool) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.load(handle, Loader=UniqueKeyLoader)
    except FileNotFoundError as exc:
        raise DryRunError(f"configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise DryRunError(f"invalid YAML: {exc.__class__.__name__}") from exc
    validator = Validator(data, allow_placeholders=allow_placeholders)
    validator.check()
    if validator.errors:
        raise DryRunError("configuration failed safety validation: " + "; ".join(validator.errors))
    if data.get("execution", {}).get("mode") != "dry-run":
        raise DryRunError("dry-run executor requires execution.mode=dry-run")
    if data.get("mainnet_guard", {}).get("enabled") is True:
        raise DryRunError("dry-run executor refuses mainnet_guard.enabled=true")
    return data


def btc_to_sats(amount: str) -> int:
    try:
        value = Decimal(amount)
    except InvalidOperation as exc:
        raise DryRunError("amount-btc must be a decimal BTC amount") from exc
    if value <= 0:
        raise DryRunError("amount-btc must be greater than zero")
    sats = (value * SATOSHIS_PER_BTC).to_integral_value(rounding=ROUND_DOWN)
    if value * SATOSHIS_PER_BTC != sats:
        raise DryRunError("amount-btc has more than 8 decimal places")
    return int(sats)


def numeric_btc(config: dict[str, Any], path: tuple[str, ...]) -> Decimal:
    value: Any = config
    for part in path:
        value = value[part]
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise DryRunError(f"invalid numeric configuration at {'.'.join(path)}") from exc


def limit_check(config: dict[str, Any], btc_sats: int, db: sqlite3.Connection) -> None:
    amount = Decimal(btc_sats) / SATOSHIS_PER_BTC
    minimum = numeric_btc(config, ("limits", "min_order_amount_btc"))
    maximum = numeric_btc(config, ("limits", "max_order_amount_btc"))
    daily = numeric_btc(config, ("limits", "daily_limit_btc"))
    if amount < minimum:
        raise DryRunError("order rejected: below min_order_amount_btc")
    if amount > maximum:
        raise DryRunError("order rejected: above max_order_amount_btc")
    today = time.strftime("%Y-%m-%d", time.gmtime())
    row = db.execute("SELECT COALESCE(SUM(btc_sats), 0) FROM dry_run_events WHERE event_day=? AND event_type='created'", (today,)).fetchone()
    used_btc = Decimal(int(row[0] or 0)) / SATOSHIS_PER_BTC
    if used_btc + amount > daily:
        raise DryRunError("order rejected: daily_limit_btc exceeded")


def create_audit_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("""CREATE TABLE IF NOT EXISTS dry_run_events (
        event_id TEXT PRIMARY KEY,
        event_day TEXT NOT NULL,
        event_type TEXT NOT NULL,
        client_order_id TEXT NOT NULL,
        order_id TEXT,
        btc_sats INTEGER NOT NULL,
        bait_units INTEGER NOT NULL,
        state TEXT NOT NULL,
        config_hash TEXT NOT NULL,
        created_at REAL NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_dry_run_day ON dry_run_events(event_day, event_type)")
    db.commit()
    return db


def config_hash(config_path: Path) -> str:
    return hashlib.sha256(config_path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> int:
    config_path = args.config.resolve()
    config = load_config(config_path, args.allow_placeholders)
    btc_sats = btc_to_sats(args.amount_btc)
    if args.bait_units <= 0:
        raise DryRunError("bait-units must be greater than zero")
    client_order_id = args.client_order_id or f"dry-run-{uuid.uuid4().hex}"
    audit_path = args.audit_db.resolve()
    audit = create_audit_db(audit_path)
    engine = SwapEngine(str(args.swap_db), quote_ttl_seconds=int(config["swap"]["quote_ttl_seconds"]))
    try:
        limit_check(config, btc_sats, audit)
        existing = engine.get_order(client_order_id)
        if existing is not None:
            result = {
                "dry_run": True,
                "network": config["environment"],
                "side": args.side,
                "client_order_id": client_order_id,
                "order_id": existing.order_id,
                "quote_id": existing.quote_id,
                "status": existing.status,
                "simulated_state": "created",
                "btc_sats": btc_sats,
                "bait_units": args.bait_units,
                "transmitted": False,
                "wallet_accessed": False,
                "lightning_endpoint_accessed": False,
                "config_sha256": config_hash(config_path),
                "audit_db": str(audit_path),
                "idempotent_replay": True,
            }
            print(json.dumps(result, sort_keys=True))
            return 0
        now = time.time()
        quote = engine.quote(args.side, btc_sats, args.bait_units, now=now)
        order = engine.place_order(quote, client_order_id, now=now)
        event_day = time.strftime("%Y-%m-%d", time.gmtime(now))
        row = audit.execute("SELECT 1 FROM dry_run_events WHERE client_order_id=? AND event_type='created'", (client_order_id,)).fetchone()
        if not row:
            event = {
                "event_id": uuid.uuid4().hex,
                "event_day": event_day,
                "event_type": "created",
                "client_order_id": client_order_id,
                "order_id": order.order_id,
                "btc_sats": btc_sats,
                "bait_units": args.bait_units,
                "state": "created",
                "config_hash": config_hash(config_path),
                "created_at": now,
            }
            audit.execute("INSERT INTO dry_run_events VALUES(?,?,?,?,?,?,?,?,?,?)", tuple(event.values()))
            audit.commit()
        result = {
            "dry_run": True,
            "network": config["environment"],
            "side": args.side,
            "client_order_id": client_order_id,
            "order_id": order.order_id,
            "quote_id": quote.quote_id,
            "status": order.status,
            "simulated_state": "created",
            "btc_sats": btc_sats,
            "bait_units": args.bait_units,
            "transmitted": False,
            "wallet_accessed": False,
            "lightning_endpoint_accessed": False,
            "config_sha256": config_hash(config_path),
            "audit_db": str(audit_path),
        }
        print(json.dumps(result, sort_keys=True))
        return 0
    finally:
        engine.close()
        audit.close()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--amount-btc", required=True, help="positive BTC amount, max 8 decimals")
    p.add_argument("--bait-units", type=int, required=True)
    p.add_argument("--side", choices=("buy_bait", "sell_bait"), default="buy_bait")
    p.add_argument("--client-order-id", help="stable idempotency key; generated if omitted")
    p.add_argument("--swap-db", type=Path, default=Path("swap-dry-run.sqlite3"))
    p.add_argument("--audit-db", type=Path, default=Path("swap-dry-run-audit.sqlite3"))
    p.add_argument("--allow-placeholders", action="store_true", help="for template-only dry-run validation")
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        return run(args)
    except (DryRunError, SwapError, KeyError, TypeError) as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
