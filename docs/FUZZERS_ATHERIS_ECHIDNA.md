# Atheris + Echidna + Foundry — BAIT bridge fuzzers

## Stack

| Layer | Tool | What it fuzzes |
|-------|------|----------------|
| L0 | **Atheris** (Python) | Pure model of conservation / rate / burn |
| L1 | **Foundry** invariant | On-chain Solidity (CI gate) |
| L2 | **Echidna** | On-chain property mode (`EchidnaBridgeTester`) |

## EchidnaBridgeTester

Path: `contracts/test/EchidnaBridgeTester.sol`

- Deploys TimelockController + WBAIT + BridgeLock (Phase-2)
- Operators: `0x10000` … `0x50000` (must match `test/echidna.yaml` senders)
- Targets: `requestLock`, `confirmLock`, `confirmByIndex`, `burnPartial`
- Properties: `echidna_minted_le_locked`, `supply_eq_minted`, `under_cap`, threshold, rate limit, 5 ops

```bash
cd contracts
forge build
echidna . --contract EchidnaBridgeTester --config test/echidna.yaml
```

## Atheris

Path: `fuzz/atheris_bridge_props.py`

- Coverage-guided if `pip install atheris`
- Else deterministic random fallback (20k steps, seed `0xBA17`)
- Same invariants as on-chain model

```bash
pip install atheris   # optional
python3 fuzz/atheris_bridge_props.py
./fuzz/run_fuzzers.sh atheris
./fuzz/run_fuzzers.sh all
```

## Analysis notes

1. **Atheris** catches logic bugs in the *model* fast; does not replace EVM semantics (reentrancy, gas, ERC20 quirks).
2. **Echidna** explores real bytecode + sender set; needs binary or Docker.
3. **Foundry** remains merge gate (`CI gate` = test + lint).
4. Divergence Atheris vs Echidna → investigate: model bug or Solidity path not mirrored.

## Exit criteria (manual)

- [ ] Atheris/fallback 20k+ steps no invariant break
- [ ] Foundry BridgeInvariant + Invariant* green
- [ ] Echidna 50k tests: all `echidna_*` pass (no falsifying sequence)
