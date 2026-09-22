# Priority queues for bridge transactions (BAIT)

## Goal

Order operator attention / processing of lock-mint and burn-release requests by priority **without**:
- Lowering the 3-of-5 threshold
- Bypassing pause or rate limit
- Auto-executing without confirms

## Priority levels (uint8)

| Level | Name | Typical use |
|-------|------|-------------|
| 0 | NORMAL | Default |
| 1 | HIGH | Institutional SLA |
| 2 | CRITICAL | Emergency ops (still requires 3/5) |

## On-chain (additive)

Add to `LockRequest`:
- `uint8 priority`
- `uint64 createdAt`

Emit priority in `LockRequested`. Optional overload:

```solidity
requestLockMint(requestId, l1TxId, recipient, amount, priority)
```

Default path keeps `priority = 0`.

Combine with rate-limit **reservation on request** (H-R2 fix).

## Off-chain operator queue

```text
order by (priority DESC, createdAt ASC)
confirm head if not yet confirmed by this operator
```

## What priority must NOT do

- Reduce REQUIRED_CONFIRMATIONS
- Skip whenNotPaused
- Skip rate limit
- Auto-confirm / auto-execute

## Phased rollout

1. Fields + events
2. Operator bots sort by priority
3. Quota on CRITICAL per operator per day
4. Cancel/TTL + release reserved rate limit

Full design notes in remediation package PRIORITY_QUEUE_BRIDGE.md.
