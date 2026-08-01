r"""Network Partition Simulator — Tests resilience under network splits.

Simulates network partitions in a testnet environment to test:
- Chain fork behavior when nodes are disconnected
- Reconciliation when partitions heal
- Consensus liveness under partial connectivity
- Transaction propagation in partitioned networks

The simulator works by maintaining a partition map that controls
which nodes can communicate. Partitions are applied by disabling
P2P connections between nodes in different partition groups.

Usage::

    partition = NetworkPartition(num_nodes=5)
    partition.split([0, 1], [2, 3, 4])  # 2-group partition
    # ... wait for forks ...
    partition.heal()  # restore full connectivity
    fork_depth = partition.get_max_fork_depth()
"""

import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class PartitionGroup:
    """A group of nodes that can communicate with each other."""
    group_id: int
    node_indices: List[int]
    created_at: float = field(default_factory=time.time)

    def can_communicate(self, node_a: int, node_b: int) -> bool:
        """Check if two nodes are in the same partition group."""
        return (node_a in self.node_indices) == (node_b in self.node_indices)

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "node_indices": self.node_indices,
            "size": len(self.node_indices),
            "created_at": self.created_at,
        }


@dataclass
class PartitionEvent:
    """Record of a partition/heal event."""
    event_type: str  # "split" or "heal"
    groups: List[List[int]]
    timestamp: float = field(default_factory=time.time)
    fork_depth_at_event: int = 0

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "groups": self.groups,
            "timestamp": self.timestamp,
            "fork_depth_at_event": self.fork_depth_at_event,
        }


class NetworkPartition:
    r"""Simulates network partitions in a testnet.

    Tracks partition state and provides analysis of chain behavior
    during and after network splits. The simulator does NOT directly
    manipulate P2P connections — it provides the partition map that
    the orchestrator uses to filter message delivery.

    Parameters
    ----------
    num_nodes : int
        Total number of nodes in the testnet
    """

    def __init__(self, num_nodes: int):
        self.num_nodes = num_nodes
        self._current_groups: List[PartitionGroup] = []
        self._history: List[PartitionEvent] = []
        self._is_partitioned = False
        self._partition_active_since: float = 0.0

        # Track fork state per node
        self._node_heights: Dict[int, int] = {i: 0 for i in range(num_nodes)}
        self._node_tips: Dict[int, str] = {i: "" for i in range(num_nodes)}

    def is_partitioned(self) -> bool:
        r"""Check if the network is currently partitioned."""
        return self._is_partitioned

    def split(self, *groups: List[int]) -> PartitionEvent:
        r"""Create a network partition.

        Parameters
        ----------
        *groups : List[int]
            Variable number of groups, each containing node indices.
            Nodes not in any group form an implicit "isolated" group.

        Returns
        -------
        PartitionEvent
            Record of the split event

        Example
        -------
        >>> partition.split([0, 1], [2, 3, 4])  # Split into 2 groups
        """
        if not groups:
            raise ValueError("At least one group required")

        # Validate all node indices
        assigned = set()
        for group in groups:
            for idx in group:
                if idx < 0 or idx >= self.num_nodes:
                    raise ValueError(f"Invalid node index: {idx}")
                if idx in assigned:
                    raise ValueError(f"Node {idx} in multiple groups")
                assigned.add(idx)

        # Build partition groups
        self._current_groups = []
        for i, node_indices in enumerate(groups):
            self._current_groups.append(
                PartitionGroup(group_id=i, node_indices=list(node_indices))
            )

        # Isolated nodes (not in any explicit group)
        isolated = [i for i in range(self.num_nodes) if i not in assigned]
        if isolated:
            self._current_groups.append(
                PartitionGroup(
                    group_id=len(groups), node_indices=isolated
                )
            )

        self._is_partitioned = True
        self._partition_active_since = time.time()

        event = PartitionEvent(
            event_type="split",
            groups=[g.node_indices for g in self._current_groups],
        )
        self._history.append(event)
        return event

    def heal(self) -> PartitionEvent:
        r"""Heal the partition, restoring full connectivity.

        Returns
        -------
        PartitionEvent
            Record of the heal event
        """
        event = PartitionEvent(
            event_type="heal",
            groups=[
                list(range(self.num_nodes))
            ],
            fork_depth_at_event=self.get_max_fork_depth(),
        )
        self._history.append(event)
        self._current_groups = []
        self._is_partitioned = False
        self._partition_active_since = 0.0
        return event

    def can_communicate(self, node_a: int, node_b: int) -> bool:
        r"""Check if two nodes can communicate given current partition."""
        if not self._is_partitioned:
            return True

        for group in self._current_groups:
            a_in = node_a in group.node_indices
            b_in = node_b in group.node_indices
            if a_in and b_in:
                return True
            if a_in or b_in:
                return False

        # Both nodes are isolated (not in any group)
        return False

    def get_group_for_node(self, node_idx: int) -> Optional[PartitionGroup]:
        r"""Get the partition group containing a specific node."""
        for group in self._current_groups:
            if node_idx in group.node_indices:
                return group
        return None

    def update_node_height(self, node_idx: int, height: int, tip_hash: str = "") -> None:
        r"""Update tracked chain height for a node (called by orchestrator)."""
        self._node_heights[node_idx] = height
        if tip_hash:
            self._node_tips[node_idx] = tip_hash

    def get_max_fork_depth(self) -> int:
        r"""Calculate the maximum fork depth across all nodes.

        Fork depth = max(height) - min(height) among all nodes.
        """
        if not self._node_heights:
            return 0
        heights = list(self._node_heights.values())
        return max(heights) - min(heights)

    def get_partition_duration(self) -> float:
        r"""Get how long the current partition has been active."""
        if not self._is_partitioned or not self._partition_active_since:
            return 0.0
        return time.time() - self._partition_active_since

    def get_conflicting_tips(self) -> List[Tuple[int, int, str, str]]:
        r"""Find pairs of nodes with conflicting chain tips.

        Returns list of (node_a, node_b, tip_a, tip_b) tuples where
        both nodes are at the same height but have different tips.
        """
        conflicts = []
        nodes = list(range(self.num_nodes))
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                if (self._node_heights[a] == self._node_heights[b]
                        and self._node_tips[a]
                        and self._node_tips[b]
                        and self._node_tips[a] != self._node_tips[b]):
                    conflicts.append(
                        (a, b, self._node_tips[a], self._node_tips[b])
                    )
        return conflicts

    def get_history(self) -> List[dict]:
        r"""Get full partition/heal event history."""
        return [e.to_dict() for e in self._history]

    def to_dict(self) -> dict:
        r"""Full partition state export."""
        return {
            "num_nodes": self.num_nodes,
            "is_partitioned": self._is_partitioned,
            "partition_duration": self.get_partition_duration(),
            "max_fork_depth": self.get_max_fork_depth(),
            "conflicting_tips": len(self.get_conflicting_tips()),
            "groups": [g.to_dict() for g in self._current_groups],
            "node_heights": dict(self._node_heights),
            "event_count": len(self._history),
        }
