r"""b'AI'tcoin Testnet — Multi-node P2P test network.

Provides orchestrated local testnet for development and testing:
- TestnetOrchestrator: manages N local P2P nodes
- TestnetConsensus: simulated consensus with deterministic block ordering
- FaucetNode: integrated testnet faucet for funding test accounts
- NetworkPartition: simulated network partitions for resilience testing

Usage::

    orch = TestnetOrchestrator(num_nodes=5)
    await orch.start()
    await orch.wait_for_sync()
    status = orch.get_network_status()
    await orch.stop()
"""

from baitcoin_core.network.testnet.orchestrator import TestnetOrchestrator
from baitcoin_core.network.testnet.consensus import TestnetConsensus
from baitcoin_core.network.testnet.faucet_node import FaucetNode
from baitcoin_core.network.testnet.partition import NetworkPartition

__all__ = [
    "TestnetOrchestrator",
    "TestnetConsensus",
    "FaucetNode",
    "NetworkPartition",
]
