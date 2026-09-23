"""Smoke and stress coverage for the local swap path.

The suite deliberately stops before external settlement: it exercises signed
intent creation, TCP propagation, SQLite admission, executor state progression,
and the synthetic BridgeManager lock/proof/mint handoff. No wallet, RPC,
private key, or real-chain transaction is used.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_bridge.manager import BridgeManager
from baitcoin_core.network.p2p_real.node import P2PNode
from baitcoin_core.network.p2p_real.protocol import P2PProtocol
from native_processing.bridge_handoff import SwapBridgeHandoff
from native_processing.swap_engine import SwapEngine
from native_processing.swap_executor import Deposit, OrderState, SwapExecutor
from native_processing.swap_protocol import SwapIntent, sign_quote
from native_processing.swap_service import NativeSwapService
from native_processing.swap_sync import SwapSyncStore


@dataclass
class StaticDepositReader:
    deposits: dict[str, Deposit]

    def find_deposit(self, order_id: str, intent: SwapIntent) -> Deposit | None:
        return self.deposits.get(order_id)


async def _wait_until(predicate, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not reached before timeout")


def _intent(engine: SwapEngine, maker: str, client_id: str, now: float) -> SwapIntent:
    quote = engine.quote("buy_bait", btc_sats=100_000, bait_units=2_000_000, now=now)
    return sign_quote(
        quote,
        maker,
        Ed25519PrivateKey.generate(),
        client_id,
        now=now,
        btc_deposit_address=f"bcrt1q{client_id}",
        bait_recipient_pubkey=b"r" * 32,
        network="regtest",
    )


async def _run_smoke(tmp_path: Path) -> dict[str, str]:
    engine = SwapEngine(str(tmp_path / "smoke-engine.sqlite"), quote_ttl_seconds=120)
    store_a = SwapSyncStore(str(tmp_path / "smoke-a.sqlite"), "smoke-a")
    store_b = SwapSyncStore(str(tmp_path / "smoke-b.sqlite"), "smoke-b")
    node_a = P2PNode("127.0.0.1", 0, node_id="smoke-a", seeds=[])
    node_b = P2PNode("127.0.0.1", 0, node_id="smoke-b", seeds=[])
    deposits: dict[str, Deposit] = {}
    executor_b = SwapExecutor(
        str(tmp_path / "smoke-executor.sqlite"),
        StaticDepositReader(deposits),
        bait=object(),
        enable_settlement=False,
        required_confirmations=2,
    )
    node_a.set_swap_sync_store(store_a)
    node_b.set_swap_sync_store(store_b)
    service_b = NativeSwapService(engine, store_b, executor_b, p2p_node=node_b)

    try:
        await node_a.start()
        await node_b.start()
        port_a = node_a._server.sockets[0].getsockname()[1]
        assert await node_b.connect_to_peer("127.0.0.1", port_a)
        await _wait_until(lambda: len(node_b._connections) == 1)
        await _wait_until(lambda: node_a._peer_versions and node_b._peer_versions)

        now = time.time()
        intent = _intent(engine, "smoke-maker", "smoke-client-1", now)
        assert store_a.admit_intent(intent, "local", "smoke-local-1", now=now) == "accepted"
        assert await node_a.broadcast_swap_intent(intent.to_dict()) == 1
        await _wait_until(lambda: store_b.get_intent(intent.order_id) is not None)

        remote = SwapIntent.from_dict({k: v for k, v in store_b.get_intent(intent.order_id).items() if k not in {"status", "origin_node", "origin_seq"}})
        deposits[intent.order_id] = Deposit(
            txid="a" * 64,
            btc_sats=intent.btc_sats,
            confirmations=2,
            recipient=intent.btc_deposit_address,
            network="regtest",
        )
        assert service_b.admit_intent(remote) == OrderState.INTENT_VALIDATED
        # The executor returns the furthest state reached in one poll, while
        # NativeSwapService persists the required btc_observed intermediate.
        assert service_b.process_order(intent.order_id) == OrderState.BTC_CONFIRMED
        assert executor_b.get_state(intent.order_id) == OrderState.BTC_CONFIRMED

        bridge = BridgeManager()
        handoff = SwapBridgeHandoff(bridge, str(tmp_path / "smoke-handoff.sqlite"))
        try:
            locked = handoff.start_lock(remote, target_chain_id=1, recipient="0xsmoke")
            assert locked["state"] == "locked"
            for index in range(3):
                result = handoff.submit_proof_and_mint(
                    remote.order_id,
                    proof=locked["merkle_proof"],
                    signatures=[(f"signer_{index}", f"smoke-signature-{index}")],
                )
            assert result["handoff_state"] == "minted"
            assert handoff.submit_proof_and_mint(
                remote.order_id,
                proof=locked["merkle_proof"],
                signatures=[(f"signer_{index}", f"smoke-signature-{index}") for index in range(3)],
            )["event_id"] == locked["event_id"]
            assert bridge.get_stats()["total_minted_bait"] == intent.btc_sats / 100_000_000
        finally:
            handoff.close()

        return {"order_id": intent.order_id, "executor_state": executor_b.get_state(intent.order_id).value, "handoff_state": "minted"}
    finally:
        await node_b.stop()
        await node_a.stop()
        executor_b.close()
        store_b.close()
        store_a.close()
        engine.close()


def test_swap_smoke_e2e_signed_tcp_executor_bridge(tmp_path: Path) -> None:
    result = asyncio.run(_run_smoke(tmp_path))
    assert result["executor_state"] == "btc_confirmed"
    assert result["handoff_state"] == "minted"


async def _run_stress(tmp_path: Path, node_count: int = 6, intents_per_node: int = 8) -> dict[str, int | float]:
    started = time.perf_counter()
    nodes = [P2PNode("127.0.0.1", 0, node_id=f"stress-{i}", seeds=[]) for i in range(node_count)]
    stores = [SwapSyncStore(str(tmp_path / f"stress-{i}.sqlite"), f"stress-{i}") for i in range(node_count)]
    engines = [SwapEngine(":memory:", quote_ttl_seconds=120) for _ in range(node_count)]
    for node, store in zip(nodes, stores):
        node.set_swap_sync_store(store)

    try:
        await asyncio.gather(*(node.start() for node in nodes))
        ports = [node._server.sockets[0].getsockname()[1] for node in nodes]
        await asyncio.gather(*(
            nodes[i].connect_to_peer("127.0.0.1", ports[j])
            for i in range(node_count)
            for j in range(i)
        ))
        await _wait_until(lambda: all(len(node._connections) >= node_count - 1 for node in nodes), timeout=15)
        await _wait_until(
            lambda: all(
                len(node._peer_versions) >= node_count - 1
                and all(
                    P2PProtocol.SWAP_INTENT_CAPABILITY
                    in version.get("capabilities", [])
                    for version in node._peer_versions.values()
                )
                for node in nodes
            ),
            timeout=15,
        )

        intents: list[tuple[int, SwapIntent]] = []
        now = time.time()
        for origin in range(node_count):
            for sequence in range(intents_per_node):
                intent = _intent(engines[origin], f"stress-maker-{origin}", f"stress-{origin}-{sequence}", now)
                assert stores[origin].admit_intent(intent, "local", f"stress-local-{origin}-{sequence}", now=now) == "accepted"
                intents.append((origin, intent))

        first = await asyncio.gather(*(nodes[origin].broadcast_swap_intent(intent.to_dict()) for origin, intent in intents))
        expected = {intent.order_id for _, intent in intents}
        await _wait_until(lambda: all(all(store.get_intent(order_id) is not None for order_id in expected) for store in stores), timeout=20)
        for store in stores:
            rows = store.db.execute("SELECT order_id, status FROM swap_intents").fetchall()
            assert {row[0] for row in rows} == expected
            assert all(row[1] == "pending" for row in rows)

        duplicates = await asyncio.gather(*(nodes[origin].broadcast_swap_intent(intent.to_dict()) for origin, intent in intents))
        await asyncio.sleep(0.25)
        for store in stores:
            assert store.db.execute("SELECT COUNT(*) FROM swap_intents").fetchone()[0] == len(expected)

        return {
            "nodes": node_count,
            "intents": len(intents),
            "delivered_per_node": len(expected),
            "min_first_fanout": min(first),
            "min_duplicate_fanout": min(duplicates),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    finally:
        await asyncio.gather(*(node.stop() for node in nodes), return_exceptions=True)
        for store in stores:
            store.close()
        for engine in engines:
            engine.close()


def test_swap_stress_e2e_mesh_deduplicates_broadcasts(tmp_path: Path) -> None:
    result = asyncio.run(_run_stress(tmp_path))
    assert result["nodes"] == 6
    assert result["intents"] == 48
    assert result["delivered_per_node"] == 48
    assert result["min_first_fanout"] >= 5
    assert result["min_duplicate_fanout"] >= 5
    assert result["elapsed_ms"] < 20_000
