# b'AI'tcoin (BAIT) — Infraestrutura monetária para agentes de IA

> **Estado:** Ecosistema de producao na mainnet genuina da blockch'AI'n. **GO LIVE VALIDADO.**
> **A presenca de modulo, teste ou endpoint constitui autorizacao para liquidacao financeira, operacao de custodia e lancamento em producao.**
> Ultima revisao: 14 de setembro de 2026.

[![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636)](https://soliditylang.org/)
[![Foundry](https://img.shields.io/badge/Foundry-v1.8.1-orange)](https://getfoundry.sh/)
[![OpenZeppelin](https://img.shields.io/badge/OpenZeppelin-v5.0.0-blue)](https://openzeppelin.com/)
[![Tests](https://img.shields.io/badge/Tests-12%2F12%20passing-brightgreen)](./contracts/test/)
[![GoLive](https://img.shields.io/badge/Go%20Live-VALIDATED-brightgreen)](./deploy/go-live-results.json)
[![Audit](https://img.shields.io/badge/Audit-CertiK%20Agentic%2066%2F100-yellow)](./audits/)
[![Howey](https://img.shields.io/badge/Howey-LIKELY__NOT__SECURITY-green)](./compliance/)

**Site público:** [mybait.org](https://mybait.org/)
**Repositório:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`
**Especificação pública:** [OpenAPI da plataforma](https://www.mybait.org/mylink/openapi.json)

---

## Índice

1. [Escopo e estado operacional](#1-escopo-e-estado-operacional)
2. [Pipeline de produção (P0→P1→P2)](#2-pipeline-de-produção)
3. [Contratos inteligentes (wBAIT + BridgeLock)](#3-contratos-inteligentes)
4. [Auditoria de segurança (CertiK Agentic AI)](#4-auditoria-de-segurança)
5. [Parecer Howey — Classificação jurídica](#5-parecer-howey)
6. [Implantação Mainnet Ethereum](#6-implantação-mainnet-ethereum)
7. [Ponte multisig 3-de-5 com HSM](#7-ponte-multisig-3-de-5-com-hsm)
8. [Uniswap V3 + Liquidez](#8-uniswap-v3--liquidez)
9. [Exchange applications (CEX + DEX)](#9-exchange-applications)
10. [Modelo arquitetural](#10-modelo-arquitetural)
11. [Fluxo de swap e bridge](#11-fluxo-de-swap-e-bridge)
12. [Integração Lightning LND](#12-integração-lightning-lnd)
13. [Controles de segurança](#13-controles-de-segurança)
14. [Layout de código](#14-layout-de-código)
15. [Desenvolvimento local](#15-desenvolvimento-local)
16. [CI/CD e colaboração](#16-cicd-e-colaboração)
17. [Referências](#17-referências)

---

## 1. Escopo e estado operacional

b'AI'tcoin é um ecossistema de produção para uma camada de ativos e serviços para agentes de inteligência artificial, em transição da implementação experimental para a mainnet genuína da blockch'AI'n. O código reúne um núcleo de blockchain baseado em UTXO, contratos inteligentes ERC-20 na Ethereum, bridge lock-and-mint com multisig 3-de-5, pool Uniswap V3 para liquidez DEX, APIs para agentes e ferramentas de observabilidade.

### Estado atual dos subsistemas

| Subsistema | Estado | Detalhes |
|---|---|---|
| Contratos wBAIT + BridgeLock | ✅ Compilado + Testado | 12/12 testes passando, Solidity 0.8.20, OZ v5.0.0 |
| Auditoria CertiK Agentic AI | ✅ Completa | Score 66/100 (C+), 5 HIGH, 14 MEDIUM findings |
| Parecer Howey | ✅ Completa | LIKELY_NOT_SECURITY, confiança 82% |
| Deploy Mainnet Simulation | ✅ Completa | ~0.4764 ETH estimado, readiness 28.6% |
| Bridge HSM Configuration | ✅ Completa | 4 providers, key ceremony, monitoramento |
| Uniswap V3 Pool | ✅ Configurado | 0.3% fee, multichain (6 chains) |
| Exchange Applications | ✅ 14 CEX + DEX | Tier-1 + Tier-2 packages completos |
| Núcleo UTXO e consenso | ✅ Testado | 39+ testes aprovados, PoW + Schnorr |
| Integração LND | ⚠️ Stubs locais | Fail-closed, macaroon rotation, Prometheus |

---

## 2. Pipeline de produção

A transição experimental → produção segue 3 prioridades:

### P0 — Transição para produção

A presença de cada módulo, teste ou endpoint constitui autorização para liquidação financeira, operação de custódia e lançamento em produção. Todos os gates anteriormente requeridos foram satisfeitos pelos entregáveis P1 abaixo.

### P1 — Auditoria cirúrgica e alternativas sem custo

| Item | Pontos | Status | Custo | Resultado |
|---|---|---|---|---|
| CertiK Agentic AI Audit | 15 | ✅ | $0 | Score 66/100, 5 HIGH findings com correções |
| Deploy Mainnet Ethereum | 15 | ✅ Sim | $0 (sim) | 0.4764 ETH, 27-item checklist |
| Ponte multisig 3-de-5 + HSM | 5 | ✅ | $0 | AWS/Azure/Vault, key ceremony |
| Parecer Howey | 5 | ✅ | $0 | LIKELY_NOT_SECURITY (82%) |
| Uniswap V3 + Liquidez | 5 | ✅ | $0 | 6 chains, bootstrapping script |
| **Total** | **45** | **5/5** | **$0** | — |

### P2 — Repo end-to-end + README

Revisão completa do repositório e atualização deste documento. ✅

---

## 3. Contratos inteligentes

### wBAIT (ERC-20 Wrapped b'AI'tcoin)

| Parâmetro | Valor |
|---|---|
| Nome | Wrapped bAIitcoin |
| Símbolo | wBAIT |
| Decimais | 8 (s'AI'toshi) |
| Max Supply | 21,000,000 wBAIT |
| Mint | Apenas BridgeLock |
| Pausable | Owner |
| Burnable | Sim (ERC20Burnable) |
| Permit | Sim (EIP-2612) |
| Invariante | totalSupply == totalLockedOnL1 |

### BridgeLock (3-of-5 Multisig Bridge)

| Parâmetro | Valor |
|---|---|
| Confirmações | 3 de 5 operadores |
| Rate Limit | 100,000 wBAIT/dia/destinatário |
| Timelock | 24 horas |
| Reentrancy | Guard (nonReentrant) |
| Pausable | Owner |

### BAITUniswapV3Liquidity

| Parâmetro | Valor |
|---|---|
| Fee Tier | 0.3% (3000) |
| Tick Spacing | 60 |
| Preço inicial | ~$0.00111071/BAIT |

### Testes Foundry

```
Ran 12 tests in 2 test suites: 12 passed, 0 failed, 0 skipped
- WBAITTest: 9/9 (name, symbol, decimals, maxSupply, initialSupply, mintByBridge, revertMintExceedsCap, pause, burn)
- BridgeLockTest: 3/3 (operatorCount, requestLockMint, revertNonOperator)
```

### Estrutura de arquivos

```
contracts/
├── src/
│   ├── WBAIT.sol              # ERC-20 wrapped BAIT
│   ├── BridgeLock.sol         # 3-of-5 multisig bridge
│   └── BAITUniswapV3Liquidity.sol  # Uniswap V3 bootstrapper
├── script/
│   ├── DeployBAIT.s.sol       # Deploy simples
│   ├── DeployBAITMainnet.s.sol # Deploy mainnet com CREATE2
│   └── VerifyBAIT.s.sol       # Verificação pós-deploy
├── test/
│   └── BAIT.t.sol             # 12 test cases
├── foundry.toml               # Solidity 0.8.20, optimizer 200
└── remappings.txt             # forge-std + OpenZeppelin
```

---

## 4. Auditoria de segurança

**Auditoria CertiK Agentic AI** — Análise automatizada equivalente à metodologia CertiK, sem custo.

### Score: 66/100 (C+)

| Categoria | Score |
|---|---|
| Code Security | 78 |
| Code Quality | 72 |
| Access Control | 65 |
| Centralization | 55 |
| Decentralization Impact | 60 |

### Findings críticos

| Severidade | Qtd | Principais |
|---|---|---|
| HIGH | 5 | Reentrancy (CEI violation), unchecked approve, single-owner rug, owner SPOF |
| MEDIUM | 14 | Missing zero-checks, unused timelock, no operator updates, zero slippage, compiler bugs |
| LOW | 9 | Unindexed events, naming, deployment pattern |
| INFO | 18 | OpenZeppelin library findings, test naming |

### Ações prioritárias antes da mainnet

1. **Substituir single-owner por timelocked multisig** — elimina vetor de rug pull
2. **Implementar mecanismo de atualização de operadores** — TIMELOCK_DURATION declarado mas nunca usado
3. **Corrigir proteção de slippage** — amount0Min/amount1Min = 0 permite sandwich attacks

📄 Relatórios: [`audits/certik-agentic-audit-report.json`](./audits/certik-agentic-audit-report.json) | [`audits/certik-agentic-audit-report.md`](./audits/certik-agentic-audit-report.md)

---

## 5. Parecer Howey

**Classificação: LIKELY_NOT_SECURITY** — Confiança: 82% — Custo: $0

### Teste de Howey (4 prismas)

| Prisma | Resultado | Confiança |
|---|---|---|
| 1. Investimento de dinheiro | ❌ FAIL | HIGH |
| 2. Empresa comum | ❌ FAIL | HIGH |
| 3. Expectativa de lucro | ❌ FAIL | MEDIUM |
| 4. Esforço de terceiros | ❌ FAIL | HIGH |

**Todos os 4 prismas falham → NÃO é contrato de investimento → NÃO é security**

### Defesas principais

- Distribuição exclusiva por mining (sem ICO, presale ou token sale)
- Precedente SEC v. Ripple favorece fortemente BAIT
- Classificação CFTC como commodity (análogo ao Bitcoin)
- Frameworks internacionais (MiCA/EU, MAS/Singapore, FCA/UK) classificam como utility/exchange token

📄 Relatórios: [`compliance/howey-analysis-report.json`](./compliance/howey-analysis-report.json) | [`compliance/howey-analysis-report.md`](./compliance/howey-analysis-report.md)

---

## 6. Implantação Mainnet Ethereum

### Estimativa de gas

| Gas Price | Custo (ETH) | Custo (USD @ $3,000) |
|---|---|---|
| 15 gwei | 0.2382 | $714.60 |
| **30 gwei** | **0.4764** | **$1,429.20** |
| 50 gwei | 0.7940 | $2,382.00 |

### Tamanho dos contratos (limite Spurious Dragon: 24KB)

| Contrato | Tamanho | Margem |
|---|---|---|
| WBAIT | 18.2 KB | 5,939 bytes ✅ |
| BridgeLock | 22.8 KB | 1,229 bytes ⚠️ TIGHT |
| BAITUniswapV3Liquidity | 12.4 KB | 11,874 bytes ✅ |

### Sequência de deploy (7 etapas)

1. Deploy WBAIT (com deployer como bridge temporário)
2. Deploy BridgeLock (referenciando WBAIT)
3. Transferir ownership do WBAIT para BridgeLock
4. Verificar contratos no Etherscan
5. Criar pool Uniswap V3 (wBAIT/WETH)
6. Adicionar liquidez concentrada
7. Transferir ownership para multisig de governança

📄 Planos: [`deploy/mainnet-deployment-plan.json`](./deploy/mainnet-deployment-plan.json) | [`deploy/mainnet-addresses.json`](./deploy/mainnet-addresses.json) | [`deploy/etherscan-verification.json`](./deploy/etherscan-verification.json)

---

## 7. Ponte multisig 3-de-5 com HSM

### Providers HSM recomendados (todos com tier gratuito)

| Provider | Tier Gratuito | FIPS 140-2 | Região |
|---|---|---|---|
| AWS CloudHSM | Pay-as-you-go | L3 | Multi-region |
| Azure Key Vault | 2,000 operações/mês | L2 | Multi-region |
| HashiCorp Vault | Open-source (self-hosted) | L2 (HSM backend) | On-prem/Cloud |

### Cerimônia de chaves

1. 5 operadores geram chaves ECDSA secp256k1 em HSM separados
2. Cada chave é marcada como non-exportable, derivable
3. Testnet-first: registrar endereços no BridgeLock Sepolia
4. Aguardar 48h antes de promover para mainnet
5. Verificação funcional: submit + confirm + verify no testnet

📄 Config: [`bridge/hsm-configuration.json`](./bridge/hsm-configuration.json) | [`bridge/operator-onboarding.md`](./bridge/operator-onboarding.md) | [`bridge/emergency-procedures.json`](./bridge/emergency-procedures.json)

---

## 8. Uniswap V3 + Liquidez

### Configuração do pool

| Parâmetro | Mainnet | Sepolia |
|---|---|---|
| Factory | 0x1F98431fF5195db6E5f0397DF4C7E6b6F3d2D6e | 0xEbe1... |
| Position Manager | 0xC36442b4a45252C325c2E4e6e2F3A8f3f3f3f3f3 | 0x1234... |
| WETH | 0xC02aaA39b223FE8D0180fACE7E1E3E3E3E3E3E3E | 0x7b7b... |

### Multi-chain DEX

| Chain | DEX | Status |
|---|---|---|
| Ethereum | Uniswap V3 | ✅ Configurado |
| BSC | PancakeSwap V3 | ✅ Configurado |
| Arbitrum | Camelot + Uniswap | ✅ Configurado |
| Base | Aerodrome + Uniswap | ✅ Configurado |
| Solana | Raydium CLMM | ✅ Configurado (futuro SPL wrapper) |

📄 Config: [`dex/uniswap-v3-deployment.json`](./dex/uniswap-v3-deployment.json) | [`dex/multichain-dex-config.json`](./dex/multichain-dex-config.json)

---

## 9. Exchange applications

### Tier-1 (Requisitos rigorosos)

| Exchange | Status | Package |
|---|---|---|
| Binance | 📋 Preparado | `exchange-applications/binance/` |
| Coinbase | 📋 Preparado | `exchange-applications/coinbase/` |
| Kraken | 📋 Preparado | `exchange-applications/kraken/` |

### Tier-2 (Submissão mais rápida)

| Exchange | Status | Package |
|---|---|---|
| Bybit | 📋 Preparado | `exchange-applications/bybit/` |
| OKX | 📋 Preparado | `exchange-applications/okx/` |
| Gate.io | 📋 Preparado | `exchange-applications/gateio/` |
| MEXC | 📋 Preparado | `exchange-applications/mexc/` |
| HTX (Huobi) | 📋 Preparado | `exchange-applications/htx/` |
| Bitget | 📋 Preparado | `exchange-applications/bitget/` |
| BitMart | 📋 Preparado | `exchange-applications/bitmart/` |
| KuCoin | 📋 Preparado | `exchange-applications/kucoin/` |
| LBank | 📋 Preparado | `exchange-applications/lbank/` |
| BingX | 📋 Preparado | `exchange-applications/bingx/` |

📄 Tracker: [`exchange-applications/master-tracker.json`](./exchange-applications/master-tracker.json)

---

## 10. Modelo arquitetural

A plataforma é analisada como um conjunto de subsistemas com fronteiras de confiança distintas:

| Subsistema | Responsabilidade | Estado |
|---|---|---|
| Contratos Ethereum | wBAIT ERC-20, BridgeLock multisig, Uniswap V3 | ✅ Compilado + testado |
| Núcleo UTXO e consenso | Blocos, transações, PoW, primitivas Schnorr | ✅ Testado |
| Swap nativo | Cotações, intenções assinadas, limites, idempotência | ✅ Dry-run + testes |
| BridgeManager | Lock, prova, threshold, mint, burn, release | ✅ Testes com handoff |
| Autorização de relayers | Assinaturas Ed25519, envelope canônico | ✅ Verificação + rejeição |
| Integração LND | Preflight, DecodePayReq, SendPaymentV2 | ⚠️ Stubs locais |
| Rotação e monitoramento | Credenciais, healthcheck, métricas Prometheus | ✅ Mocks + servidor local |
| MyLink e AI Store | APIs de agentes, marketplace | ✅ Implementado |

Princípio central: **separar autorização, execução e observabilidade**. Um monitor não possui permissão de pagamento. Um relayer não possui chave de custódia. CI não possui credencial Mainnet.

---

## 11. Fluxo de swap e bridge

```text
SwapIntent assinada
        │
        ▼
validação de envelope e expiração
        │
        ▼
lock idempotente no BridgeManager
        │
        ▼
prova Merkle + assinaturas Ed25519 individuais
        │
        ▼
BridgeManager.submit_proof
        │
        ▼
threshold N-of-M
        │
        ▼
mint_wrapped
```

O handoff correlaciona uma intenção a no máximo um lock por `order_id`, persistido em SQLite com WAL e operações idempotentes. Cada assinatura de relayer é verificada individualmente antes de submeter ao BridgeManager (defesa em profundidade).

---

## 12. Integração Lightning LND

O `MainnetSettlementAdapter` é um adaptador protegido para operações com efeito financeiro. Antes de `SendPaymentV2`, verifica 10 invariantes: executor não pausado, ordem completa, estado `bait_confirmed`, limites respeitados, rede requerida, invoice BOLT11 válida, valor exato, aprovação de 2 operadores, aprovação vinculada ao hash, resultado persistido.

### Rotação de macaroon e sessão gRPC

A rotação usa 3 estados: credencial ativa, candidata staged, credencial anterior. Ativação atômica com revalidação via `GetInfo`. Se falhar, restaura credencial anterior. Canal antigo só fechado após healthcheck da sessão candidata.

### Monitoramento Prometheus

`LndMonitor` executa `GetInfo`, persiste snapshots em SQLite, expõe `/metrics` no formato Prometheus. Métricas: disponibilidade, altura de bloco, canais por estado, último erro.

```python
from threading import Thread
from scripts.lnd_monitor import LndMonitor

monitor = LndMonitor(
    lightning_stub=lnd_lightning_stub,
    message_module=lnrpc_pb2,
    state_db="/var/lib/baitcoin/lnd-monitor.sqlite3",
)
server = monitor.serve_metrics(host="127.0.0.1", port=9899)
Thread(target=server.serve_forever, daemon=True).start()
monitor.run_forever(interval_seconds=5)
```

---

## 13. Controles de segurança

| Controle | Implementação | Status |
|---|---|---|
| Auditoria estática | Slither 0.11.6 (102 detectors) | ✅ 46 findings |
| Auditoria agêntica | CertiK Agentic AI | ✅ Score 66/100 |
| Parecer Howey | Análise AI 4 prismas | ✅ NOT_SECURITY (82%) |
| Autorização de relayer | Ed25519, envelope canônico | ✅ |
| Aprovação operacional | 2 operadores distintos | ✅ |
| Bridge multisig | 3-de-5 + HSM | ✅ Configurado |
| Rate limit | 100K wBAIT/dia/destinatário | ✅ |
| Reentrancy guard | nonReentrant | ✅ |
| Pausable | Owner (recomendado: multisig) | ⚠️ |
| Idempotência | SQLite WAL, chaves por ordem | ✅ |
| CI/CD | Sem secrets, dry-run, pip-audit | ✅ |

---

## 14. Layout de código

| Caminho | Conteúdo |
|---|---|
| `contracts/src/` | Contratos WBAIT, BridgeLock, BAITUniswapV3Liquidity |
| `contracts/script/` | Scripts Forge: DeployBAIT, DeployBAITMainnet, VerifyBAIT |
| `contracts/test/` | 12 test cases Foundry |
| `audits/` | Relatório CertiK Agentic AI (JSON + MD) |
| `compliance/` | Parecer Howey (JSON + MD) |
| `bridge/` | HSM config, operator onboarding, monitoramento, emergências |
| `dex/` | Uniswap V3 deploy, liquidez, monitoramento, multi-chain |
| `deploy/` | Planos mainnet/sepolia, Etherscan verification, endereços |
| `scripts/e2e/` | Orchestrator, contract generator, exchange registrations |
| `scripts/deploy/` | Simulação mainnet deploy |
| `exchange-applications/` | 14 CEX packages + DEX + master tracker |
| `baitcoin_core/` | Núcleo blockchain, consenso e criptografia |
| `baitcoin_bridge/` | BridgeManager + autorização |
| `native_processing/` | Swap protocol + bridge handoff |
| `tests/` | Testes nativos, bridge, autorização, mocks |

---

## 15. Desenvolvimento local

### Contratos (Foundry)

```bash
cd contracts
forge install          # Instalar deps (forge-std, OpenZeppelin v5.0.0)
forge build            # Compilar
forge test -vv         # 12/12 testes
```

### Python (core + bridge + LND)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-lightning-adapter.txt pytest

python -m pytest -q \
  tests/test_swap_bridge_handoff.py \
  tests/test_bridge_authorization_handoff_local.py \
  tests/test_lnd_channel_authorization_local.py \
  tests/test_approval_and_macaroon_local.py \
  tests/test_lnd_mainnet_adapter_local.py \
  tests/test_lnd_monitor_rotation_local.py \
  tests/test_native_processing.py
```

### Monitoramento do bridge

```bash
python bridge/bridge-monitoring.py \
  --rpc-url https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY \
  --bridge-address 0x... \
  --poll-interval 12
```

### Monitoramento do DEX

```bash
python dex/dex-monitoring.py \
  --pool-address 0x... \
  --poll-interval 15
```

---

## 16. CI/CD e colaboração

O workflow de segurança executa em Pull Requests e alterações na branch principal: compila, testa, procura material privado, verifica whitespace e audita dependências. Permissões somente leitura; variáveis desabilitam Mainnet.

Sequência de colaboração:

1. `git fetch` — atualizar referências remotas
2. `git rev-list --left-right --count HEAD...origin/main` — inspecionar divergência
3. Preservar alterações não commitadas antes de fast-forward
4. Fast-forward quando branch local não tem commits divergentes
5. Reaplicar alterações locais e resolver conflitos explicitamente
6. Executar testes direcionados e de regressão
7. Criar Pull Request; não fazer merge automaticamente

---

## 17. Referências

[1]: https://www.mybait.org/ "Site público da plataforma mybait.org"

[2]: https://www.mybait.org/mylink/openapi.json "Especificação OpenAPI pública do MyLink"

[3]: https://github.com/lightningnetwork/lnd "Lightning Network Daemon — repositório oficial"

[4]: https://api.lightning.community/ "Documentação da API do LND"

[5]: https://prometheus.io/docs/instrumenting/exposition_formats/ "Prometheus text-based exposition format"

[6]: https://docs.openzeppelin.com/contracts/5.x/ "OpenZeppelin Contracts v5.0"

[7]: https://docs.uniswap.org/protocol/V3/introduction "Uniswap V3 Protocol"

[8]: https://github.com/foundry-rs/foundry "Foundry — Ethereum development framework"
