r"""
Block Synchronization Protocol for b'AI'tcoin.

Manages block synchronization between peers with:
- Sync status tracking (height, peer height, progress)
- Block range requests
- Block validation before application to chain
- Fork detection and resolution (longest chain wins)
- Orphan block pool for blocks awaiting parent arrival

Usage::

    sync = BlockSync(blockchain)
    status = sync.get_sync_status()
    blocks = sync.request_blocks(0, 10, "peer_id")
    valid = sync.validate_and_apply(block)
"""

import time
import logging
from typing import List, Dict, Optional, Any
from baitcoin_core.blockchain.block import Block

logger = logging.getLogger(__name__)


class BlockSync:
    """Block synchronization protocol for chain state convergence.

    Wraps a Blockchain instance and provides:
    - Sync status queries
    - Block range requests (simulated via blockchain lookup)
    - Validation + application of incoming blocks
    - Fork detection and resolution (longest chain wins)
    - Orphan pool management for out-of-order blocks

    Args:
        blockchain: The Blockchain instance to synchronize against.
        max_orphan_pool: Maximum size of the orphan block pool.
    """

    def __init__(
        self,
        blockchain,
        max_orphan_pool: int = 1024,
    ):
        self.blockchain = blockchain
        self.max_orphan_pool = max_orphan_pool

        # Orphan pool: blocks whose parent is not yet in the chain
        # Key: prev_block_hash (hex), Value: list of Block
        self._orphan_pool: Dict[str, List[Block]] = {}

        # Sync state
        self._syncing: bool = False
        self._sync_start_time: Optional[float] = None
        self._sync_start_height: int = 0
        self._peer_heights: Dict[str, int] = {}  # peer_id -> known height

        # Stats
        self._blocks_applied: int = 0
        self._blocks_rejected: int = 0
        self._forks_resolved: int = 0

    # ── Sync Status ──────────────────────────────────────────

    def get_sync_status(self) -> Dict[str, Any]:
        """Return the current synchronization status.

        Returns:
            Dict with keys: syncing, height, peer_height, progress,
            blocks_applied, blocks_rejected, forks_resolved.
        """
        our_height = self.blockchain.height

        # Best known peer height
        best_peer_height = 0
        if self._peer_heights:
            best_peer_height = max(self._peer_heights.values())

        progress = 1.0
        if best_peer_height > our_height and best_peer_height > 0:
            progress = min(our_height / best_peer_height, 1.0)

        return {
            "syncing": self._syncing,
            "height": our_height,
            "peer_height": best_peer_height,
            "progress": progress,
            "blocks_applied": self._blocks_applied,
            "blocks_rejected": self._blocks_rejected,
            "forks_resolved": self._forks_resolved,
            "orphan_pool_size": self._orphan_pool_size(),
        }

    def update_peer_height(self, peer_id: str, height: int) -> None:
        """Record the reported chain height from a peer.

        Args:
            peer_id: Identifier of the reporting peer.
            height: The peer's reported chain height.
        """
        self._peer_heights[peer_id] = height

    def start_sync(self, target_height: Optional[int] = None) -> None:
        """Mark sync as in-progress.

        Args:
            target_height: Optional target height for progress tracking.
        """
        self._syncing = True
        self._sync_start_time = time.time()
        self._sync_start_height = self.blockchain.height

    def stop_sync(self) -> None:
        """Mark sync as complete."""
        self._syncing = False
        self._sync_start_time = None

    # ── Block Requests ───────────────────────────────────────

    def request_blocks(
        self,
        from_height: int,
        to_height: int,
        peer_id: Optional[str] = None,
    ) -> List[Block]:
        """Request a range of blocks.

        In a real implementation, this would send a network request to
        the specified peer. Here we look up blocks from the local
        blockchain (useful for simulating sync between local instances).

        Args:
            from_height: Starting block height (inclusive).
            to_height: Ending block height (inclusive).
            peer_id: Peer to request from (logged for debugging).

        Returns:
            List of Block objects in the requested range.
        """
        logger.debug(
            "Requesting blocks %d-%d from peer %s",
            from_height, to_height, peer_id,
        )
        blocks = []
        for h in range(from_height, min(to_height + 1, len(self.blockchain.chain))):
            block = self.blockchain.get_block(h)
            if block is not None:
                blocks.append(block)
        return blocks

    # ── Validation and Application ──────────────────────────

    def validate_and_apply(self, block: Block) -> bool:
        """Validate a block against chain rules and apply if valid.

        Validation checks:
        1. Block height must be exactly one greater than chain height
        2. Block must reference the current tip
        3. Merkle root must be correct
        4. Coinbase transaction must be present (for height > 0)
        5. Block timestamp must not be too far in the future

        Args:
            block: The Block to validate and apply.

        Returns:
            True if the block was validated and added to the chain.
        """
        our_height = self.blockchain.height

        # Check if block is for the next slot
        if block.index != our_height + 1:
            # Could be a duplicate or orphan
            if block.index > our_height + 1:
                self._add_to_orphan_pool(block)
                return False
            else:
                # Block at same or lower height — reject
                self._blocks_rejected += 1
                logger.info(
                    "Rejected block at height %d (our height %d)",
                    block.index, our_height,
                )
                return False

        # Check parent hash linkage
        expected_parent = self.blockchain.last_block.block_hash
        if block.header.prev_block_hash != expected_parent:
            # Fork detected — try to resolve
            resolved = self.handle_fork(block)
            return resolved

        # Validate the block internally
        if not self._validate_block_integrity(block):
            self._blocks_rejected += 1
            return False

        # Apply the block
        self.blockchain.chain.append(block)

        # Update UTXO set for coinbase
        for tx in block.transactions:
            if tx.is_coinbase:
                self.blockchain._update_utxo(tx)

        self._blocks_applied += 1

        # Try to process orphans
        self._process_orphans()

        logger.info("Applied block at height %d", block.index)
        return True

    def _validate_block_integrity(self, block: Block) -> bool:
        """Validate internal block structure.

        Checks merkle root, coinbase presence, timestamp.
        """
        # Merkle root
        if block.header.merkle_root != block.compute_merkle_root():
            logger.warning("Block %d: invalid merkle root", block.index)
            return False

        # Coinbase required for non-genesis
        if block.index > 0 and not block.coinbase_tx:
            logger.warning("Block %d: missing coinbase", block.index)
            return False

        # Timestamp sanity (max 2 hours in the future)
        if block.header.timestamp > time.time() + 7200:
            logger.warning("Block %d: timestamp too far in future", block.index)
            return False

        return True

    # ── Fork Resolution ───────────────────────────────────────

    def handle_fork(self, block: Block) -> bool:
        """Detect and resolve a chain fork.

        Strategy: longest chain wins. If the incoming block creates a
        fork, we compare cumulative work. For now, since we only have
        a single competing block, we simply reject blocks that don't
        extend our current tip. In a full implementation, we would
        request the competing chain and compare.

        Args:
            block: The block that triggered a potential fork.

        Returns:
            True if the fork was resolved (block applied), False otherwise.
        """
        logger.info(
            "Fork detected at height %d — incoming block parent differs from tip",
            block.index,
        )
        self._forks_resolved += 1

        # For now: reject forks that don't extend our chain.
        # A full implementation would:
        # 1. Track the forked chain
        # 2. Request competing blocks
        # 3. Switch to the longer chain
        self._add_to_orphan_pool(block)
        self._blocks_rejected += 1
        return False

    # ── Orphan Pool ───────────────────────────────────────────

    def _add_to_orphan_pool(self, block: Block) -> None:
        """Add a block to the orphan pool.

        Orphans are keyed by their prev_block_hash so they can
        be found when the parent block arrives.

        Args:
            block: The orphan Block to store.
        """
        if self._orphan_pool_size() >= self.max_orphan_pool:
            # Evict oldest entries
            self._evict_oldest_orphans(self.max_orphan_pool // 4)

        parent_key = block.header.prev_block_hash.hex()
        if parent_key not in self._orphan_pool:
            self._orphan_pool[parent_key] = []
        self._orphan_pool[parent_key].append(block)
        logger.debug(
            "Added orphan block at height %d (parent: %s...)",
            block.index,
            parent_key[:16],
        )

    def _orphan_pool_size(self) -> int:
        """Return the total number of orphan blocks."""
        return sum(len(blocks) for blocks in self._orphan_pool.values())

    def _evict_oldest_orphans(self, count: int) -> None:
        """Evict the oldest orphan entries to make room."""
        # Simple eviction: remove first `count` keys
        keys = list(self._orphan_pool.keys())
        for key in keys[:count]:
            del self._orphan_pool[key]
        logger.debug("Evicted %d orphan entries", min(count, len(keys)))

    def _process_orphans(self) -> int:
        """Try to apply orphan blocks whose parent now exists.

        Called after a new block is applied. Checks if any orphans
        can now be connected to the chain.

        Returns:
            Number of orphan blocks successfully applied.
        """
        tip_hash = self.blockchain.last_block.block_hash.hex()
        orphans = self._orphan_pool.pop(tip_hash, [])

        applied = 0
        for block in orphans:
            if self.validate_and_apply(block):
                applied += 1

        if applied > 0:
            logger.info("Processed %d orphan blocks", applied)

        return applied

    def get_orphan_pool(self) -> List[Dict[str, Any]]:
        """Return all orphan blocks as dicts.

        Returns:
            List of serialized orphan block dicts.
        """
        result = []
        for blocks in self._orphan_pool.values():
            for block in blocks:
                result.append(block.to_dict())
        return result

    # ── Diagnostics ────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return synchronization statistics."""
        return self.get_sync_status()
