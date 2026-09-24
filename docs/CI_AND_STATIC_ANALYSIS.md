# CI, Slither detectors & Foundry coverage

## CI jobs (Foundry)

| Job | Blocks merge? | Role |
|---|---|---|
| **forge build & test** | Yes (via CI gate) | Unit + BridgeInvariant lifecycle |
| **forge lint** | Yes | `src/` only |
| **Slither** | No (`continue-on-error`) | Static analysis High |
| **forge coverage** | No | Summary report (advisory) |
| **CI gate** | Required status | test + lint must succeed |

### Slither job fix (Foundry 1.x)

Previous failure was **not** a detector finding:

```
KeyError: 'output'  # crytic_compile hardhat_like_parsing
```

Cause: `ignore-compile: true` + Foundry artifact layout without the expected `"output"` key.

**Fix:** remove `ignore-compile`; let crytic-compile drive `forge`; filter `lib|script|test`.

---

## Slither detector types (impact levels)

Trail of Bits / Crytic classifiers (simplified):

| Impact | Meaning | Typical examples |
|---|---|---|
| **High** | Likely exploitable or severe fund/access risk | Reentrancy with state after external call, arbitrary `delegatecall`, unprotected `selfdestruct`, critical access-control bypass |
| **Medium** | Real risk under conditions / design smell | Missing zero-address checks on sensitive paths, dangerous ERC20 approve patterns, timestamp dependence for critical logic |
| **Low** | Limited impact or hard to exploit | Unindexed events, unused returns, suboptimal visibility |
| **Informational** | Style / best practice / noise from deps | Naming, version pragmas, OZ internal patterns |
| **Optimization** | Gas / structure only | Storage packing, unnecessary SLOAD |

Detectors are **heuristic**. Always triage:

1. Confirm reachable path in *this* contract (not only `lib/`).
2. Check CEI / `nonReentrant` / multisig already mitigate.
3. Prefer Foundry invariant + unit regression over silencing High without review.

Common detector *families* (names vary by Slither version):

- **reentrancy-*** — external call ordering
- **arbitrary-send-eth / controlled-delegatecall** — value / code injection
- **suicidal / uninitialized-state** — destructive or bad init
- **tx-origin** — auth via `tx.origin`
- **unchecked-transfer** — ERC20 false success
- **timestamp / block-number** — miner influence
- **naming-convention / solc-version** — often excluded in CI noise filters

Our CI excludes low-signal: `naming-convention`, `solc-version`, `low-level-calls` (review offline if needed).

---

## Foundry coverage

### Commands

```bash
cd contracts

# Table: % lines / statements / branches / functions
forge coverage --report summary

# LCOV for Codecov / genhtml
forge coverage --report lcov
# genhtml lcov.info -o coverage/

# Restrict to suites that compile under Phase-2
forge coverage --report summary \
  --match-contract "WBAITTest|BridgeLockTest|BAITPhase2Test|BridgeInvariantTest"
```

### What the numbers mean

| Metric | Meaning |
|---|---|
| **Lines** | Executable source lines hit at least once |
| **Statements** | Individual statements |
| **Branches** | `if` / `require` / ternary arms |
| **Functions** | Functions entered |

Coverage ≠ security. High % with weak invariants can still miss economic bugs. Pair with:

- `forge test` unit + lifecycle
- `forge test --match-contract Invariant*` stateful fuzz
- Slither High triage when the job actually emits findings

### Notes

- Coverage needs a successful compile of targeted files.
- Legacy `script/Deploy*` / `TestBridge*` may still use pre–Phase-2 constructors; skip them until migrated.
- CI runs coverage as **advisory** (`continue-on-error`).
