# Gas — priority fields vs bucket queue vs heap

## BridgeLock (current): priority + createdAt + rate reserve

| Item | Delta gas (order of magnitude) |
|------|--------------------------------|
| Extra SSTORE pack priority/createdAt | ~5k–20k |
| dailyMinted reserve on request | ~5k warm / ~20k cold |
| Event + uint8 | ~375+ |
| **Typical overhead per request** | **~15k–40k** |

No loops. Mainnet-acceptable.

## Bucket queue library (optional)

| Op | Complexity | Est. gas |
|----|------------|----------|
| enqueue | O(1) | ~40k–65k |
| dequeue | O(1) | ~15k–30k |
| peekNext | O(3) | ~3k–8k |
| binary heap insert | O(log n) | 100k+ at scale |

Prefer buckets over heap for discrete levels 0..2.

## Validate

```bash
forge test --gas-report
forge snapshot
```
