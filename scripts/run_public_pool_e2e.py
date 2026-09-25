#!/usr/bin/env python3
"""Run a deterministic four-node transport-only P2P E2E probe.

This probe binds ephemeral loopback ports only. It does not represent public
infrastructure and never signs, broadcasts, or touches custody assets.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from baitcoin_core.network.p2p_real.node import P2PNode


async def wait_until(predicate, timeout: float = 8.0, interval: float = 0.05) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(interval)
    raise TimeoutError("condition was not reached before timeout")


async def run(node_count: int = 4) -> dict[str, Any]:
    nodes = [
        P2PNode(host="127.0.0.1", port=0, node_id=f"e2e-node-{i}", agent_id=f"e2e-agent-{i}", seeds=[])
        for i in range(node_count)
    ]
    try:
        await asyncio.gather(*(node.start() for node in nodes))
        endpoints = [
            ("127.0.0.1", node._server.sockets[0].getsockname()[1])
            for node in nodes
        ]
        for i, node in enumerate(nodes):
            for j in range(i + 1, node_count):
                host, port = endpoints[j]
                assert await node.connect_to_peer(host, port), f"node {i} failed to connect to node {j}"

        await wait_until(
            lambda: all(
                node.get_public_status()["handshake_peers"] >= node_count - 1
                for node in nodes
            )
        )

        statuses = [node.get_public_status() for node in nodes]
        assert all(status["running"] for status in statuses)
        assert all(status["peer_count"] == node_count - 1 for status in statuses), statuses
        assert all(status["handshake_peers"] == node_count - 1 for status in statuses), statuses

        block = {
            "hash": hashlib.sha256(b"public-pool-e2e-block").hexdigest(),
            "height": 1,
            "previous_hash": "0" * 64,
            "network": "baitcoin-testnet",
        }
        assert await nodes[0].broadcast_block(block) == node_count - 1
        await wait_until(
            lambda: all(
                block["hash"] in node.protocol._known_blocks
                for node in nodes[1:]
            )
        )

        return {
            "status": "GO",
            "mode": "local-transport-only",
            "node_count": node_count,
            "endpoints": [{"host": host, "port": port} for host, port in endpoints],
            "nodes": statuses,
            "gossip": {"block_hash": block["hash"], "recipients": node_count - 1},
        }
    finally:
        await asyncio.gather(*(node.stop() for node in nodes), return_exceptions=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=4)
    args = parser.parse_args()
    if args.nodes < 4:
        parser.error("at least four nodes are required for a three-peer-per-node pool")
    try:
        result = asyncio.run(run(args.nodes))
    except (AssertionError, OSError, TimeoutError) as exc:
        result = {"status": "NO-GO", "mode": "local-transport-only", "error": str(exc)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
