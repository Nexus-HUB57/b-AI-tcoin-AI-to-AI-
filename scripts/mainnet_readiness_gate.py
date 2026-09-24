#!/usr/bin/env python3
"""Fail-closed, read-only Mainnet readiness gate.

This script never signs, broadcasts, deploys, opens ports, or changes custody.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


class GateFailure(RuntimeError):
    pass


def get_json(url: str, timeout: float = 15.0) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "baitcoin-mainnet-readiness/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise GateFailure(f"{url}: HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GateFailure(f"{url}: {exc}") from exc


def rpc(rpc_url: str, method: str, params: list) -> object:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(
        rpc_url,
        data=body,
        headers={"content-type": "application/json", "User-Agent": "baitcoin-mainnet-readiness/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode())
    if "error" in payload:
        raise GateFailure(f"RPC {method}: {payload['error']}")
    return payload.get("result")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="public API origin, e.g. https://mybait.org/api")
    parser.add_argument("--eth-rpc", required=True)
    parser.add_argument("--manifest", default="deploy/mainnet-addresses.json")
    parser.add_argument("--min-peers", type=int, default=3)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    failures: list[str] = []
    evidence: dict = {"checks": {}}

    try:
        status = get_json(f"{base}/api/v1/status")
        evidence["checks"]["api_status"] = status
        if status.get("chain_valid") is not True:
            failures.append("public status chain_valid is not true")
    except GateFailure as exc:
        failures.append(str(exc))

    try:
        p2p = get_json(f"{base}/api/v1/p2p/status")
        evidence["checks"]["p2p"] = p2p
        if p2p.get("peer_count", 0) < args.min_peers:
            failures.append(f"P2P peer_count < {args.min_peers}")
        if p2p.get("handshake_peers", 0) < args.min_peers:
            failures.append(f"P2P handshake_peers < {args.min_peers}")
        if not p2p.get("running"):
            failures.append("P2P transport is not running")
    except GateFailure as exc:
        failures.append(str(exc))

    manifest = json.loads(Path(args.manifest).read_text())
    evidence["checks"]["manifest"] = {
        "network": manifest.get("network"),
        "chain_id": manifest.get("chain_id"),
        "deployed_at": manifest.get("deployed_at"),
        "deploy_tx_hash": manifest.get("deploy_tx_hash"),
    }
    if manifest.get("chain_id") != 1 or manifest.get("network") != "ethereum-mainnet":
        failures.append("manifest is not Ethereum Mainnet")
    if not manifest.get("deployed_at") or not manifest.get("deploy_tx_hash"):
        failures.append("manifest has no deployment timestamp/transaction")

    try:
        chain_id = rpc(args.eth_rpc, "eth_chainId", [])
        if chain_id != "0x1":
            failures.append(f"Ethereum RPC chain id is {chain_id}, expected 0x1")
        for name, entry in manifest.get("contracts", {}).items():
            address = entry.get("address")
            code = rpc(args.eth_rpc, "eth_getCode", [address, "latest"])
            evidence["checks"].setdefault("contracts", {})[name] = {"address": address, "bytecode_bytes": max(0, (len(code) - 2) // 2) if isinstance(code, str) else 0}
            if not isinstance(code, str) or code in ("0x", "0x0"):
                failures.append(f"{name} has empty Ethereum bytecode")
    except (GateFailure, urllib.error.URLError, TimeoutError) as exc:
        failures.append(str(exc))

    evidence["status"] = "GO" if not failures else "NO-GO"
    evidence["failures"] = failures
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
