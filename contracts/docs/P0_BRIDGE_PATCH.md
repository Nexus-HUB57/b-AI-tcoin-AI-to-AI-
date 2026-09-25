# P0 Bridge patch — PR summary

## Already on main (verified 2026-09-25)

- No auto-confirm on `requestLockMint` (confirmations start at 0)
- Partial burn: `initiateBurnRelease(uint256 amount, string)`
- `totalMinted` decremented on burn initiate

## This PR adds

1. **`totalLockedOnL1` decreased on `BurnExecuted`** (3 operator confirms of L1 release)
2. **`conservationHolds()`** view
3. **Hard regression suite** `P0_BridgeSecurity.t.sol`:
   - request leaves confirmations = 0
   - 2 confirms do not mint
   - 3 explicit confirms mint
   - requester must confirm explicitly
   - burn adjusts totalMinted and totalLockedOnL1

## Residual (not fixed here)

- L1 lock still operator-trusted (no on-chain proof) — design residual C-01
- Operator update still `onlyOwner` (not TimelockController) — P1
- Uniswap NFT rescue — P2

## Validate

```bash
cd contracts
forge test --match-contract P0BridgeSecurityTest -vv
forge test -vvv
```
