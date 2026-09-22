# E2E Validation — Phase 2

PR: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/pull/34

## Local

```bash
git checkout remediation/phase-2-contracts
cd contracts && forge build && forge test -vvv
forge test --match-contract BridgeInvariant -vv
forge test --match-contract BridgeFoundryInvariant -vv
```

## Echidna

```bash
echidna test/echidna/BridgeEchidna.sol --contract BridgeEchidna --config test/echidna/echidna.yaml
```

## Slither

```bash
slither . --filter-paths "lib|node_modules|test" --exclude-dependencies --fail-high
```

## Deploy smoke (anvil)

```bash
forge script script/DeployBAIT.s.sol --rpc-url http://127.0.0.1:8545 --broadcast -vvvv
# Confirm log: WBAIT.bridgeLock set to BridgeLock address
```

## Accept criteria

| ID | Expected |
|----|----------|
| H-01 | Bridge mints; deployer cannot |
| H-02 | No auto-confirm |
| C-02 | totalMinted <= totalLocked |
| C-01 | Timelock script ready |
| Slither | Re-run; do not claim 0 High until clean |
