# P1 — On-chain priority heap (optional, not in BridgeLock core)

## Why not ship a heap in BridgeLock now

- 3/5 security does not need on-chain ordering
- Binary heap on-chain is gas-heavy (swaps, storage writes)
- Discrete levels 0..2 + off-chain sort is enough

## If fairness must be proven on-chain later

Prefer **bucket queues** over a binary heap:

```solidity
mapping(uint8 => bytes32[]) private queueByPriority; // 0..2 FIFO each
uint256 public head0;
uint256 public head1;
uint256 public head2;

function enqueue(uint8 p, bytes32 id) internal {
    queueByPriority[p].push(id);
}

function peekNext() public view returns (bytes32 id, bool found) {
    if (head2 < queueByPriority[2].length) return (queueByPriority[2][head2], true);
    if (head1 < queueByPriority[1].length) return (queueByPriority[1][head1], true);
    if (head0 < queueByPriority[0].length) return (queueByPriority[0][head0], true);
    return (bytes32(0), false);
}
```

O(1) enqueue/dequeue per level; no heapify.

## Binary heap (only if continuous scores needed)

- Array-backed max-heap of (priorityScore, requestId)
- insert O(log n) storage writes — expensive at scale
- Not recommended for bridge msig with 3 levels

## Recommendation

Keep BridgeLock as committed (levels + events + off-chain bots). Add bucket queue only if product requires mandatory on-chain FIFO-per-tier execution.
