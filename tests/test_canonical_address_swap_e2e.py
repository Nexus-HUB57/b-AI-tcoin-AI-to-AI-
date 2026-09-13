import asyncio
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_core.blockchain.addresses import BAITAddress, validate_address
from baitcoin_core.network.p2p_real.node import P2PNode
from baitcoin_sdk.wallet_sdk import AgentWalletSDK
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


async def _run_canonical_swap_flow(tmp_path):
    wallet = AgentWalletSDK(object()).create("maker-canonical")
    assert wallet.address.startswith("b'1")
    assert validate_address(wallet.address)
    parsed = BAITAddress.parse(wallet.address)
    assert parsed.network == "mainnet"

    node_a = P2PNode(host="127.0.0.1", port=0, node_id="canonical-a", seeds=[])
    node_b = P2PNode(host="127.0.0.1", port=0, node_id="canonical-b", seeds=[])
    store_a = SwapSyncStore(str(tmp_path / "canonical-a.sqlite3"), "canonical-a")
    store_b = SwapSyncStore(str(tmp_path / "canonical-b.sqlite3"), "canonical-b")
    node_a.set_swap_sync_store(store_a)
    node_b.set_swap_sync_store(store_b)
    received = []
    node_b.on_swap_intent_received(lambda intent, peer_id: received.append((intent, peer_id)))
    engine = SwapEngine(":memory:", quote_ttl_seconds=30)
    private_key = Ed25519PrivateKey.generate()

    try:
        await node_a.start()
        await node_b.start()
        port_a = node_a._server.sockets[0].getsockname()[1]
        assert await node_b.connect_to_peer("127.0.0.1", port_a)
        await _wait_until(lambda: node_a._peer_versions and node_b._peer_versions)

        now = time.time()
        quote = engine.quote("buy_bait", btc_sats=100_000, bait_units=2_000_000, now=now)
        intent = sign_quote(
            quote,
            maker_id=wallet.address,
            private_key=private_key,
            client_order_id="canonical-client-1",
            now=now,
        )
        assert intent.verify(now=now)
        assert store_a.admit_intent(intent, "local", "canonical-local", now=now) == "accepted"

        assert await node_a.broadcast_swap_intent(intent.to_dict()) == 1
        await _wait_until(lambda: len(received) == 1)

        received_intent, peer_id = received[0]
        assert peer_id in node_b._connections
        assert received_intent.order_id == intent.order_id
        assert received_intent.maker_id == wallet.address
        assert validate_address(received_intent.maker_id)
        assert store_b.get_intent(intent.order_id)["status"] == "pending"

        # Reenvio do mesmo envelope não cria segunda aceitação econômica.
        assert await node_a.broadcast_swap_intent(intent.to_dict()) == 1
        await asyncio.sleep(0.1)
        assert len(received) == 1
        assert store_b.get_intent(intent.order_id)["status"] == "pending"
    finally:
        await node_a.stop()
        await node_b.stop()
        store_a.close()
        store_b.close()
        engine.close()


def test_canonical_address_decentralized_swap_e2e(tmp_path):
    asyncio.run(_run_canonical_swap_flow(tmp_path))
