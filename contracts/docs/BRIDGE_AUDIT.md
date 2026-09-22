# Bridge Contract Security Audit — BAIT/wBAIT

**Scope:** BridgeLock.sol, WBAIT.sol, BAITUniswapV3Liquidity.sol  
**Branch:** remediation/phase-2-contracts  
**Type:** Engineering security review (not a third-party audit certificate)

## Executive summary

| Severity | Open (post phase-2) | Fixed in PR #34 |
|----------|---------------------|-----------------|
| Critical residual | 1 (L1 trust) | deploy bug, on-chain counters |
| High | 2 | auto-confirm removed |
| Medium | 4 | — |

## Critical residual

### C-R1 — L1 lock not verifiable on-chain
`totalLocked` increases on operator `requestLockMint` with no L1 proof. 3 colluding operators can mint unbacked wBAIT.

**Mitigation path:** L1 proofs / higher threshold / global daily mint cap / explicit user-facing trust disclosure.

## High

### H-R1 — pause() still onlyOwner immediate
Run SetupTimelock + acceptOwnership before mainnet.

### H-R2 — Rate limit checked at request, charged at execute
Parallel pending requests for same recipient can sum above RATE_LIMIT after confirms.

**Fix:** Reserve quota on request, or re-check in `_executeLockMint` before mint.

## Medium

- **M-01** Burn always uses full balance — add `amount` param
- **M-02** totalLocked never decreases (pending requests + burns)
- **M-03** No lock request expiry/cancel
- **M-04** Uniswap helper: WETH funding assumptions; no NFT rescue; single positionTokenId

## Low

- Duplicate operator addresses in constructor reduce real diversity
- l1TxId not forced unique
- l1ReleaseAddress format unchecked
- CONTRACTS.md still inaccurate vs code/Slither

## Controls OK after PR #34

- onlyBridge mint, setBridgeLock once, no auto-confirm, 3 distinct confirms
- nonReentrant on mint execute + burn
- supply cap 21M, Ownable2Step, operator update 24h timelock
- conservation check totalMinted <= totalLocked on execute

## Priority before mainnet

1. Timelock ownership (H-R1)
2. Document C-R1 trust model
3. Fix rate-limit reservation (H-R2)
4. Partial burn (M-01)
5. External audit

Full narrative: see remediation package BRIDGE_AUDIT.md locally if mirrored.
