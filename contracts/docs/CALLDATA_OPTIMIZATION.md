# Calldata optimization — BridgeLock / BAIT

## Why it matters

| Byte type | Gas (post EIP-2028) |
|-----------|---------------------|
| Zero | 4 |
| Non-zero | 16 |

## Current hot paths

- `requestLockMint(bytes32,bytes32,address,uint256)` ~4x32B + selector
- `requestLockMint(..., uint8 priority)` — uint8 still ABI-padded to 32B
- `confirmLockMint(bytes32)` ~32B + selector

Priority field calldata overhead is negligible vs SSTORE for rate limit / totalLocked.

## High-ROI optimizations

1. **Batch confirms** for operators:
   `confirmLockMintBatch(bytes32[] calldata ids)` — saves n× base tx cost (~21k each).
2. **`string calldata`** on burn release address (avoid memory copy).
3. **Custom errors** instead of long revert strings (deploy + returndata).

## Low ROI

- Packing priority into calldata: ABI still 32-byte slots.
- Shortening requestId: breaks idempotency.

## Measure

```bash
forge test --gas-report
cast estimate <bridge> "confirmLockMint(bytes32)" <id> --from <op>
```
