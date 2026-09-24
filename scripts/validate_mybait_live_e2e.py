#!/usr/bin/env python3
"""Read-only live E2E probe for the public b'AI'tcoin API.

This tool never calls write endpoints, never signs, never broadcasts, and never
loads wallet files or secrets. It is intentionally separate from Bitcoin custody
and from the project's local-chain comprehensive tests.

Usage:
    python3 scripts/validate_mybait_live_e2e.py
    python3 scripts/validate_mybait_live_e2e.py --base-url https://mybait.org --json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://mybait.org"
ENDPOINTS = (
    "/api/v1/status",
    "/api/v1/health",
    "/api/v1/oracle/prices",
    "/api/v1/blockchain",
    "/api/v1/explorer/txs/latest",
    "/api/v1/swap/book",
    "/api/v1/mylink/agents",
    "/api/v1/platform/stats",
    "/mylink/tarefas.json",
    "/mylink/openapi.json",
)


@dataclass
class Probe:
    path: str
    http_status: int | None
    ok: bool
    classification: str
    detail: dict[str, Any]
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "http_status": self.http_status,
            "ok": self.ok,
            "classification": self.classification,
            "detail": self.detail,
            **({"error": self.error} if self.error else {}),
        }


def _json_request(base_url: str, path: str, timeout: float) -> tuple[int, Any]:
    url = base_url.rstrip("/") + path
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "BAITHex-readonly-e2e/1.0"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        return response.status, json.loads(raw.decode("utf-8"))


def classify(path: str, status: int, body: Any) -> Probe:
    detail: dict[str, Any] = {}
    if isinstance(body, dict):
        detail["keys"] = list(body)[:20]

    if status != 200:
        return Probe(path, status, False, "FAIL", detail, f"HTTP {status}")
    if not isinstance(body, dict):
        return Probe(path, status, False, "FAIL", detail, "response is not a JSON object")

    if path == "/api/v1/status":
        detail.update({k: body.get(k) for k in ("network", "version", "chain_height", "chain_valid", "utxo_count", "mempool_size", "agents_registered")})
        required = all(k in body for k in ("network", "chain_height", "chain_valid"))
        return Probe(path, status, required, "OBSERVED" if required else "FAIL", detail, None if required else "missing status fields")
    if path == "/api/v1/health":
        detail.update({k: body.get(k) for k in ("status", "height")})
        ok = body.get("status") == "ok" and isinstance(body.get("height"), int)
        return Probe(path, status, ok, "OBSERVED" if ok else "FAIL", detail, None if ok else "health contract mismatch")
    if path == "/api/v1/blockchain":
        detail.update({k: body.get(k) for k in ("height", "block_count", "utxo_count", "mempool_size", "total_supply_bait")})
        ok = all(k in body for k in ("height", "block_count", "utxo_count"))
        return Probe(path, status, ok, "OBSERVED" if ok else "FAIL", detail, None if ok else "missing blockchain fields")
    if path == "/api/v1/explorer/txs/latest":
        txs = body.get("transactions")
        if not isinstance(txs, list):
            return Probe(path, status, False, "FAIL", detail, "transactions is not a list")
        types = sorted({tx.get("tx_type") for tx in txs if isinstance(tx, dict)})
        detail.update({"transaction_count": len(txs), "tx_types": types, "non_coinbase_count": sum(tx.get("tx_type") != "coinbase" for tx in txs if isinstance(tx, dict))})
        return Probe(path, status, True, "OBSERVED", detail)
    if path == "/api/v1/swap/book":
        orders = body.get("orders", [])
        trades = body.get("trades", [])
        detail.update({"orders": len(orders) if isinstance(orders, list) else None, "trades": len(trades) if isinstance(trades, list) else None, "master_pool": body.get("master_pool"), "custody_btc_present": "custody_btc" in body})
        ok = isinstance(orders, list) and isinstance(trades, list)
        classification = "OBSERVED_MATCHING_ONLY" if ok else "FAIL"
        return Probe(path, status, ok, classification, detail, None if ok else "orders/trades are not lists")
    if path == "/api/v1/mylink/agents":
        detail["total"] = body.get("total")
        ok = isinstance(body.get("total"), int)
        return Probe(path, status, ok, "OBSERVED" if ok else "FAIL", detail, None if ok else "missing integer total")
    if path == "/api/v1/platform/stats":
        detail.update({k: body.get(k) for k in ("chain_height", "agents_registered", "staking", "faucet")})
        return Probe(path, status, True, "OBSERVED", detail)
    if path == "/mylink/tarefas.json":
        detail.update({k: body.get(k) for k in ("ok", "live", "fundo")})
        ok = body.get("ok") is True and isinstance(body.get("tarefas"), list)
        return Probe(path, status, ok, "OBSERVED" if ok else "FAIL", detail, None if ok else "task contract mismatch")
    if path == "/mylink/openapi.json":
        detail.update({k: body.get(k) for k in ("openapi",)})
        info = body.get("info") if isinstance(body.get("info"), dict) else {}
        detail["api_version"] = info.get("version")
        ok = isinstance(body.get("paths"), dict) and bool(body.get("openapi"))
        return Probe(path, status, ok, "OBSERVED" if ok else "FAIL", detail, None if ok else "invalid OpenAPI shape")
    return Probe(path, status, True, "OBSERVED", detail)


def probe(base_url: str, timeout: float) -> dict[str, Any]:
    results: list[Probe] = []
    for path in ENDPOINTS:
        try:
            status, body = _json_request(base_url, path, timeout)
            results.append(classify(path, status, body))
        except HTTPError as exc:
            results.append(Probe(path, exc.code, False, "FAIL", {}, f"HTTP {exc.code}"))
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            results.append(Probe(path, None, False, "FAIL", {}, str(exc)))
    failures = [r for r in results if not r.ok]
    return {
        "base_url": base_url.rstrip("/"),
        "mode": "read-only",
        "write_calls": 0,
        "signing_calls": 0,
        "broadcast_calls": 0,
        "results": [r.as_dict() for r in results],
        "observed": sum(r.ok for r in results),
        "failed": len(failures),
        "overall": "PASS_WITH_LIMITATIONS" if not failures else "FAIL",
        "limitations": [
            "Endpoint availability does not prove monetary settlement or ownership.",
            "b'AI'tcoin Mainnet is distinct from Bitcoin Mainnet.",
            "A filled order is not proof of an on-chain transfer.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = probe(args.base_url, args.timeout)
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for result in report["results"]:
            print(f"[{result['classification']}] {result['path']} HTTP={result['http_status']}")
        print(f"Overall: {report['overall']} ({report['observed']} observed, {report['failed']} failed)")
        print("No signing or broadcast calls were made.")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
