#!/usr/bin/env python3
"""Validate a public-peer manifest without network calls or secrets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def fail(message: str) -> None:
    raise SystemExit(f"MANIFEST_NO_GO: {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read JSON: {exc}")

    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        fail("nodes must be a list")
    if len(nodes) < int(data.get("minimum_nodes", 4)):
        fail("not enough nodes")

    required = {"node_id", "operator_id", "provider", "region", "asn", "p2p_host", "p2p_port", "api_base"}
    ids = []
    operators = []
    endpoints = []
    for node in nodes:
        if not required.issubset(node):
            fail(f"missing fields for node: {node}")
        serialized = json.dumps(node, sort_keys=True)
        if "REPLACE_" in serialized or ".example.org" in serialized:
            fail(f"unresolved placeholder for node: {node.get('node_id')}")
        if not isinstance(node["p2p_port"], int) or not (1 <= node["p2p_port"] <= 65535):
            fail(f"invalid p2p_port for node: {node.get('node_id')}")
        parsed = urlparse(node["api_base"])
        if parsed.scheme != "https" or not parsed.netloc:
            fail(f"api_base must be HTTPS for node: {node.get('node_id')}")
        ids.append(node["node_id"])
        operators.append(node["operator_id"])
        endpoints.append((node["p2p_host"], node["p2p_port"]))

    if len(ids) != len(set(ids)):
        fail("node_id values must be unique")
    if len(operators) < int(data.get("minimum_independent_operators", 3)):
        fail("fewer than minimum independent operators")
    if len(set(endpoints)) != len(endpoints):
        fail("P2P endpoints must be unique")
    if data.get("network") != "baitcoin-testnet":
        fail("only baitcoin-testnet manifests may pass this pre-Mainnet gate")
    if not data.get("genesis_hash") or "REPLACE_" in data["genesis_hash"]:
        fail("approved testnet genesis_hash is required")

    print(f"MANIFEST_GO: {len(nodes)} nodes, {len(set(operators))} operators, unique P2P endpoints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
