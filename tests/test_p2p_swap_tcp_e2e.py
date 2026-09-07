import asyncio
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_core.network.p2p_real.node import P2PNode
from native_processing.swap_engine import SwapEngine
from native_processing.swap_protocol import sign_quote
from native_processing.swap_sync import SwapSyncStore


async def _wait_for_intent(store, order_id: str, timeout: float = 3.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if store.get_intent(order_id) is not None:
            return
        await asyncio.sleep(0.05)
    raise AssertionError("swap intent was not synchronized over TCP")


def test_swap_intent_sync_over_real_tcp_late_join(tmp_path: Path):
    asyncio.run(_exercise_real_tcp_sync(tmp_path))


async def _exercise_real_tcp_sync(tmp_path: Path):
    engine = SwapEngine(str(tmp_path / "engine.sqlite"), quote_ttl_seconds=120)
    store_a = SwapSyncStore(str(tmp_path / "a.sqlite"), "node-a")
    store_b = SwapSyncStore(str(tmp_path / "b.sqlite"), "node-b")
    node_a = P2PNode("127.0.0.1", 0, node_id="node-a", seeds=[])
    node_b = P2PNode("127.0.0.1", 0, node_id="node-b", seeds=[])
    node_a.set_swap_sync_store(store_a)
    node_b.set_swap_sync_store(store_b)
    try:
        quote = engine.quote("sell_bait", btc_sats=250_000, bait_units=25_000_000)
        intent = sign_quote(
            quote,
            "maker-a",
            Ed25519PrivateKey.generate(),
            "late-join-regression",
            btc_deposit_address="bcrt1qswapdeposit",
            bait_recipient_pubkey=b"r" * 32,
            network="regtest",
        )
        assert store_a.admit_intent(intent, "local", "local:late-join") == "accepted"

        await node_a.start()
        await node_b.start()
        port_a = node_a._server.sockets[0].getsockname()[1]
        assert await node_b.connect_to_peer("127.0.0.1", port_a)

        await _wait_for_intent(store_b, intent.order_id)
        remote = store_b.get_intent(intent.order_id)
        assert remote is not None
        assert remote["order_id"] == intent.order_id
        assert remote["btc_sats"] == 250_000
        assert remote["bait_units"] == 25_000_000
        assert remote["network"] == "regtest"
    finally:
        await node_b.stop()
        await node_a.stop()
        store_a.close()
        store_b.close()
        engine.close()
