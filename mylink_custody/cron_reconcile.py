"""Scheduled read-only reconciliation entrypoint.

Inputs are injected through environment variables; no private key or wallet
file is read. The indexer endpoint must return JSON: {"utxos": [...]}.
"""
from __future__ import annotations
import json, os, sys, urllib.request
from pathlib import Path
from .reconcile import UTXO, derive_address, reconcile_utxos


def main() -> int:
    xpub=os.environ.get("MYLINK_WATCH_XPUB", "").strip()
    endpoint=os.environ.get("MYLINK_UTXO_ENDPOINT", "").strip()
    report=Path(os.environ.get("MYLINK_RECONCILIATION_REPORT", "/var/lib/trinity/mylink-reconciliation.json"))
    if not xpub or not endpoint or not endpoint.startswith("https://"):
        print("BLOCKED: MYLINK_WATCH_XPUB and HTTPS MYLINK_UTXO_ENDPOINT are required", file=sys.stderr); return 2
    count=int(os.environ.get("MYLINK_DERIVATION_COUNT", "100"))
    if not 1 <= count <= 10000: print("BLOCKED: invalid derivation count",file=sys.stderr); return 2
    addresses={derive_address(xpub,b,i,os.environ.get("MYLINK_SCRIPT_TYPE","p2wpkh")) for b in (0,1) for i in range(count)}
    req=urllib.request.Request(endpoint, headers={"Accept":"application/json","User-Agent":"mylink-custody-reconciler/1"})
    with urllib.request.urlopen(req, timeout=30) as r: payload=json.loads(r.read().decode())
    rows=[UTXO(str(v["txid"]),int(v["vout"]),int(v["value_sats"]),str(v["address"]),bool(v.get("confirmed",False)),v.get("block_height")) for v in payload.get("utxos",[])]
    result=reconcile_utxos(derived_addresses=addresses,observed=rows)
    result.update({"xpub_fingerprint": xpub[:8], "derived_address_count": len(addresses), "endpoint": endpoint, "read_only": True})
    report.parent.mkdir(parents=True, exist_ok=True); tmp=report.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n"); os.replace(tmp,report)
    print(json.dumps(result,sort_keys=True)); return 0 if result["status"]=="PASS" else 1

if __name__ == "__main__": raise SystemExit(main())
