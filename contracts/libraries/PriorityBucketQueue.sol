// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PriorityBucketQueue
 * @notice O(1) enqueue/dequeue for fixed priority levels 0..2.
 * @dev Optional module — not wired into BridgeLock core by default.
 */
library PriorityBucketQueue {
    uint8 internal constant LEVELS = 3;

    struct Queue {
        mapping(uint8 => mapping(uint256 => bytes32)) items;
        mapping(uint8 => uint256) head;
        mapping(uint8 => uint256) tail;
        mapping(bytes32 => bool) enqueued;
    }

    error InvalidPriority();
    error EmptyQueue();
    error AlreadyEnqueued();

    function enqueue(Queue storage q, uint8 priority, bytes32 id) internal {
        if (priority >= LEVELS) revert InvalidPriority();
        if (id == bytes32(0)) revert InvalidPriority();
        if (q.enqueued[id]) revert AlreadyEnqueued();

        uint256 t = q.tail[priority];
        q.items[priority][t] = id;
        q.tail[priority] = t + 1;
        q.enqueued[id] = true;
    }

    function dequeue(Queue storage q, uint8 priority) internal returns (bytes32 id) {
        if (priority >= LEVELS) revert InvalidPriority();
        uint256 h = q.head[priority];
        uint256 t = q.tail[priority];
        if (h >= t) revert EmptyQueue();

        id = q.items[priority][h];
        delete q.items[priority][h];
        q.head[priority] = h + 1;
        q.enqueued[id] = false;
    }

    function peekNext(Queue storage q) internal view returns (bytes32 id, uint8 priority, bool found) {
        for (uint8 p = LEVELS; p > 0; ) {
            unchecked { --p; }
            uint256 h = q.head[p];
            if (h < q.tail[p]) {
                return (q.items[p][h], p, true);
            }
        }
        return (bytes32(0), 0, false);
    }

    function length(Queue storage q, uint8 priority) internal view returns (uint256) {
        if (priority >= LEVELS) return 0;
        uint256 h = q.head[priority];
        uint256 t = q.tail[priority];
        return t > h ? t - h : 0;
    }

    function totalLength(Queue storage q) internal view returns (uint256 n) {
        for (uint8 p = 0; p < LEVELS; ++p) {
            n += length(q, p);
        }
    }
}
