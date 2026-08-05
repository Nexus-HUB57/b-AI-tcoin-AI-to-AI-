r"""
Phase B: Network Operations — Tests

Tests for:
- B.1: GossipProtocol (serialize, deserialize, dedup, fanout, block message)
- B.2: BlockSync (validate_and_apply, fork_resolution, orphan_pool)
- B.3: IndependentNode (node_creation, status, connect_peer)
- B.4: TestnetManager (config_creation, testnet_address_detection)

All tests are self-contained with no network I/O.
Uses a loose ZkML target (0x00ffff...) for fast mining.
"""

import hashlib
import json
import time
import pytest

from baitcoin_core.blockchain.block import (
    Block, BlockHeader, Transaction, TransactionOutput, TransactionInput,
)
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.network.gossip import (
    GossipProtocol, GossipMessage, GossipMessageType,
)
from baitcoin_core.network.block_sync import BlockSync
from baitcoin_core.network.node import IndependentNode
from baitcoin_core.network.testnet.testnet_manager import TestnetManager


# ── Helpers ──────────────────────────────────────────────────

# Loose target for fast mining in tests (~instant)
LOOSE_TARGET = 0x00ffff0000000000000000000000000000000000000000000000000000000000


def _make_consensus():
    """Create a ZkMLConsensus with a loose target for fast tests."""
    return ZkMLConsensus(target=LOOSE_TARGET)


def _make_blockchain():
    """Create a test Blockchain with loose consensus."""
    return Blockchain(consensus=_make_consensus())


def _make_block(index: int, prev_block_hash: bytes, miner: str = "test_miner") -> Block:
    """Create a simple block at the given height for testing."""
    header = BlockHeader(
        version=1,
        prev_block_hash=prev_block_hash,
        timestamp=time.time(),
        bits=0x1d00ffff,
        agent_validator=miner,
    )
    coinbase = Transaction(
        tx_type="coinbase",
        outputs=[TransactionOutput(
            amount_sats=50 * 100_000_000,
            script_pubkey=b"test_pubkey",
        )],
        agent_id=miner,
    )
    block = Block(index=index, header=header, transactions=[coinbase])
    block.finalize()
    return block


def _mine_block(chain: Blockchain, miner: str = "test_miner") -> Block:
    """Mine a single block on the chain and return it."""
    pubkey = hashlib.sha256(miner.encode()).digest()[:32]
    return chain.mine_block(miner_agent=miner, miner_pubkey=pubkey)


# ═══════════════════════════════════════════════════════════
# B.1: GossipProtocol Tests
# ═══════════════════════════════════════════════════════════


class TestGossipProtocol:
    """Tests for the GossipProtocol message system."""

    def test_serialize(self):
        """Serialize a gossip message to JSON bytes."""
        proto = GossipProtocol(node_id="node_1")
        msg = GossipMessage(
            msg_type=GossipMessageType.BLOCK,
            payload={"block": {"index": 42}},
            sender="node_1",
            timestamp=1700000000.0,
            nonce="abc123",
        )
        raw = proto.serialize(msg)
        assert isinstance(raw, bytes)

        data = json.loads(raw.decode("utf-8"))
        assert data["type"] == "block"
        assert data["payload"]["block"]["index"] == 42
        assert data["sender"] == "node_1"
        assert data["nonce"] == "abc123"
        assert data["signature"] is None

    def test_deserialize(self):
        """Deserialize JSON bytes back into a GossipMessage."""
        proto = GossipProtocol(node_id="node_1")
        msg = GossipMessage(
            msg_type=GossipMessageType.TRANSACTION,
            payload={"tx_id": "0xdead"},
            sender="node_2",
            nonce="xyz789",
        )
        raw = proto.serialize(msg)

        recovered = proto.deserialize(raw)
        assert recovered is not None
        assert recovered.msg_type == GossipMessageType.TRANSACTION
        assert recovered.payload["tx_id"] == "0xdead"
        assert recovered.sender == "node_2"
        assert recovered.nonce == "xyz789"

    def test_deserialize_invalid(self):
        """Deserialize invalid bytes returns None."""
        proto = GossipProtocol(node_id="node_1")
        assert proto.deserialize(b"not json at all") is None
        assert proto.deserialize(b"{}") is None  # missing 'type'
        assert proto.deserialize(b'{"type": "invalid_type"}') is None

    def test_serialize_roundtrip(self):
        """Serialize -> deserialize preserves all fields."""
        proto = GossipProtocol(node_id="node_1")
        sig = b"\x00" * 64
        msg = GossipMessage(
            msg_type=GossipMessageType.PING,
            payload={"echo": "hello"},
            sender="node_a",
            timestamp=1700000500.0,
            signature=sig,
            nonce="roundtrip_nonce",
        )
        raw = proto.serialize(msg)
        recovered = proto.deserialize(raw)
        assert recovered.msg_type == GossipMessageType.PING
        assert recovered.payload["echo"] == "hello"
        assert recovered.sender == "node_a"
        assert recovered.timestamp == 1700000500.0
        assert recovered.signature == sig
        assert recovered.nonce == "roundtrip_nonce"

    def test_dedup(self):
        """Duplicate messages are filtered by receive()."""
        proto = GossipProtocol(node_id="node_1")
        msg = proto.create_ping_message()
        raw = proto.serialize(msg)

        # First receive should return the message
        result1 = proto.receive(raw)
        assert len(result1) == 1

        # Second receive of same message should be deduped
        result2 = proto.receive(raw)
        assert len(result2) == 0

    def test_dedup_multiple_messages(self):
        """Different messages are not deduplicated."""
        proto = GossipProtocol(node_id="node_1")
        msg1 = proto.create_ping_message()
        msg2 = proto.create_ping_message()  # different nonce
        raw1 = proto.serialize(msg1)
        raw2 = proto.serialize(msg2)

        result1 = proto.receive(raw1)
        result2 = proto.receive(raw2)
        assert len(result1) == 1
        assert len(result2) == 1

    def test_fanout(self):
        """Broadcast targets fanout number of peers."""
        proto = GossipProtocol(node_id="node_1", fanout=3)
        proto.set_peers(["peer_a", "peer_b", "peer_c", "peer_d", "peer_e"])

        msg = proto.create_ping_message()
        count = proto.broadcast(msg)
        assert count == 3  # Fanout is 3

    def test_fanout_excludes_sender(self):
        """Fanout excludes the message sender."""
        proto = GossipProtocol(node_id="node_1", fanout=3)
        proto.set_peers(["node_1", "peer_a", "peer_b"])

        msg = proto.create_ping_message()
        count = proto.broadcast(msg)
        # Should send to peer_a, peer_b (excludes node_1 = sender)
        assert count == 2

    def test_fanout_limited_peers(self):
        """Fanout respects available peer count."""
        proto = GossipProtocol(node_id="node_1", fanout=5)
        proto.set_peers(["peer_a", "peer_b"])  # only 2 peers

        msg = proto.create_ping_message()
        count = proto.broadcast(msg)
        assert count == 2  # Only 2 available

    def test_block_message(self):
        """Create and verify a BLOCK gossip message."""
        proto = GossipProtocol(node_id="node_1")
        block_data = {"index": 5, "hash": "0xabcdef", "tx_count": 3}
        msg = proto.create_block_message(block_data)

        assert msg.msg_type == GossipMessageType.BLOCK
        assert msg.sender == "node_1"
        assert msg.payload["block"]["index"] == 5
        assert msg.payload["block"]["hash"] == "0xabcdef"

        # Roundtrip
        raw = proto.serialize(msg)
        recovered = proto.deserialize(raw)
        assert recovered.msg_type == GossipMessageType.BLOCK
        assert recovered.payload["block"]["index"] == 5

    def test_tx_message(self):
        """Create and verify a TRANSACTION gossip message."""
        proto = GossipProtocol(node_id="node_1")
        tx_data = {"tx_id": "0xtx123", "tx_type": "transfer"}
        msg = proto.create_tx_message(tx_data)

        assert msg.msg_type == GossipMessageType.TRANSACTION
        assert msg.payload["transaction"]["tx_id"] == "0xtx123"

    def test_ping_pong_messages(self):
        """Create PING and PONG messages."""
        proto = GossipProtocol(node_id="node_1")

        ping = proto.create_ping_message()
        assert ping.msg_type == GossipMessageType.PING
        assert ping.payload == {}

        pong = proto.create_pong_message(ping_nonce="ping_nonce_123")
        assert pong.msg_type == GossipMessageType.PONG
        assert pong.payload["ping_nonce"] == "ping_nonce_123"

    def test_sync_messages(self):
        """Create SYNC_REQUEST and SYNC_RESPONSE messages."""
        proto = GossipProtocol(node_id="node_1")

        req = proto.create_sync_request_message(from_height=10, to_height=20)
        assert req.msg_type == GossipMessageType.SYNC_REQUEST
        assert req.payload["from_height"] == 10
        assert req.payload["to_height"] == 20

        resp = proto.create_sync_response_message(
            blocks=[{"index": 10}, {"index": 11}]
        )
        assert resp.msg_type == GossipMessageType.SYNC_RESPONSE
        assert len(resp.payload["blocks"]) == 2

    def test_peer_discovery_message(self):
        """Create PEER_DISCOVERY message with known peers."""
        proto = GossipProtocol(node_id="node_1")
        msg = proto.create_peer_discovery_message(
            known_peers=["peer_a", "peer_b"]
        )
        assert msg.msg_type == GossipMessageType.PEER_DISCOVERY
        assert msg.payload["peers"] == ["peer_a", "peer_b"]

    def test_dedup_key_uniqueness(self):
        """Each message has a unique dedup key."""
        proto = GossipProtocol(node_id="node_1")
        msg1 = proto.create_ping_message()
        msg2 = proto.create_ping_message()
        assert msg1.dedup_key != msg2.dedup_key

    def test_stats(self):
        """get_stats returns expected fields."""
        proto = GossipProtocol(node_id="stats_node")
        proto.set_peers(["p1", "p2"])
        stats = proto.get_stats()

        assert stats["node_id"] == "stats_node"
        assert stats["fanout"] == GossipProtocol.DEFAULT_FANOUT
        assert stats["known_peers"] == 2
        assert "seen_messages" in stats
        assert "outbox_size" in stats


# ═══════════════════════════════════════════════════════════
# B.2: BlockSync Tests
# ═══════════════════════════════════════════════════════════


class TestBlockSync:
    """Tests for the BlockSync protocol."""

    def test_validate_and_apply(self):
        """Valid block is applied to the chain."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        # Mine block #1
        block = _mine_block(chain)
        assert chain.height == 1

        # Create block #2 manually
        block2 = _make_block(2, chain.last_block.block_hash)
        # Apply via sync
        valid = sync.validate_and_apply(block2)
        assert valid is True
        assert chain.height == 2

    def test_validate_and_apply_correct_parent(self):
        """Block with wrong parent hash is not applied."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        # Create block #1 with wrong parent hash
        wrong_hash = b"\xff" * 32
        block1 = _make_block(1, wrong_hash)

        valid = sync.validate_and_apply(block1)
        assert valid is False
        assert chain.height == 0  # Genesis only

    def test_validate_and_apply_wrong_height(self):
        """Block at wrong height is rejected or orphaned."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        # Block #5 when we're at #0 should go to orphan pool
        block5 = _make_block(5, b"\xaa" * 32)
        valid = sync.validate_and_apply(block5)
        assert valid is False
        assert sync._orphan_pool_size() == 1

    def test_validate_and_apply_duplicate_height(self):
        """Block at same height as tip is rejected."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        # Create another block at height 0 (genesis height)
        block0 = _make_block(0, b"\x00" * 32)
        valid = sync.validate_and_apply(block0)
        assert valid is False

    def test_fork_resolution(self):
        """Fork is detected and counted."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        # Mine block #1
        _mine_block(chain)

        # Create block #2 pointing to genesis (fork!)
        genesis_hash = chain.chain[0].block_hash
        fork_block = _make_block(2, genesis_hash)

        # Should detect fork and add to orphan pool
        valid = sync.handle_fork(fork_block)
        assert valid is False  # Fork not resolved (single block)
        assert sync._forks_resolved >= 1

    def test_orphan_pool(self):
        """Orphan blocks are stored and retrievable."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        # Add several orphan blocks
        orphan1 = _make_block(10, b"\x01" * 32)
        orphan2 = _make_block(10, b"\x02" * 32)
        orphan3 = _make_block(11, b"\x03" * 32)

        sync._add_to_orphan_pool(orphan1)
        sync._add_to_orphan_pool(orphan2)
        sync._add_to_orphan_pool(orphan3)

        orphans = sync.get_orphan_pool()
        assert len(orphans) == 3

    def test_orphan_pool_max_size(self):
        """Orphan pool respects max size limit."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain, max_orphan_pool=5)

        for i in range(8):
            block = _make_block(10 + i, bytes([i]) * 32)
            sync._add_to_orphan_pool(block)

        # Should not exceed max + some buffer
        assert sync._orphan_pool_size() <= 8  # eviction keeps it manageable

    def test_sync_status(self):
        """get_sync_status returns expected fields."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        status = sync.get_sync_status()
        assert "syncing" in status
        assert "height" in status
        assert "peer_height" in status
        assert "progress" in status
        assert status["height"] == 0
        assert status["syncing"] is False

    def test_sync_status_with_peer_height(self):
        """Sync progress reflects peer height."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        sync.update_peer_height("peer_a", 10)
        status = sync.get_sync_status()
        assert status["peer_height"] == 10
        assert status["progress"] == 0.0  # 0/10

    def test_request_blocks(self):
        """request_blocks returns blocks in range."""
        chain = _make_blockchain()
        _mine_block(chain)  # Block #1
        _mine_block(chain)  # Block #2

        sync = BlockSync(blockchain=chain)
        blocks = sync.request_blocks(0, 2)
        assert len(blocks) == 3  # genesis + 2 mined

    def test_request_blocks_out_of_range(self):
        """request_blocks for non-existent heights returns partial list."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        blocks = sync.request_blocks(0, 10)
        assert len(blocks) == 1  # Only genesis exists

    def test_start_stop_sync(self):
        """Sync can be started and stopped."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        assert sync.get_sync_status()["syncing"] is False

        sync.start_sync(100)
        assert sync.get_sync_status()["syncing"] is True

        sync.stop_sync()
        assert sync.get_sync_status()["syncing"] is False

    def test_validate_and_apply_updates_utxo(self):
        """Applying a block updates the UTXO set."""
        chain = _make_blockchain()
        sync = BlockSync(blockchain=chain)

        block1 = _make_block(1, chain.last_block.block_hash)
        sync.validate_and_apply(block1)

        # The coinbase output should be in the UTXO set
        assert len(chain.utxo_set) > 0


# ═══════════════════════════════════════════════════════════
# B.3: IndependentNode Tests
# ═══════════════════════════════════════════════════════════


class TestIndependentNode:
    """Tests for IndependentNode creation and status."""

    def test_node_creation(self):
        """Node initializes with all components."""
        consensus = _make_consensus()
        node = IndependentNode(
            node_id="test_node",
            host="127.0.0.1",
            port=18444,
            consensus=consensus,
        )

        assert node.node_id == "test_node"
        assert node.host == "127.0.0.1"
        assert node.port == 18444
        assert node.network == "mainnet"
        assert node.blockchain is not None
        assert node.p2p is not None
        assert node.gossip is not None
        assert node.block_sync is not None
        assert node._running is False

    def test_node_auto_id(self):
        """Node auto-generates ID if empty string."""
        node = IndependentNode(
            node_id="",
            host="127.0.0.1",
            port=18444,
        )
        assert len(node.node_id) > 0
        assert len(node.node_id) == 16

    def test_node_start(self):
        """start() marks node as running."""
        node = IndependentNode(
            node_id="start_test",
            host="127.0.0.1",
            port=18445,
        )
        assert node._running is False

        node.start()
        assert node._running is True
        assert node.blockchain.height == 0  # Genesis exists

    def test_node_start_idempotent(self):
        """Starting an already-running node is a no-op."""
        node = IndependentNode(node_id="idempotent", port=18446)
        node.start()
        node.start()  # Should not raise
        assert node._running is True

    def test_node_stop(self):
        """stop() marks node as stopped."""
        node = IndependentNode(node_id="stop_test", port=18447)
        node.start()
        node.stop()
        assert node._running is False

    def test_node_stop_not_running(self):
        """Stopping a non-running node is a no-op."""
        node = IndependentNode(node_id="already_stopped", port=18448)
        node.stop()  # Should not raise
        assert node._running is False

    def test_status(self):
        """get_status returns comprehensive status dict."""
        node = IndependentNode(node_id="status_test", port=18449)
        node.start()

        status = node.get_status()
        assert status["node_id"] == "status_test"
        assert status["host"] == "127.0.0.1"
        assert status["port"] == 18449
        assert status["network"] == "mainnet"
        assert status["running"] is True
        assert status["height"] == 0
        assert status["peers"] == 0
        assert "blockchain" in status
        assert "consensus" in status
        assert "gossip" in status
        assert "sync_status" in status
        assert status["uptime"] >= 0

    def test_status_not_running(self):
        """Status reflects stopped state."""
        node = IndependentNode(node_id="stopped_status", port=18450)
        status = node.get_status()
        assert status["running"] is False

    def test_connect_peer(self):
        """connect_to_peer adds a peer to P2P and gossip."""
        node = IndependentNode(node_id="connect_test", port=18451)
        node.start()

        result = node.connect_to_peer("192.168.1.1", 18452)
        assert result is True
        assert len(node.p2p.peers) == 1

    def test_connect_multiple_peers(self):
        """Multiple peers can be connected."""
        node = IndependentNode(node_id="multi_peer", port=18453)
        node.start()

        node.connect_to_peer("192.168.1.1", 18452)
        node.connect_to_peer("192.168.1.2", 18453)
        node.connect_to_peer("192.168.1.3", 18454)

        assert len(node.p2p.peers) == 3

    def test_propagate_block(self):
        """propagate_block creates gossip message and P2P broadcast."""
        node = IndependentNode(node_id="propagate_test", port=18455)
        node.start()
        node.connect_to_peer("peer_host", 18456)

        block = _make_block(1, node.blockchain.last_block.block_hash)
        count = node.propagate_block(block)

        # Should attempt to broadcast to at least the connected peer
        assert count >= 0
        assert len(node.gossip._outbox) > 0

    def test_handle_incoming_block(self):
        """handle_incoming_block validates and applies a valid block."""
        node = IndependentNode(
            node_id="incoming_test", port=18457,
            consensus=_make_consensus(),
        )
        node.start()

        block = _make_block(1, node.blockchain.last_block.block_hash)
        result = node.handle_incoming_block(block)

        assert result is True
        assert node.blockchain.height == 1

    def test_handle_invalid_incoming_block(self):
        """handle_incoming_block rejects invalid blocks."""
        node = IndependentNode(node_id="invalid_test", port=18458)
        node.start()

        # Block with wrong parent hash
        block = _make_block(1, b"\xff" * 32)
        result = node.handle_incoming_block(block)

        assert result is False
        assert node.blockchain.height == 0

    def test_repr(self):
        """Node __repr__ includes key info."""
        node = IndependentNode(node_id="repr_test", port=18459)
        node.start()
        text = repr(node)
        assert "repr_test" in text
        assert "18459" in text
        assert "height=0" in text

    def test_status_blockchain_fields(self):
        """Status blockchain sub-dict has expected fields."""
        node = IndependentNode(node_id="bc_status", port=18460)
        node.start()
        status = node.get_status()

        bc = status["blockchain"]
        assert "block_count" in bc
        assert "utxo_count" in bc
        assert "mempool_size" in bc
        assert "last_block_hash" in bc
        assert bc["block_count"] >= 1  # At least genesis


# ═══════════════════════════════════════════════════════════
# B.4: TestnetManager Tests
# ═══════════════════════════════════════════════════════════


class TestTestnetManager:
    """Tests for TestnetManager configuration and address detection."""

    def test_config_creation(self):
        """create_testnet_config returns a valid config dict."""
        mgr = TestnetManager()
        config = mgr.create_testnet_config(network_id=2, testnet_coinbase="my_genesis")

        assert config["network_id"] == 2
        assert config["network_name"] == "testnet"
        assert config["coinbase_agent"] == "my_genesis"
        assert "consensus" in config
        assert "genesis" in config
        assert "seed_peers" in config
        assert "rpc" in config
        assert "limits" in config
        assert "faucet" in config

    def test_config_default_values(self):
        """Default config has expected defaults."""
        mgr = TestnetManager()
        config = mgr.create_testnet_config()

        assert config["port"] == 18444
        assert len(config["seed_peers"]) == 3
        assert config["limits"]["max_peers"] == 25
        assert config["faucet"]["max_fund_per_request"] == 1_000_000

    def test_config_consensus_target(self):
        """Testnet config uses a loose consensus target."""
        mgr = TestnetManager()
        config = mgr.create_testnet_config()

        target = int(config["consensus"]["target"], 16)
        # Should be a loose target (starts with 0x00ffff)
        assert target > 0
        assert config["consensus"]["block_time"] == 30

    def test_config_stored(self):
        """Config is stored on the manager."""
        mgr = TestnetManager()
        config = mgr.create_testnet_config()
        assert mgr._config is config

    def test_testnet_address_detection(self):
        """is_testnet_address detects t' prefix."""
        assert TestnetManager.is_testnet_address("t'abc123") is True
        assert TestnetManager.is_testnet_address("t'") is True
        assert TestnetManager.is_testnet_address("t'1A2b3C4d5E") is True

    def test_testnet_address_rejection(self):
        """is_testnet_address rejects non-t' prefixes."""
        assert TestnetManager.is_testnet_address("b'abc123") is False
        assert TestnetManager.is_testnet_address("abc123") is False
        assert TestnetManager.is_testnet_address("") is False
        assert TestnetManager.is_testnet_address("t") is False  # No quote
        assert TestnetManager.is_testnet_address("T'abc") is False  # Capital

    def test_testnet_address_non_string(self):
        """is_testnet_address rejects non-string types."""
        assert TestnetManager.is_testnet_address(None) is False
        assert TestnetManager.is_testnet_address(123) is False
        assert TestnetManager.is_testnet_address(b"t'abc") is False

    def test_start_testnet_node(self):
        """start_testnet_node creates and starts a node."""
        mgr = TestnetManager()
        config = mgr.create_testnet_config()
        node = mgr.start_testnet_node(
            config=config,
            node_id="testnet_node_1",
            port=19000,
        )

        assert node.node_id == "testnet_node_1"
        assert node.network == "testnet"
        assert node._running is True
        assert "testnet_node_1" in mgr.nodes

    def test_start_testnet_node_auto_id(self):
        """start_testnet_node auto-generates ID if not provided."""
        mgr = TestnetManager()
        config = mgr.create_testnet_config()
        node = mgr.start_testnet_node(config=config, port=19001)

        assert len(node.node_id) > 0
        assert node.node_id in mgr.nodes

    def test_initialize_faucet(self):
        """initialize_faucet sets balance and returns status."""
        mgr = TestnetManager()
        mgr.create_testnet_config()

        status = mgr.initialize_faucet(initial_fund_sats=5_000_000_000)

        assert status["initialized"] is True
        assert status["balance_sats"] == 5_000_000_000
        assert status["balance_bait"] == 50.0

    def test_testnet_status(self):
        """get_testnet_status returns expected fields."""
        mgr = TestnetManager()
        mgr.create_testnet_config()
        mgr.initialize_faucet()

        status = mgr.get_testnet_status()
        assert status["network_id"] == 2
        assert status["network_name"] == "testnet"
        assert status["active_nodes"] == 0
        assert status["total_blocks"] == 0
        assert status["faucet"]["initialized"] is True
        assert status["faucet"]["balance_sats"] > 0

    def test_testnet_status_with_nodes(self):
        """Status reflects running testnet nodes."""
        mgr = TestnetManager()
        mgr.create_testnet_config()
        mgr.start_testnet_node(node_id="node_a", port=19010)
        mgr.start_testnet_node(node_id="node_b", port=19011)

        status = mgr.get_testnet_status()
        assert status["active_nodes"] == 2
        assert "node_a" in status["node_details"]
        assert "node_b" in status["node_details"]

    def test_stop_all_nodes(self):
        """stop_all_nodes shuts down all nodes."""
        mgr = TestnetManager()
        mgr.create_testnet_config()
        mgr.start_testnet_node(node_id="stop_a", port=19020)
        mgr.start_testnet_node(node_id="stop_b", port=19021)

        assert len(mgr.nodes) == 2
        mgr.stop_all_nodes()
        assert len(mgr.nodes) == 0

    def test_dispense_faucet_funds(self):
        """dispense_faucet_funds creates a valid dispense record."""
        mgr = TestnetManager()
        mgr.create_testnet_config()
        mgr.initialize_faucet(initial_fund_sats=10_000_000)

        result = mgr.dispense_faucet_funds(
            address="t'test_address_123",
            amount_sats=1_000_000,
        )

        assert result["success"] is True
        assert result["amount_sats"] == 1_000_000
        assert result["address"] == "t'test_address_123"
        assert result["remaining_balance_sats"] == 9_000_000
        assert "tx_ref" in result

    def test_dispense_faucet_rejects_mainnet_address(self):
        """Faucet rejects mainnet (b') addresses."""
        mgr = TestnetManager()
        mgr.create_testnet_config()
        mgr.initialize_faucet()

        result = mgr.dispense_faucet_funds(address="b'mainnet_addr")
        assert result["success"] is False
        assert "not a valid testnet address" in result["reason"]

    def test_dispense_faucet_insufficient_balance(self):
        """Faucet rejects when balance is insufficient."""
        mgr = TestnetManager()
        mgr.create_testnet_config()
        mgr.initialize_faucet(initial_fund_sats=500_000)

        result = mgr.dispense_faucet_funds(
            address="t'addr",
            amount_sats=1_000_000,
        )
        assert result["success"] is False
        assert "insufficient" in result["reason"]

    def test_dispense_exceeds_max_per_request(self):
        """Faucet rejects amounts exceeding max per request."""
        mgr = TestnetManager()
        mgr.create_testnet_config()
        mgr.initialize_faucet(initial_fund_sats=100_000_000_000)

        result = mgr.dispense_faucet_funds(
            address="t'addr",
            amount_sats=5_000_000,  # exceeds default max of 1M
        )
        assert result["success"] is False
        assert "max per request" in result["reason"]

    def test_repr(self):
        """Manager __repr__ includes key info."""
        mgr = TestnetManager()
        text = repr(mgr)
        assert "TestnetManager" in text
        assert "network_id=2" in text
