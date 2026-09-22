import asyncio
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_core.network.p2p_real.node import P2PNode
from native_processing.swap_engine import SwapEngine
from native_processing.swap_protocol import sign_quote
from native_processing.swap_sync import SwapSyncStore


async def _wait_until(predicate, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("load-test condition was not reached before timeout")


async def _run_load(tmp_path, node_count=5, intents_per_node=6):
    nodes = [
        P2PNode(host="127.0.0.1", port=0, node_id=f"load-{i}", seeds=[])
        for i in range(node_count)
    ]
    stores = [
        SwapSyncStore(str(tmp_path / f"node-{i}.sqlite3"), f"load-{i}")
        for i in range(node_count)
    ]
    engines = [SwapEngine(":memory:", quote_ttl_seconds=120) for _ in range(node_count)]
    for node, store in zip(nodes, stores):
        node.set_swap_sync_store(store)

    try:
        await asyncio.gather(*(node.start() for node in nodes))
        ports = [node._server.sockets[0].getsockname()[1] for node in nodes]

        # Malha completa TCP para testar fan-out simultâneo e deduplicação.
        await asyncio.gather(*(
            nodes[i].connect_to_peer("127.0.0.1", ports[j])
            for i in range(node_count)
            for j in range(i)
        ))
        await _wait_until(
            lambda: all(len(node._connections) >= node_count - 1 for node in nodes),
            timeout=10.0,
        )
        await _wait_until(
            lambda: all(
                any(node.protocol.SWAP_INTENT_CAPABILITY in payload.get("capabilities", [])
                    for payload in node._peer_versions.values())
                for node in nodes
            ),
            timeout=10.0,
        )

        intents = []
        for origin in range(node_count):
            for seq in range(intents_per_node):
                now = time.time()
                quote = engines[origin].quote(
                    "buy_bait", btc_sats=100_000 + seq, bait_units=2_000_000 + seq, now=now
                )
                intent = sign_quote(
                    quote,
                    maker_id=f"load-maker-{origin}",
                    private_key=Ed25519PrivateKey.generate(),
                    client_order_id=f"load-client-{origin}-{seq}",
                    now=now,
                )
                assert stores[origin].admit_intent(
                    intent, "local", f"load-local-{origin}-{seq}", now=now
                ) == "accepted"
                intents.append((origin, intent))

        # Cada nó faz broadcast simultaneamente, simulando produção concorrente.
        results = await asyncio.gather(*(
            nodes[origin].broadcast_swap_intent(intent.to_dict())
            for origin, intent in intents
        ))
        assert all(result >= node_count - 1 for result in results)

        expected_ids = {intent.order_id for _, intent in intents}
        await _wait_until(
            lambda: all(
                all(store.get_intent(order_id) is not None for order_id in expected_ids)
                for store in stores
            ),
            timeout=15.0,
        )

        # O mesmo conjunto econômico deve convergir em todos os nós.
        for store in stores:
            rows = store.db.execute("SELECT order_id, status FROM swap_intents").fetchall()
            assert {row[0] for row in rows} == expected_ids
            assert all(row[1] == "pending" for row in rows)

        # Reenvio integral testa idempotência sob carga repetida.
        duplicate_results = await asyncio.gather(*(
            nodes[origin].broadcast_swap_intent(intent.to_dict())
            for origin, intent in intents
        ))
        assert all(result >= node_count - 1 for result in duplicate_results)
        await asyncio.sleep(0.25)
        for store in stores:
            count = store.db.execute("SELECT COUNT(*) FROM swap_intents").fetchone()[0]
            assert count == len(expected_ids)

        return {
            "nodes": node_count,
            "intents": len(intents),
            "expected_per_node": len(expected_ids),
            "min_first_broadcast_fanout": min(results),
            "min_duplicate_broadcast_fanout": min(duplicate_results),
        }
    finally:
        await asyncio.gather(*(node.stop() for node in nodes), return_exceptions=True)
        for store in stores:
            store.close()
        for engine in engines:
            engine.close()


def test_p2p_swap_concurrent_multi_node_load(tmp_path):
    result = asyncio.run(_run_load(tmp_path))
    assert result == {
        "nodes": 5,
        "intents": 30,
        "expected_per_node": 30,
        "min_first_broadcast_fanout": 4,
        "min_duplicate_broadcast_fanout": 4,
    }
