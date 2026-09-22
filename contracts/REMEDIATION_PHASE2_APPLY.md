# Fase 2 Remediation — Apply Guide

## Changes in this PR

| ID | Issue | Fix |
|----|-------|-----|
| H-01 | DeployBAIT set WBAIT.bridgeLock to deployer | setBridgeLock one-time after BridgeLock deploy |
| H-02 | Auto-confirm on requestLockMint | No auto-confirm; 3 explicit confirms required |
| C-02 | No on-chain conservation invariant | totalLocked / totalMinted + require |
| C-01 | pause() onlyOwner immediate | SetupTimelock.s.sol → TimelockController 48h |

## Files

- `contracts/src/WBAIT.sol`
- `contracts/src/BridgeLock.sol` (follow-up commit if not in this PR yet)
- `contracts/script/DeployBAIT.s.sol`
- `contracts/script/SetupTimelock.s.sol`
- `contracts/test/BridgeInvariant.t.sol`
- `contracts/test/echidna/*`

## Verify

```bash
cd contracts
forge test -vvv
forge test --match-contract BridgeInvariant -vv
```

## After merge

1. Deploy with fixed DeployBAIT.s.sol
2. Run SetupTimelock and acceptOwnership after 48h
3. Point production multisig as Timelock proposer/executor
