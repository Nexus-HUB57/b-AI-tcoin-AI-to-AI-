r"""
Independent Node for b'AI'tcoin — Standalone full-node network operation.

Wraps a full Blockchain instance + P2P network layer into a single
independent node that can mine, listen for peers, propagate blocks,
and synchronize chain state.

Usage::

    node = IndependentNode(node_id="alpha", host="127.0.0.1", port=18444)
    node.start()
    status = node.get_status()
    node.connect_to_peer("127.0.0.1", 18445)
    node.stop()
"""

import asyncio
import hashlib
import logging
import os
import time
from typing import Dict, List, Optional, Any

from baitcoin_core.blockchain.block import Block
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.network.p2p import P2PNetwork, MessageType
from baitcoin_core.network.gossip import GossipProtocol, GossipMessage
from baitcoin_core.network.block_sync import BlockSync

logger = logging.getLogger(__name__)


class IndependentNode:
    """A standalone b'AI'tcoin full node.

    Combines a Blockchain, P2P network, gossip protocol, and block
    synchronizer into a single operational unit. Supports concurrent
    operations via asyncio.

    Args:
        node_id: Unique identifier for this node. Auto-generated if empty.
        host: Host address to listen on.
        port: Port to listen on.
        network: Network name ('mainnet' or 'testnet').
        data_path: Optional filesystem path for persistent storage.
        consensus: Optional pre-configured ZkMLConsensus instance.
    """

    def __init__(
        self,
        node_id: str,
        host: str = "127.0.0.1",
        port: int = 18444,
        network: str = "mainnet",
        data_path: Optional[str] = None,
        consensus: Optional[ZkMLConsensus] = None,
    ):
        self.node_id = node_id or hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        self.host = host
        self.port = port
        self.network = network
        self.data_path = data_path

        # Core components
        self.consensus = consensus or ZkMLConsensus()
        self.blockchain = Blockchain(consensus=self.consensus)
        self.p2p = P2PNetwork(node_id=self.node_id, listen_port=port)
        self.gossip = GossipProtocol(node_id=self.node_id)
        self.block_sync = BlockSync(blockchain=self.blockchain)

        # State
        self._running: bool = False
        self._tasks: List[asyncio.Task] = []
        self._start_time: Optional[float] = None

        # Register gossip peer tracking with P2P
        self._sync_gossip_peers()

        logger.info(
            "Initialized node %s on %s:%d (%s)",
            self.node_id, self.host, self.port, self.network,
        )

    # ── Lifecycle ─────────────────────────────────────────────

    def start(self) -> None:
        """Start the blockchain node.

        Ensures genesis block exists, begins listening for peers,
        and starts periodic tasks (gossip maintenance, sync checks).
        """
        if self._running:
            logger.warning("Node %s is already running", self.node_id)
            return

        self._running = True
        self._start_time = time.time()

        # Genesis block is always created by Blockchain.__init__
        logger.info(
            "Node %s started — chain height %d",
            self.node_id, self.blockchain.height,
        )

    async def start_async(self) -> None:
        """Async start with background tasks.

        Starts the node and launches periodic maintenance tasks.
        """
        self.start()
        self._tasks = [
            asyncio.create_task(self._periodic_gossip_sync(), name="gossip_sync"),
            asyncio.create_task(self._periodic_peer_check(), name="peer_check"),
        ]

    def stop(self) -> None:
        """Gracefully shut down the node.

        Cancels all background tasks and marks the node as stopped.
        """
        if not self._running:
            return

        self._running = False

        # Cancel asyncio tasks if running in async context
        for task in self._tasks:
            if not task.done():
                task.cancel()

        self._tasks.clear()

        logger.info(
            "Node %s stopped — final height %d, uptime %.1fs",
            self.node_id,
            self.blockchain.height,
            time.time() - (self._start_time or time.time()),
        )

    async def stop_async(self) -> None:
        """Async graceful shutdown with task cleanup."""
        self.stop()
        # Wait for tasks to complete cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

    # ── Peer Management ────────────────────────────────────────

    def connect_to_peer(self, host: str, port: int) -> bool:
        """Connect to another node on the network.

        Args:
            host: Peer host address.
            port: Peer port.

        Returns:
            True if the peer was added successfully.
        """
        success = self.p2p.add_peer(address=host, port=port)
        if success:
            peer_id = self._peer_id_from_addr(host, port)
            self.gossip.add_peer(peer_id)
            self._send_hello(host, port)
            logger.info(
                "Node %s connected to peer %s:%d",
                self.node_id, host, port,
            )
        return success

    def _peer_id_from_addr(self, host: str, port: int) -> str:
        """Derive a peer ID from host:port."""
        return hashlib.sha256(f"{host}:{port}".encode()).hexdigest()[:16]

    def _send_hello(self, host: str, port: int) -> None:
        """Send a HELLO handshake message to a new peer."""
        self.p2p.broadcast(
            MessageType.HELLO,
            {
                "node_id": self.node_id,
                "version": P2PNetwork.PROTOCOL_VERSION,
                "height": self.blockchain.height,
                "network": self.network,
            },
        )

    def _sync_gossip_peers(self) -> None:
        """Sync gossip peer list with P2P peer list."""
        peer_ids = list(self.p2p.peers.keys())
        self.gossip.set_peers(peer_ids)

    # ── Status ────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return comprehensive node status.

        Returns:
            Dict with keys: node_id, host, port, network, running,
            height, peers, sync_status, uptime, blockchain_info,
            consensus_info, gossip_stats.
        """
        uptime = 0.0
        if self._start_time and self._running:
            uptime = time.time() - self._start_time

        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "network": self.network,
            "running": self._running,
            "height": self.blockchain.height,
            "peers": len(self.p2p.peers),
            "sync_status": self.block_sync.get_sync_status(),
            "uptime": uptime,
            "blockchain": {
                "block_count": len(self.blockchain.chain),
                "utxo_count": len(self.blockchain.utxo_set),
                "mempool_size": self.blockchain.fee_market.size,
                "last_block_hash": self.blockchain.last_block.block_hash.hex(),
            },
            "consensus": self.consensus.to_dict(),
            "gossip": self.gossip.get_stats(),
            "p2p": self.p2p.get_stats(),
        }

    # ── Block Propagation ─────────────────────────────────────

    def propagate_block(self, block: Block) -> int:
        """Propagate a block to all peers via the gossip protocol.

        Serializes the block and broadcasts it as a gossip BLOCK message.

        Args:
            block: The Block to propagate.

        Returns:
            Number of peers the message was sent to.
        """
        msg = self.gossip.create_block_message(block.to_dict())
        raw = self.gossip.serialize(msg)

        # Also broadcast via P2P
        self.p2p.broadcast(
            MessageType.BLOCK,
            {"block_data": block.to_dict()},
        )

        return self.gossip.broadcast(msg)

    def handle_incoming_block(self, block: Block) -> bool:
        """Validate and add a block received from a peer.

        Uses the BlockSync protocol to validate, apply, and handle
        potential forks or orphans.

        Args:
            block: The incoming Block from a peer.

        Returns:
            True if the block was accepted and applied.
        """
        logger.info(
            "Node %s: handling incoming block at height %d",
            self.node_id, block.index,
        )

        # Validate and apply via BlockSync
        valid = self.block_sync.validate_and_apply(block)

        if valid:
            # Propagate to other peers
            self.propagate_block(block)

        return valid

    # ── Chain Synchronization ─────────────────────────────────

    def sync_chain(self, peer_id: str) -> int:
        """Request missing blocks from a specific peer.

        Calculates the range of blocks needed and requests them.

        Args:
            peer_id: The peer to sync from.

        Returns:
            Number of blocks requested.
        """
        our_height = self.blockchain.height
        peer_height = self.block_sync._peer_heights.get(peer_id, our_height)

        if peer_height <= our_height:
            logger.info(
                "Node %s: already synced with peer %s",
                self.node_id, peer_id,
            )
            return 0

        self.block_sync.start_sync(peer_height)

        # Request blocks in batches
        batch_size = 50
        total_requested = 0
        from_height = our_height + 1

        while from_height <= peer_height:
            to_height = min(from_height + batch_size - 1, peer_height)
            blocks = self.block_sync.request_blocks(
                from_height, to_height, peer_id
            )
            total_requested += len(blocks)

            for block in blocks:
                self.handle_incoming_block(block)

            from_height = to_height + 1

        self.block_sync.stop_sync()

        logger.info(
            "Node %s: synced %d blocks from peer %s",
            self.node_id, total_requested, peer_id,
        )
        return total_requested

    # ── Periodic Tasks ───────────────────────────────────────

    async def _periodic_gossip_sync(self) -> None:
        """Periodically sync gossip peer list with P2P peers."""
        while self._running:
            try:
                self._sync_gossip_peers()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Gossip sync error: %s", exc)
                await asyncio.sleep(5)

    async def _periodic_peer_check(self) -> None:
        """Periodically check peer liveness via PING."""
        while self._running:
            try:
                if self.p2p.peers:
                    self.p2p.broadcast(MessageType.PING, {"nonce": time.time()})
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Peer check error: %s", exc)
                await asyncio.sleep(10)

    # ── Representation ────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"IndependentNode(id={self.node_id}, "
            f"addr={self.host}:{self.port}, "
            f"height={self.blockchain.height}, "
            f"peers={len(self.p2p.peers)})"
        )
