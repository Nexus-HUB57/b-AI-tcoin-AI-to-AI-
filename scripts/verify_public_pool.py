#!/usr/bin/env python3
"""Compare three public node APIs without signing, broadcasting, or mutating state."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "baitcoin-public-pool-check/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"{url}: HTTP {response.status}")
        return json.loads(response.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="append", required=True, help="API base ending in /api; repeat exactly three times")
    parser.add_argument("--min-peers", type=int, default=3)
    args = parser.parse_args()
    if len(args.api) < 3:
        parser.error("at least three independent API origins are required")

    observations = []
    failures = []
    for origin in args.api:
        base = origin.rstrip("/")
        try:
            status = get_json(f"{base}/api/v1/status")
            p2p = get_json(f"{base}/api/v1/p2p/status")
            observations.append({
                "origin": base,
                "height": status.get("chain_height"),
                "chain_valid": status.get("chain_valid"),
                "peer_count": p2p.get("peer_count", 0),
                "handshake_peers": p2p.get("handshake_peers", 0),
                "running": p2p.get("running", False),
            })
            if status.get("chain_valid") is not True:
                failures.append(f"{base}: chain_valid is not true")
            if p2p.get("peer_count", 0) < args.min_peers or p2p.get("handshake_peers", 0) < args.min_peers:
                failures.append(f"{base}: insufficient live handshakes")
            if not p2p.get("running"):
                failures.append(f"{base}: P2P is not running")
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
            failures.append(str(exc))

    heights = {item["height"] for item in observations}
    if len(heights) > 1:
        failures.append(f"tip heights diverge: {sorted(heights)}")

    result = {"status": "GO" if not failures else "NO-GO", "nodes": observations, "failures": failures}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
