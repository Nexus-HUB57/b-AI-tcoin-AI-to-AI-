r"""
Testnet Manager for b'AI'tcoin — Public testnet operation.

Provides a high-level interface for managing b'AI'tcoin testnet operations:
- Testnet configuration generation
- Testnet node creation with testnet parameters
- Faucet initialization for funding test accounts
- Testnet-wide status monitoring
- Testnet address detection (t' prefix)

Usage::

    mgr = TestnetManager()
    config = mgr.create_testnet_config()
    node = mgr.start_testnet_node(config)
    faucet = mgr.initialize_faucet()
    status = mgr.get_testnet_status()
"""

import hashlib
import logging
import os
import time
from typing import Dict, List, Optional, Any

from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.network.node import IndependentNode

logger = logging.getLogger(__name__)

# Default testnet ports and seeds
TESTNET_DEFAULT_PORT = 18444
TESTNET_MAGIC = bytes([0x0b, 0x11, 0x09, 0x07])  # testnet magic bytes


class TestnetManager:
    """Manager for b'AI'tcoin public testnet operations.

    Handles the full lifecycle of testnet management: configuration,
    node creation, faucet funding, and status monitoring.

    Attributes:
        nodes: Dict of active testnet node_id -> IndependentNode.
        faucet_balance: Current faucet balance in satoshis.
        network_id: Testnet network identifier.
    """

    def __init__(self):
        self.nodes: Dict[str, IndependentNode] = {}
        self.faucet_balance: int = 0
        self.network_id: int = 2  # Default testnet network ID
        self._faucet_initialized: bool = False
        self._config: Optional[Dict[str, Any]] = None

    # ── Configuration ────────────────────────────────────────

    def create_testnet_config(
        self,
        network_id: int = 2,
        testnet_coinbase: str = "testnet_genesis",
    ) -> Dict[str, Any]:
        """Generate a testnet configuration.

        Creates a complete configuration dict for launching testnet nodes
        with testnet-specific parameters: lower difficulty, shorter
        block times, testnet coinbase, and testnet seed peers.

        Args:
            network_id: Network identifier (default 2 for testnet).
            testnet_coinbase: Coinbase agent ID for testnet genesis.

        Returns:
            Configuration dict with all testnet parameters.
        """
        self.network_id = network_id

        # Testnet uses a much easier target for fast mining
        # Target: must start with 0x00ffff... (very easy)
        testnet_target = 0x00ffff0000000000000000000000000000000000000000000000000000000000

        config = {
            "network_id": network_id,
            "network_name": "testnet",
            "coinbase_agent": testnet_coinbase,
            "port": TESTNET_DEFAULT_PORT,
            "magic_bytes": TESTNET_MAGIC.hex(),
            "consensus": {
                "target": hex(testnet_target),
                "target_bits": "0x1d00ffff",
                "block_time": 30,  # 30s target
                "difficulty_adjustment_interval": 2016,
            },
            "genesis": {
                "timestamp": 1700000000.0,
                "bits": 0x1d00ffff,
                "coinbase_text": f"b'AI'tcoin Testnet Genesis - {testnet_coinbase}",
            },
            "seed_peers": [
                {"host": "testnet-seed1.baitcoin.ai", "port": TESTNET_DEFAULT_PORT},
                {"host": "testnet-seed2.baitcoin.ai", "port": TESTNET_DEFAULT_PORT + 1},
                {"host": "testnet-seed3.baitcoin.ai", "port": TESTNET_DEFAULT_PORT + 2},
            ],
            "rpc": {
                "host": "127.0.0.1",
                "port": TESTNET_DEFAULT_PORT + 1000,
            },
            "limits": {
                "max_peers": 25,
                "max_mempool": 10_000,
                "max_orphan_pool": 512,
            },
            "address_prefix": "t'",
            "faucet": {
                "max_fund_per_request": 1_000_000,  # 0.01 BAIT
                "cooldown_seconds": 60,
                "max_total_fund": 100_000_000_000,  # 1000 BAIT
            },
        }

        self._config = config
        logger.info(
            "Created testnet config: network_id=%d, target=%s",
            network_id, hex(testnet_target),
        )
        return config

    # ── Node Management ───────────────────────────────────────

    def start_testnet_node(
        self,
        config: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
    ) -> IndependentNode:
        """Start a testnet node with the given configuration.

        Creates an IndependentNode with testnet-specific consensus
        parameters (lower difficulty target).

        Args:
            config: Testnet configuration dict. Uses stored config if None.
            node_id: Optional node identifier. Auto-generated if None.
            host: Host to bind to.
            port: Port to listen on. Uses config default if None.

        Returns:
            The started IndependentNode.
        """
        if config is None:
            config = self._config or self.create_testnet_config()

        # Parse testnet target
        target_hex = config["consensus"]["target"]
        testnet_target = int(target_hex, 16)

        # Create consensus with testnet target
        consensus = ZkMLConsensus(target=testnet_target)

        # Auto-generate node_id if not provided
        if node_id is None:
            node_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]

        if port is None:
            port = config.get("port", TESTNET_DEFAULT_PORT)

        # Create and start the node
        node = IndependentNode(
            node_id=node_id,
            host=host,
            port=port,
            network="testnet",
            consensus=consensus,
        )
        node.start()

        self.nodes[node_id] = node
        logger.info(
            "Started testnet node %s on %s:%d",
            node_id, host, port,
        )
        return node

    def stop_all_nodes(self) -> None:
        """Stop all testnet nodes."""
        for node_id, node in self.nodes.items():
            try:
                node.stop()
            except Exception as exc:
                logger.error("Error stopping node %s: %s", node_id, exc)
        self.nodes.clear()
        logger.info("All testnet nodes stopped")

    # ── Faucet ─────────────────────────────────────────────────

    def initialize_faucet(
        self,
        initial_fund_sats: int = 1_000_000_000,
    ) -> Dict[str, Any]:
        """Initialize the testnet faucet with an initial balance.

        The faucet provides testnet coins for development and testing.
        In a real deployment, the faucet would have its own wallet.

        Args:
            initial_fund_sats: Initial funding in satoshis.

        Returns:
            Faucet initialization status dict.
        """
        self.faucet_balance = initial_fund_sats
        self._faucet_initialized = True

        status = {
            "initialized": True,
            "balance_sats": self.faucet_balance,
            "balance_bait": self.faucet_balance / 100_000_000,
            "max_per_request": self._config["faucet"]["max_fund_per_request"]
            if self._config
            else 1_000_000,
            "cooldown_seconds": self._config["faucet"]["cooldown_seconds"]
            if self._config
            else 60,
        }

        logger.info(
            "Initialized testnet faucet with %d sats (%.2f BAIT)",
            initial_fund_sats,
            initial_fund_sats / 100_000_000,
        )
        return status

    def dispense_faucet_funds(
        self,
        address: str,
        amount_sats: int = 1_000_000,
    ) -> Dict[str, Any]:
        """Dispense testnet coins from the faucet.

        Args:
            address: Target address (must be a testnet address).
            amount_sats: Amount to dispense in satoshis.

        Returns:
            Dispense result dict with success/failure info.
        """
        if not self._faucet_initialized:
            return {"success": False, "reason": "Faucet not initialized"}

        max_per_request = (
            self._config["faucet"]["max_fund_per_request"]
            if self._config
            else 1_000_000
        )

        if amount_sats > max_per_request:
            return {
                "success": False,
                "reason": f"Amount exceeds max per request ({max_per_request} sats)",
            }

        if amount_sats > self.faucet_balance:
            return {"success": False, "reason": "Faucet balance insufficient"}

        if not self.is_testnet_address(address):
            return {"success": False, "reason": "Address is not a valid testnet address"}

        self.faucet_balance -= amount_sats

        tx_ref = hashlib.sha256(
            f"{address}:{amount_sats}:{time.time()}".encode()
        ).hexdigest()[:16]

        return {
            "success": True,
            "address": address,
            "amount_sats": amount_sats,
            "tx_ref": tx_ref,
            "remaining_balance_sats": self.faucet_balance,
        }

    # ── Status ────────────────────────────────────────────────

    def get_testnet_status(self) -> Dict[str, Any]:
        """Return comprehensive testnet status.

        Returns:
            Dict with active nodes, total blocks, faucet balance,
            network details.
        """
        total_blocks = 0
        node_statuses = {}
        for node_id, node in self.nodes.items():
            height = node.blockchain.height
            total_blocks = max(total_blocks, height)
            node_statuses[node_id] = {
                "height": height,
                "peers": len(node.p2p.peers),
                "running": node._running,
            }

        return {
            "network_id": self.network_id,
            "network_name": "testnet",
            "active_nodes": len(self.nodes),
            "node_details": node_statuses,
            "total_blocks": total_blocks,
            "faucet": {
                "initialized": self._faucet_initialized,
                "balance_sats": self.faucet_balance,
                "balance_bait": self.faucet_balance / 100_000_000,
            },
            "config_exists": self._config is not None,
        }

    # ── Address Detection ──────────────────────────────────────

    @classmethod
    def is_testnet_address(cls, addr: str) -> bool:
        """Check if an address is a valid testnet address.

        Testnet addresses use the ``t'`` prefix (as opposed to
        mainnet ``b'`` prefix).

        Args:
            addr: The address string to check.

        Returns:
            True if the address starts with the testnet prefix.
        """
        if not isinstance(addr, str):
            return False
        if not addr:
            return False
        return addr.startswith("t'")

    # ── Representation ─────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"TestnetManager(network_id={self.network_id}, "
            f"nodes={len(self.nodes)}, "
            f"faucet_balance={self.faucet_balance})"
        )
