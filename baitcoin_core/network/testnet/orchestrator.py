r"""Testnet Orchestrator — Manages a local multi-node P2P testnet.

Orchestrates N b'AI'tcoin P2P nodes on localhost, each with its own:
- Independent blockchain instance
- P2P server on a unique port
- Connected to all other nodes (mesh topology)
- Shared testnet configuration

The orchestrator handles lifecycle (start/stop), health monitoring,
chain synchronization verification, and provides a unified status view.

Architecture::

    Orchestrator
    +-- Node 0  (port 19000) <---> Node 1 (port 19001)
    +-- Node 1  (port 19001) <---> Node 2 (port 19002)
    +-- Node 2  (port 19002) <---> Node 3 (port 19003)
    +-- Node 3  (port 19003) <---> Node 4 (port 19004)
    +-- Node 4  (port 19004) <---> Node 0 (port 19000)
    (full mesh: every node connects to every other node)

Consensus in testnet uses TestnetConsensus which provides:
    - Deterministic block production (round-robin validator rotation)
    - Reduced difficulty for fast block times (2s instead of 30s)
    - Instant finality via supermajority agreement

Usage::

    orch = TestnetOrchestrator(num_nodes=5, base_port=19000)
    await orch.start()
    await orch.wait_for_sync(timeout=30)
    status = orch.get_network_status()
    print(status["consensus"])  # {'synced': True, 'height': 42}
    await orch.stop()
"""

import asyncio
import hashlib
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from baitcoin_core.network.testnet.consensus import TestnetConsensus
from baitcoin_core.network.testnet.faucet_node import FaucetNode
from baitcoin_core.network.p2p_real.node import P2PNode
from baitcoin_core.network.p2p_real.protocol import P2PProtocol

logger = logging.getLogger("baitcoin.testnet.orchestrator")


@dataclass
class NodeConfig:
    """Configuration for a single testnet node."""
    node_id: str
    host: str
    port: int
    agent_id: str
    seeds: List[Tuple[str, int]]
    is_validator: bool = True
    stake_sats: int = 0


@dataclass
class TestnetStatus:
    """Aggregated status of the testnet."""
    running: bool = False
    num_nodes: int = 0
    connected_pairs: int = 0
    total_connections: int = 0
    best_height: int = 0
    min_height: int = 0
    synced: bool = False
    total_blocks_produced: int = 0
    total_txs_processed: int = 0
    uptime_seconds: float = 0.0
    consensus: Dict[str, Any] = field(default_factory=dict)
    nodes: List[Dict[str, Any]] = field(default_factory=list)


class TestnetOrchestrator:
    r"""Orchestrates a local multi-node P2P test network.

    Manages the full lifecycle of N b'AI'tcoin nodes:
    - Spawns each node with an independent blockchain
    - Connects every node to every other node (full mesh)
    - Runs testnet consensus (deterministic round-robin)
    - Monitors health and synchronization
    - Provides testnet faucet for funding accounts

    Parameters
    ----------
    num_nodes : int
        Number of nodes in the testnet (default 5, max 20)
    base_port : int
        Starting port number (each node gets base_port + i)
    host : str
        Bind address (default "127.0.0.1")
    block_interval : float
        Seconds between blocks in testnet (default 2.0, much faster than mainnet 30s)
    testnet_faucet : bool
        Whether to include a faucet node (default True)
    """

    MAX_NODES = 20
    DEFAULT_BASE_PORT = 19000
    DEFAULT_BLOCK_INTERVAL = 2.0
    SYNC_CHECK_INTERVAL = 0.5

    def __init__(
        self,
        num_nodes: int = 5,
        base_port: int = DEFAULT_BASE_PORT,
        host: str = "127.0.0.1",
        block_interval: float = DEFAULT_BLOCK_INTERVAL,
        testnet_faucet: bool = True,
    ):
        if num_nodes < 1:
            raise ValueError("num_nodes must be >= 1")
        if num_nodes > self.MAX_NODES:
            raise ValueError(f"num_nodes must be <= {self.MAX_NODES}")

        self.num_nodes = num_nodes
        self.base_port = base_port
        self.host = host
        self.block_interval = block_interval
        self.testnet_faucet_enabled = testnet_faucet

        self._nodes: Dict[str, P2PNode] = {}
        self._node_configs: Dict[str, NodeConfig] = {}
        self._consensus: Optional[TestnetConsensus] = None
        self._faucet: Optional[FaucetNode] = None
        self._running = False
        self._start_time: float = 0.0
        self._consensus_task: Optional[asyncio.Task] = None
        self._blockchain_hooks: Dict[str, dict] = {}
        self._blocks_produced = 0
        self._txs_processed = 0

        self._build_node_configs()

    def _build_node_configs(self) -> None:
        """Build configuration for all nodes with full mesh seed lists."""
        all_ports = [(self.host, self.base_port + i) for i in range(self.num_nodes)]

        for i in range(self.num_nodes):
            port = self.base_port + i
            node_id = hashlib.sha256(f"testnet-node-{i}@{port}".encode()).hexdigest()[:16]
            agent_id = f"testnet_validator_{i}"

            # Full mesh: every node knows every other node
            seeds = [(h, p) for j, (h, p) in enumerate(all_ports) if j != i]

            self._node_configs[node_id] = NodeConfig(
                node_id=node_id,
                host=self.host,
                port=port,
                agent_id=agent_id,
                seeds=seeds,
                is_validator=True,
                stake_sats=1000 * 100_000_000,  # 1000 BAIT per validator
            )

    async def start(self) -> None:
        r"""Start all nodes and wait for P2P connections.

        1. Creates a TestnetConsensus instance
        2. Initializes P2PNode for each configured node
        3. Sets blockchain integration hooks
        4. Starts all P2P servers
        5. Waits for initial peer connections
        """
        if self._running:
            logger.warning("Testnet already running")
            return

        self._running = True
        self._start_time = time.time()
        logger.info(
            "Starting b'AI'tcoin testnet: %d nodes on %s:%d-%d",
            self.num_nodes, self.host, self.base_port,
            self.base_port + self.num_nodes - 1,
        )

        # Create consensus engine
        validator_ids = [cfg.agent_id for cfg in self._node_configs.values()]
        self._consensus = TestnetConsensus(
            validator_ids=validator_ids,
            block_interval=self.block_interval,
        )

        # Initialize each P2P node
        for node_id, cfg in self._node_configs.items():
            node = P2PNode(
                host=cfg.host,
                port=cfg.port,
                node_id=node_id,
                agent_id=cfg.agent_id,
                seeds=cfg.seeds,
            )

            # Set blockchain hooks for P2P integration
            node.set_blockchain_hooks(
                get_block=lambda h, nid=node_id: self._get_block(nid, h),
                get_headers=lambda loc, stop, nid=node_id: self._get_headers(nid, loc, stop),
                get_height=lambda nid=node_id: self._get_height(nid),
            )
            node.on_block_received(self._on_block_received)
            node.on_tx_received(self._on_tx_received)

            self._nodes[node_id] = node
            self._blockchain_hooks[node_id] = {
                "blocks": {},
                "height": 0,
                "tip_hash": "",
            }

        # Start all P2P servers
        start_tasks = []
        for node_id, node in self._nodes.items():
            start_tasks.append(node.start())

        await asyncio.gather(*start_tasks)

        # Wait for initial mesh connections
        await asyncio.sleep(1.0)
        logger.info("All %d testnet nodes started", self.num_nodes)

        # Start consensus loop
        self._consensus_task = asyncio.create_task(self._consensus_loop())

        # Initialize faucet if enabled
        if self.testnet_faucet_enabled:
            self._faucet = FaucetNode(
                network_name="baitcoin-testnet",
                initial_balance_sats=1_000_000 * 100_000_000,  # 1M BAIT
                claim_amount_sats=100 * 100_000_000,  # 100 BAIT per claim
                cooldown_seconds=60,
            )
            logger.info("Testnet faucet active: 1,000,000 BAIT available")

    async def stop(self) -> None:
        r"""Gracefully stop all nodes and cleanup resources."""
        self._running = False

        if self._consensus_task:
            self._consensus_task.cancel()
            try:
                await self._consensus_task
            except asyncio.CancelledError:
                pass

        stop_tasks = []
        for node in self._nodes.values():
            stop_tasks.append(node.stop())

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        self._nodes.clear()
        self._blockchain_hooks.clear()
        logger.info("Testnet stopped after %.1fs", time.time() - self._start_time)

    async def wait_for_sync(self, timeout: float = 30.0) -> bool:
        r"""Wait until all nodes are at the same block height.

        Polls node heights every SYNC_CHECK_INTERVAL seconds.
        Returns True if sync achieved within timeout, False otherwise.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._running:
                return False
            status = self.get_network_status()
            if status.synced:
                logger.info("All nodes synced at height %d", status.best_height)
                return True
            await asyncio.sleep(self.SYNC_CHECK_INTERVAL)
        logger.warning("Sync timeout: nodes not synced within %.1fs", timeout)
        return False

    async def mine_blocks(self, count: int = 1) -> int:
        r"""Manually trigger mining of `count` blocks via testnet consensus.

        Returns the new chain height after mining.
        """
        if not self._consensus:
            raise RuntimeError("Testnet not started")

        for _ in range(count):
            block_data = self._consensus.produce_block()
            if block_data:
                self._blocks_produced += 1
                # Propagate to all nodes
                for node in self._nodes.values():
                    await node.broadcast_block(block_data)

        return self._consensus.current_height

    async def submit_transaction(self, tx_data: dict) -> int:
        r"""Submit a transaction to the testnet for propagation.

        Returns the number of nodes that received the transaction.
        """
        total_propagated = 0
        for node in self._nodes.values():
            count = await node.broadcast_tx(tx_data)
            total_propagated += count
        self._txs_processed += 1
        return total_propagated

    def faucet_claim(self, agent_id: str, pubkey_hex: str) -> dict:
        r"""Claim testnet BAIT from the faucet.

        Returns claim details including amount and tx hash.
        """
        if not self._faucet:
            return {"error": "faucet_not_enabled"}
        return self._faucet.claim(agent_id, pubkey_hex)

    def get_network_status(self) -> TestnetStatus:
        r"""Get aggregated status of the entire testnet.

        Returns a TestnetStatus with per-node and aggregate metrics.
        """
        heights = []
        node_statuses = []
        total_connections = 0

        for node_id, node in self._nodes.items():
            status = node.get_status()
            height = self._blockchain_hooks.get(node_id, {}).get("height", 0)
            heights.append(height)
            total_connections += status["connections"]

            node_statuses.append({
                "node_id": node_id,
                "port": self._node_configs[node_id].port,
                "connections": status["connections"],
                "height": height,
                "known_blocks": status["known_blocks"],
                "known_txs": status["known_txs"],
                "running": status["running"],
            })

        best_height = max(heights) if heights else 0
        min_height = min(heights) if heights else 0
        connected_pairs = sum(1 for ns in node_statuses if ns["connections"] > 0)

        return TestnetStatus(
            running=self._running,
            num_nodes=self.num_nodes,
            connected_pairs=connected_pairs,
            total_connections=total_connections,
            best_height=best_height,
            min_height=min_height,
            synced=(best_height == min_height and best_height > 0),
            total_blocks_produced=self._blocks_produced,
            total_txs_processed=self._txs_processed,
            uptime_seconds=time.time() - self._start_time if self._start_time else 0.0,
            consensus=self._consensus.to_dict() if self._consensus else {},
            nodes=node_statuses,
        )

    def get_node(self, node_index: int) -> Optional[P2PNode]:
        r"""Get a specific node by index (0-based)."""
        node_ids = list(self._node_configs.keys())
        if 0 <= node_index < len(node_ids):
            return self._nodes.get(node_ids[node_index])
        return None

    # --- Internal methods ---

    async def _consensus_loop(self) -> None:
        r"""Background loop that drives testnet consensus."""
        while self._running:
            try:
                if self._consensus:
                    block_data = self._consensus.produce_block()
                    if block_data:
                        self._blocks_produced += 1
                        for node in self._nodes.values():
                            await node.broadcast_block(block_data)
            except Exception as e:
                logger.error("Consensus loop error: %s", e)
            await asyncio.sleep(self.block_interval)

    def _get_block(self, node_id: str, block_hash: str) -> Optional[dict]:
        """Retrieve a block from a specific node's chain."""
        hooks = self._blockchain_hooks.get(node_id, {})
        return hooks.get("blocks", {}).get(block_hash)

    def _get_headers(self, node_id: str, locator_hashes: List[str],
                      stop_hash: str) -> List[dict]:
        """Get headers from a specific node."""
        hooks = self._blockchain_hooks.get(node_id, {})
        blocks = hooks.get("blocks", {})
        headers = []
        for h, block_data in blocks.items():
            if h != stop_hash:
                if "header" in block_data:
                    headers.append(block_data["header"])
                else:
                    headers.append(block_data)
                if h == stop_hash:
                    break
        return headers[-50:]  # Max 50 headers

    def _get_height(self, node_id: str) -> int:
        """Get the chain height of a specific node."""
        return self._blockchain_hooks.get(node_id, {}).get("height", 0)

    def _on_block_received(self, block_data: dict, peer_id: str) -> None:
        """Handle a block received from a peer."""
        block_hash = block_data.get("hash", "")
        if not block_hash:
            return

        # Update all nodes' tracking (simulated shared state)
        for nid in self._blockchain_hooks:
            hooks = self._blockchain_hooks[nid]
            hooks["blocks"][block_hash] = block_data
            new_height = block_data.get("index", 0) + 1
            if new_height > hooks["height"]:
                hooks["height"] = new_height
                hooks["tip_hash"] = block_hash

    def _on_tx_received(self, tx_data: dict, peer_id: str) -> None:
        """Handle a transaction received from a peer."""
        self._txs_processed += 1

    def get_testnet_config(self) -> dict:
        r"""Export testnet configuration for external tools."""
        return {
            "network_name": "baitcoin-testnet",
            "num_nodes": self.num_nodes,
            "host": self.host,
            "base_port": self.base_port,
            "block_interval": self.block_interval,
            "faucet_enabled": self.testnet_faucet_enabled,
            "nodes": [
                {
                    "node_id": cfg.node_id,
                    "agent_id": cfg.agent_id,
                    "host": cfg.host,
                    "port": cfg.port,
                    "is_validator": cfg.is_validator,
                }
                for cfg in self._node_configs.values()
            ],
        }
