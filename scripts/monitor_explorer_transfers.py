#!/usr/bin/env python3
"""One-shot / watch monitor for non-coinbase explorer txs."""
from __future__ import annotations
import argparse, json, sys, time
from collections import Counter
from datetime import datetime, timezone
from urllib.request import Request, urlopen

DEFAULT_URL = "https://mybait.org/api/v1/explorer/txs/latest"

def fetch(url):
    req = Request(url, headers={"Accept":"application/json","User-Agent":"BAITHex-monitor/1.0"})
    with urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode())
    return d.get("transactions") or d.get("txs") or []

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--watch", type=int, default=0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    while True:
        txs = fetch(args.url)
        types = Counter(t.get("tx_type") for t in txs)
        non = [t for t in txs if (t.get("tx_type") or "") != "coinbase"]
        report = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "count": len(txs),
            "types": dict(types),
            "non_coinbase": len(non),
            "signal": "TRANSFER_DETECTED" if non else "ONLY_COINBASE",
            "sample": non[:5],
        }
        print(json.dumps(report, indent=2) if args.json else f"{report['ts']} {report['signal']} types={report['types']}")
        if args.watch <= 0:
            return 0 if non else 1
        time.sleep(args.watch)

if __name__ == "__main__":
    sys.exit(main())
