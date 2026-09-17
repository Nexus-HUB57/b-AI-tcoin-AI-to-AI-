import asyncio
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_core.network.p2p_real.node import P2PNode
from native_processing.swap_engine import SwapEngine
from native_processing.swap_protocol import sign_quote
from native_processing.swap_sync import SwapSyncStore


async def _wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("condition was not reached before timeout")


async def _run_real_tcp_swap_flow(tmp_path):
    # O seed inválido impede conexões externas durante o teste; as conexões
    # relevantes são abertas explicitamente entre as duas portas efêmeras.
    node_a = P2PNode(host="127.0.0.1", port=0, node_id="node-a", seeds=[("127.0.0.1", 1)])
    node_b = P2PNode(host="127.0.0.1", port=0, node_id="node-b", seeds=[("127.0.0.1", 1)])
    store_a = SwapSyncStore(str(tmp_path / "a.sqlite3"), "node-a")
    store_b = SwapSyncStore(str(tmp_path / "b.sqlite3"), "node-b")
    node_a.set_swap_sync_store(store_a)
    node_b.set_swap_sync_store(store_b)
    received = []
    node_b.on_swap_intent_received(lambda intent, peer_id: received.append((intent, peer_id)))
    private = Ed25519PrivateKey.generate()
    engine = SwapEngine(":memory:", quote_ttl_seconds=30)
    now = time.time()
    bootstrap_quote = engine.quote("buy_bait", 100_000, 2_000_000, now=now)
    bootstrap_intent = sign_quote(bootstrap_quote, "maker-bootstrap", private, "client-bootstrap", now=now)
    assert store_a.admit_intent(bootstrap_intent, "local", "local-bootstrap", now=now) == "accepted"

    try:
        await node_a.start()
        await node_b.start()
        port_a = node_a._server.sockets[0].getsockname()[1]
        assert await node_b.connect_to_peer("127.0.0.1", port_a)

        await _wait_until(lambda: "127.0.0.1:" + str(port_a) in node_b._connections)
        await _wait_until(lambda: any(
            item.get("capabilities") and
            node_a.protocol.SWAP_INTENT_CAPABILITY in item["capabilities"]
            for item in node_a._peer_versions.values()
        ))
        await _wait_until(lambda: store_b.get_intent(bootstrap_intent.order_id) is not None)
        assert store_b.get_intent(bootstrap_intent.order_id)["status"] == "pending"

        now = time.time()
        quote = engine.quote("buy_bait", 100_000, 2_000_000, now=now)
        intent = sign_quote(quote, "maker-e2e", private, "client-e2e", now=now)
        assert store_a.admit_intent(intent, "local", "local-e2e", now=now) == "accepted"
        assert await node_a.broadcast_swap_intent(intent.to_dict()) == 1

        await _wait_until(lambda: len(received) == 1)
        received_intent, peer_id = received[0]
        assert received_intent.order_id == intent.order_id
        assert received_intent.verify(now=time.time())
        assert peer_id in node_b._connections
        assert store_b.get_intent(intent.order_id)["status"] == "pending"

        # Uma segunda propagação da mesma intent é idempotente no receptor.
        assert await node_a.broadcast_swap_intent(intent.to_dict()) == 1
        await asyncio.sleep(0.1)
        assert len(received) == 1
        engine.close()
    finally:
        await node_a.stop()
        await node_b.stop()
        store_a.close()
        store_b.close()


def test_real_tcp_two_p2pnodes_swap_intent_e2e(tmp_path):
    asyncio.run(_run_real_tcp_swap_flow(tmp_path))
