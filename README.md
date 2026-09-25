# b'AI'tcoin (BAIT) — Infraestrutura monetária para agentes de IA

> **Estado:** Código e validações locais em evolução. Os testes locais não comprovam deploy, custódia ou liquidação em mainnet.
> **A presença de módulo, teste ou endpoint não autoriza liquidação financeira, operação de custódia ou lançamento em produção.**
> Última revisão: **24 de setembro de 2026** (Phase-2 bridge H-02, CI gate, Slither job fix).

[![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636)](https://soliditylang.org/)
[![Foundry](https://img.shields.io/badge/Foundry-stable-orange)](https://getfoundry.sh/)
[![OpenZeppelin](https://img.shields.io/badge/OpenZeppelin-v5.0.2-blue)](https://openzeppelin.com/)
[![CI gate](https://img.shields.io/badge/CI%20gate-Foundry%20test%20%2B%20lint-brightgreen)](./.github/workflows/foundry-ci.yml)
[![Slither](https://img.shields.io/badge/Slither-advisory%20(Foundry%20native)-lightgrey)](./docs/CI_AND_STATIC_ANALYSIS.md)

**Site público:** [mybait.org](https://mybait.org/)  
**Repositório:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`  
**CI / static analysis:** [`docs/CI_AND_STATIC_ANALYSIS.md`](./docs/CI_AND_STATIC_ANALYSIS.md) · [`docs/CI.md`](./docs/CI.md)

---

## Escopo rápido (2026-09-24)

| Área | Estado |
|---|---|
| **BridgeLock** | H-02 (sem auto-confirm) + burn parcial + `consumedL1TxIds` / rate reserve |
| **WBAIT** | ERC-20 8 dec, max 21M, mint só BridgeLock, Timelock pause |
| **Foundry CI** | Jobs `forge build & test` + `forge lint` → **CI gate** (obrigatório) |
| **Slither** | Advisory; job sem `ignore-compile` (evita `KeyError: output` no Foundry 1.x) |
| **Coverage** | `forge coverage --report summary` (advisory no CI) |
| **Mainnet broadcast** | **NO-GO** até Safe + 5 operators produção + checklist assinado |

### Contratos (Phase-2)

| Contrato | Notas |
|---|---|
| `WBAIT.sol` | `constructor(bridge, timelock)` + `initializeBridgeLock` |
| `BridgeLock.sol` | `constructor(wbait, timelock, operators[5])`; 3 confirms explícitos |
| `FoundersVesting.sol` | `Ownable(initialOwner)` (OZ v5) |

### Desenvolvimento local

```bash
cd contracts
forge install
forge test --match-contract "WBAITTest|BridgeLockTest|BAITPhase2Test|BridgeInvariantTest" -vv --summary
forge coverage --report summary --match-contract "WBAITTest|BridgeLockTest|BAITPhase2Test|BridgeInvariantTest"
# optional: make ci
```

### CI/CD

Workflow: [`.github/workflows/foundry-ci.yml`](./.github/workflows/foundry-ci.yml)

| Job | Blocks merge? |
|---|---|
| forge build & test | **Yes** (via CI gate) |
| forge lint | **Yes** |
| Slither | No (`continue-on-error`) |
| forge coverage | No |
| **CI gate** | Require this check on `main` |

Detalhes de detectors Slither e métricas de coverage: **[`docs/CI_AND_STATIC_ANALYSIS.md`](./docs/CI_AND_STATIC_ANALYSIS.md)**.

---

## Documentação histórica

O restante do material operacional (Howey, exchange packs, HSM, Uniswap, LND, go-live checklists) permanece nos paths originais (`deploy/`, `audits/`, `compliance/`).  
**Claims de “100% readiness / mainnet validated” em docs legados não substituem o gate atual:** testes locais + CI verde ≠ broadcast mainnet.

**Site / API:** [mybait.org](https://mybait.org/) · [OpenAPI](https://www.mybait.org/mylink/openapi.json)
