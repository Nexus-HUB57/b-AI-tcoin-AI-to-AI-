#!/usr/bin/env python3
"""Compare three public node APIs without signing, broadcasting, or mutating state."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit


TIP_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def normalize_origin(origin: str) -> str:
    """Return a canonical API origin and reject ambiguous URLs."""
    parsed = urlsplit(origin.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"invalid API origin: {origin}")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"API origin must not contain credentials/query/fragment: {origin}")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"invalid API port: {origin}") from exc
    hostname = parsed.hostname.lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if port is not None and not ((parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443)):
        netloc = f"{netloc}:{port}"
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", "")).rstrip("/")


def valid_tip_hash(value: object) -> bool:
    return isinstance(value, str) and TIP_HASH_RE.fullmatch(value) is not None


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "baitcoin-public-pool-check/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"{url}: HTTP {response.status}")
        return json.loads(response.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="append", required=True, help="API base ending in /api; repeat for independent nodes")
    parser.add_argument("--min-peers", type=int, default=3)
    parser.add_argument(
        "--require-tip-hash",
        action="store_true",
        help="require every node to expose a valid 64-character hexadecimal tip_hash",
    )
    args = parser.parse_args()
    if len(args.api) < 3:
        parser.error("at least three independent API origins are required")

    try:
        origins = [normalize_origin(origin) for origin in args.api]
    except ValueError as exc:
        parser.error(str(exc))
    if len(origins) != len(set(origins)):
        parser.error("API origins must be unique after normalization")

    observations = []
    failures = []
    for base in origins:
        try:
            status = get_json(f"{base}/api/v1/status")
            p2p = get_json(f"{base}/api/v1/p2p/status")
            tip_hash = status.get("tip_hash")
            observations.append({
                "origin": base,
                "height": status.get("chain_height"),
                "tip_hash": tip_hash,
                "chain_valid": status.get("chain_valid"),
                "peer_count": p2p.get("peer_count", 0),
                "handshake_peers": p2p.get("handshake_peers", 0),
                "running": p2p.get("running", False),
                "attestation": p2p.get("attestation"),
            })
            if status.get("chain_valid") is not True:
                failures.append(f"{base}: chain_valid is not true")
            if p2p.get("peer_count", 0) < args.min_peers or p2p.get("handshake_peers", 0) < args.min_peers:
                failures.append(f"{base}: insufficient live handshakes")
            if not p2p.get("running"):
                failures.append(f"{base}: P2P is not running")
            if tip_hash is not None and not valid_tip_hash(tip_hash):
                failures.append(f"{base}: tip_hash is not a 64-character hexadecimal hash")
            if args.require_tip_hash and not valid_tip_hash(tip_hash):
                failures.append(f"{base}: tip_hash is required")
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
            failures.append(str(exc))

    heights = {item["height"] for item in observations}
    if len(heights) > 1:
        failures.append(f"tip heights diverge: {sorted(heights)}")

    valid_tip_count = sum(
        1 for item in observations if valid_tip_hash(item.get("tip_hash"))
    )
    tip_hashes = {
        item["tip_hash"].lower()
        for item in observations
        if valid_tip_hash(item.get("tip_hash"))
    }
    if tip_hashes and valid_tip_count != len(observations):
        failures.append("incomplete tip_hash evidence across nodes")
    if len(tip_hashes) > 1:
        failures.append(f"tip hashes diverge: {sorted(tip_hashes)}")

    result = {
        "status": "GO" if not failures else "NO-GO",
        "tip_hash_verified": bool(observations) and valid_tip_count == len(observations) and len(tip_hashes) == 1,
        "nodes": observations,
        "failures": failures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
