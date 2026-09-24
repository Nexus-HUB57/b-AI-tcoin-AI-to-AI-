# Echidna + Slither custom detectors (BAIT)

## Echidna invariants

Properties mirror Foundry `InvariantBridge` / `Handler`:

| Property | Meaning |
|----------|--------|
| `echidna_minted_le_locked` | totalMinted ≤ totalLockedOnL1 |
| `echidna_supply_eq_minted` | ERC20 totalSupply == totalMinted |
| `echidna_under_cap` | supply ≤ MAX_SUPPLY |
| `echidna_threshold_is_three` | REQUIRED_CONFIRMATIONS == 3 |
| `echidna_rate_limit_positive` | RATE_LIMIT > 0 |

### Run

```bash
# https://github.com/crytic/echidna/releases
cd contracts && forge build
echidna . --contract EchidnaBridgeTester --config docs/echidna/echidna.yaml
```

Wire `EchidnaBridgeProperties` by deploying Timelock + WBAIT + BridgeLock in a concrete tester.

Foundry parity (CI):
```bash
FOUNDRY_INVARIANT_RUNS=128 FOUNDRY_INVARIANT_DEPTH=40 \
  forge test --match-contract "InvariantBridgeTest|InvariantAdvancedTest"
```

## Slither custom detector

`bait-conservation` — heuristic if a function writes `totalMinted` without referencing `totalLockedOnL1` in the same function.

See `docs/echidna/slither_plugin/` and https://github.com/crytic/slither/wiki/Adding-a-new-detector
