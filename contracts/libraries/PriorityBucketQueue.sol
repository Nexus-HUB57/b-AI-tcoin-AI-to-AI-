// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PriorityBucketQueue (gas-optimized)
 * @notice O(1) enqueue/dequeue for priority levels 0..2.
 * @dev head+tail packed in one slot per level (saves an SSTORE on enqueue path).
 */
library PriorityBucketQueue {
    uint8 internal constant LEVELS = 3;

    struct Queue {
        mapping(uint8 => mapping(uint256 => bytes32)) items;
        mapping(uint8 => uint256) headTail;
        mapping(bytes32 => bool) enqueued;
    }

    error InvalidPriority();
    error EmptyQueue();
    error AlreadyEnqueued();

    function _head(uint256 packed) private pure returns (uint256) {
        return packed & type(uint128).max;
    }

    function _tail(uint256 packed) private pure returns (uint256) {
        return packed >> 128;
    }

    function _pack(uint256 head_, uint256 tail_) private pure returns (uint256) {
        return head_ | (tail_ << 128);
    }

    function enqueue(Queue storage q, uint8 priority, bytes32 id) internal {
        if (priority >= LEVELS) revert InvalidPriority();
        if (q.enqueued[id]) revert AlreadyEnqueued();

        uint256 packed = q.headTail[priority];
        uint256 t = _tail(packed);
        q.items[priority][t] = id;
        q.headTail[priority] = _pack(_head(packed), t + 1);
        q.enqueued[id] = true;
    }

    function dequeue(Queue storage q, uint8 priority) internal returns (bytes32 id) {
        if (priority >= LEVELS) revert InvalidPriority();
        uint256 packed = q.headTail[priority];
        uint256 h = _head(packed);
        uint256 t = _tail(packed);
        if (h >= t) revert EmptyQueue();

        id = q.items[priority][h];
        delete q.items[priority][h];
        q.headTail[priority] = _pack(h + 1, t);
        q.enqueued[id] = false;
    }

    function peekNext(Queue storage q)
        internal
        view
        returns (bytes32 id, uint8 priority, bool found)
    {
        uint256 packed = q.headTail[2];
        if (_head(packed) < _tail(packed)) {
            return (q.items[2][_head(packed)], 2, true);
        }
        packed = q.headTail[1];
        if (_head(packed) < _tail(packed)) {
            return (q.items[1][_head(packed)], 1, true);
        }
        packed = q.headTail[0];
        if (_head(packed) < _tail(packed)) {
            return (q.items[0][_head(packed)], 0, true);
        }
        return (bytes32(0), 0, false);
    }

    function length(Queue storage q, uint8 priority) internal view returns (uint256) {
        if (priority >= LEVELS) return 0;
        uint256 packed = q.headTail[priority];
        uint256 h = _head(packed);
        uint256 t = _tail(packed);
        return t > h ? t - h : 0;
    }

    function totalLength(Queue storage q) internal view returns (uint256 n) {
        unchecked {
            n = length(q, 0) + length(q, 1) + length(q, 2);
        }
    }
}
