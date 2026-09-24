#!/usr/bin/env python3
"""Validação E2E do stack de parity + smoke do ecossistema de produção (read-only)."""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from native_processing.parity_ecosystem import health_parity, live_attestation_dict  # noqa: E402
from native_processing.parity_gate_factory import load_parity_gate  # noqa: E402
from native_processing.schnorr_keypair import SchnorrKeyPair  # noqa: E402
from native_processing.test_parity_gate import make_test_parity_gate  # noqa: E402
from native_processing.parity_attestation_builder import build_signed_attestation  # noqa: E402


def http_json(url: str, timeout: float = 12.0):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bait-parity-e2e/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), None
    except Exception as e:
        return None, str(e)


def main() -> int:
    report = {"local": {}, "production": {}, "status": "FAIL"}

    # --- Local gate ---
    gate, oracles = make_test_parity_gate(clock=time.time)
    att = build_signed_attestation(oracles, bait_usdt=1.0, ttl_seconds=90)
    try:
        digest = gate.validate(att)
        report["local"]["gate_validate"] = "PASS"
        report["local"]["digest"] = digest
    except Exception as e:
        report["local"]["gate_validate"] = f"FAIL: {e}"
        print(json.dumps(report, indent=2))
        return 1

    # Ecosystem helpers
    d = live_attestation_dict(oracles)
    assert d["proof_b64"] and d["pair"] == "BAIT/USDT"
    report["local"]["live_attestation_dict"] = "PASS"
    report["local"]["proof_b64_len"] = len(d["proof_b64"])

    # --- Production read-only ---
    stats, err = http_json("https://mybait.org/api/v1/platform/stats")
    if stats:
        report["production"]["platform_stats"] = {
            "chain_height": stats.get("chain_height"),
            "agents_registered": stats.get("agents_registered"),
            "bait_price": (stats.get("oracle") or {}).get("prices", {}).get("BAIT"),
        }
    else:
        report["production"]["platform_stats"] = f"error: {err}"

    health, err = http_json("https://mybait.org/api/v1/health")
    report["production"]["health"] = health if health else f"error: {err}"

    prices, err = http_json("https://mybait.org/api/v1/oracle/prices")
    report["production"]["oracle_prices"] = prices if prices else f"error: {err}"

    report["status"] = "PASS"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
