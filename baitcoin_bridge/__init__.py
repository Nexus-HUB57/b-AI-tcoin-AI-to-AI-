r"""b'AI'tcoin Cross-Chain Bridges — Interoperability with ETH and SOL.

Implements the bridge protocol for transferring assets between
b'AI'tcoin and external blockchains (Ethereum, Solana).

Architecture (Lock-Mint-Burn-Release pattern)::

    Ethereum/Solana                      b'AI'tcoin
    +------------------+     Anchor     +------------------+
    |  Lock Contract   | <----------- |  Bridge Watcher  |
    |  (lock BAIT/ETH) |    Merkle     |  (monitor events)|
    +------------------+    Proofs     +------------------+
           |                              |
           |    Relayer submits           |
           |    SPV proof to              |
           |    Bridge Manager            |
           v                              v
    +------------------+     Mint     +------------------+
    |  Release Contract| ----------> |  Bridge Manager  |
    |  (release ETH)   |   Tokens    |  (mint wrapped)  |
    +------------------+              +------------------+

Bridge Components:
    - BridgeManager: orchestrates lock/mint/burn/release
    - BridgeWatcher: monitors external chain events
    - Relayer: submits cross-chain proofs
    - AnchorProtocol: Merkle proof anchoring
    - BridgePool: liquidity pool for instant swaps

Supported Chains:
    - Ethereum (ETH, ERC-20 tokens)
    - Solana (SOL, SPL tokens)

Security:
    - N-of-M multi-sig for mint authorization
    - Merkle proof verification (SPV)
    - Timeout + refund mechanism
    - Rate limiting per address
    - Emergency pause

Usage::

    manager = BridgeManager()
    lock = manager.lock_bait_on_eth("agent_1", 100 * 100_000_000, "0xRecipient")
    proof = manager.generate_merkle_proof(lock["event_id"])
    mint = manager.mint_wrapped(lock["event_id"], proof)
"""

from baitcoin_bridge.manager import BridgeManager
from baitcoin_bridge.watcher import BridgeWatcher
from baitcoin_bridge.relayer import Relayer
from baitcoin_bridge.anchor import AnchorProtocol
from baitcoin_bridge.pool import BridgePool
from baitcoin_bridge.config import ChainConfig, BridgeConfig

__all__ = [
    "BridgeManager",
    "BridgeWatcher",
    "Relayer",
    "AnchorProtocol",
    "BridgePool",
    "ChainConfig",
    "BridgeConfig",
]
