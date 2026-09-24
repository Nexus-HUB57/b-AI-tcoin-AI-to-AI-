# Snippet to fold into README § CI/CD

> Status as of 2026-09-24 (post PR #55–#60).

## CI/CD (Foundry)

Workflow: `.github/workflows/foundry-ci.yml`

| Check | Required | Notes |
|---|---|---|
| forge build & test | **Yes** | H-02 / partial burn / rate-limit suites |
| forge lint (`src/`) | **Yes** | Errors fail; warnings OK |
| **CI gate** | **Yes** | Branch protection should require this job |
| Slither | Advisory | Foundry-native compile (no `ignore-compile`) |
| forge coverage | Advisory | `forge coverage --report summary` |

### Local parity

```bash
cd contracts
make ci   # or: forge test --match-contract "WBAITTest|BridgeLockTest|BAITPhase2Test|BridgeInvariantTest"
forge coverage --report summary --match-contract "WBAITTest|BridgeLockTest|BAITPhase2Test|BridgeInvariantTest"
```

### Docs

- `docs/CI.md` — job matrix
- `docs/CI_AND_STATIC_ANALYSIS.md` — Slither detector types + coverage
- Mainnet broadcast remains **NO-GO** until Safe + operators production + checklist signed
