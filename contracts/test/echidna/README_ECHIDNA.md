# Echidna — BridgeLock / WBAIT

## Critical property

```text
totalMinted <= totalLocked
```

## Run

```bash
cd contracts
echidna test/echidna/BridgeEchidna.sol \
  --contract BridgeEchidna \
  --config test/echidna/echidna.yaml \
  --format text
```

Long campaign:

```bash
echidna test/echidna/BridgeEchidna.sol \
  --contract BridgeEchidna \
  --config test/echidna/echidna.yaml \
  --test-limit 500000 \
  --workers 4
```

## Properties

| Function | Guarantees |
|----------|------------|
| `echidna_minted_leq_locked` | CRITICAL conservation |
| `echidna_conservation_holds` | View helper |
| `echidna_supply_under_cap` | Supply ≤ MAX_SUPPLY |
| `echidna_bridge_wired` | bridgeLock wired |
| `echidna_supply_leq_minted` | ERC20 supply ≤ totalMinted |

## CI snippet

```yaml
  echidna:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { submodules: recursive }
      - uses: foundry-rs/foundry-toolchain@v1
      - name: Install Echidna
        run: |
          curl -L https://github.com/crytic/echidna/releases/download/v2.2.6/echidna-2.2.6-x86_64-linux.tar.gz | tar -xz
          sudo mv echidna /usr/local/bin/
      - name: Run Echidna
        working-directory: contracts
        run: |
          echidna test/echidna/BridgeEchidna.sol --contract BridgeEchidna --config test/echidna/echidna.yaml --format text
```

Use Foundry invariants daily; Echidna for long campaigns / nightly CI.
