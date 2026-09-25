#!/usr/bin/env python3
"""G-03→G-09 surgical E2E audit (read-only, fail-closed).

Não assina, não broadcast, não habilita settlement.
Uso: python3 scripts/g03_g09_surgical_audit.py [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Any

API = "https://mybait.org"


def fetch(path: str) -> tuple[Any, str]:
    req = urllib.request.Request(
        API + path,
        headers={"User-Agent": "BAITHex-G0309/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read()
    return json.loads(body.decode()), hashlib.sha256(body).hexdigest()


def chainlink_btc() -> dict[str, Any]:
    feed = "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c"
    rpc = "https://rpc.mevblocker.io"

    def call(data: str) -> str:
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": feed, "data": data}, "latest"],
            }
        ).encode()
        req = urllib.request.Request(
            rpc,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "BAITHex/1.0"},
            method="POST",
        )
        return json.loads(urllib.request.urlopen(req, timeout=12).read())["result"]

    try:
        dec = int(call("0x313ce567"), 16)
        raw = call("0xfeaf968c")[2:]
        words = [raw[i : i + 64] for i in range(0, 320, 64)]
        ans = int(words[1], 16)
        if ans >= 2**255:
            ans -= 2**256
        upd = int(words[3], 16)
        price = ans / (10**dec)
        return {"price": price, "age_s": time.time() - upd, "ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def audit() -> dict[str, Any]:
    status, h_s = fetch("/api/v1/status")
    book, h_b = fetch("/api/v1/swap/book")
    expl, h_e = fetch("/api/v1/explorer/txs/latest")
    txs = expl.get("transactions") or []
    types = dict(Counter(t.get("tx_type") for t in txs))
    non_cb = [t for t in txs if (t.get("tx_type") or "") != "coinbase"]
    fills = book.get("fills") or []
    offers = book.get("offers") or []
    orders = book.get("orders") or []
    trades = book.get("trades") or []
    pool = book.get("master_pool") or {}
    cl = chainlink_btc()
    bait_btc = (status.get("oracle") or {}).get("prices", {}).get("BTC")
    diff = None
    if cl.get("ok") and bait_btc:
        diff = abs(cl["price"] - bait_btc) / bait_btc * 10_000

    gates = {
        "G-03": {
            "name": "A2A non-coinbase tx",
            "status": "BLOCKED" if not non_cb else "PASS",
            "detail": f"types={types} non_coinbase={len(non_cb)}",
        },
        "G-04": {
            "name": "Matching book/order/fill",
            "status": "PARTIAL" if (fills or trades) else "BLOCKED",
            "detail": f"offers={len(offers)} fills={len(fills)} orders={len(orders)} trades={len(trades)}",
        },
        "G-05": {
            "name": "BTC deposit UTXO",
            "status": "BLOCKED",
            "detail": f"custody={book.get('custody_btc')} pool_utxos={pool.get('utxos')} (no public txid:vout)",
        },
        "G-06": {
            "name": "BAIT settlement confirmed",
            "status": "BLOCKED",
            "detail": "no transfer in explorer; enable_settlement not public",
        },
        "G-07": {
            "name": "BTC payout",
            "status": "BLOCKED",
            "detail": f"master_pool={pool}; no PSBT path from public API",
        },
        "G-08": {
            "name": "master_pool",
            "status": "BLOCKED" if not (pool.get("btc") or pool.get("utxos")) else "PASS",
            "detail": str(pool),
        },
        "G-09": {
            "name": "ParityGate",
            "status": "CODE_READY_PROD_PENDING",
            "detail": f"chainlink_btc={cl.get('price')} bait={bait_btc} diff_bps={round(diff, 2) if diff is not None else None}",
        },
    }
    return {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "height": status.get("chain_height"),
        "chain_valid": status.get("chain_valid"),
        "payload_sha256": {"status": h_s, "book": h_b, "explorer": h_e},
        "gates": gates,
        "go_live_financial": "BLOCKED",
        "hard_stop": "no broadcast/sweep without HSM+PSBT+2 reviewers",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    try:
        report = audit()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"height={report['height']} valid={report['chain_valid']} "
            f"go_live={report['go_live_financial']}"
        )
        for gid, g in report["gates"].items():
            print(f"  [{g['status']}] {gid} {g['name']}: {g['detail']}")
    return 0 if report["go_live_financial"] != "BLOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
