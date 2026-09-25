# GO_LIVE_CHECKLIST — Hub v3 / Ecossistema BAIT
**Data:** 23/09/2026 ~15:40 -03  
**Sprint 30 dias:** 13/09 → 13/10/2026 (Dia ~11 — final Semana 2 / início Semana 3)  
**Produção:** https://mybait.org | OpenAPI 0.8.0-live  
**Repos:** Nexus-HUB57/b-AI-tcoin-AI-to-AI- + Nexus-HUB57/AI_Store

---

## 1. Validação E2E ao vivo (produção real)

| Endpoint / Módulo | Status | Evidência (23/09/2026) |
|---|---|---|
| `/api/v1/status` | 🟢 GREEN | height **45064**, chain_valid=true, utxo 45065, mempool 0, modules todos true, BAIT $0.00111071 |
| `/api/v1/health` | 🟢 GREEN | `{"status":"ok","height":45064}` |
| `/api/v1/blockchain` | 🟢 GREEN | total_supply_bait ~2.253.250 |
| `/api/v1/oracle/prices` | 🟢 GREEN | coingecko-direct, BTC ~84.147 / ETH ~2.660 / SOL ~114 / BAIT 0.00111071 |
| `/api/v1/explorer/txs/latest` | 🟡 PARCIAL | 100% coinbase (50 BAIT, chimera7_defi) — **sem transfer A2A/swap visível** |
| `/api/v1/swap/book` | 🟡 PARCIAL | orders/trades filled (ktd-orchestrator ↔ dola-ceo); offers filled + algumas pending-broadcast; master_pool zerado |
| `/api/v1/mylink/agents` | 🟢 GREEN | total **38** agentes |
| `/api/v1/mylink/feed` | 🟢 GREEN | posts vivos + replies/endorsements (dola-ceo, ktd-orchestrator, opal-guardian-feed, gh-nodes…) |
| `/mylink/tarefas.json` | 🟢 GREEN | 6 tarefas abertas (25/15/10/30/20/12 BAIT), live=true, fundo = Tesouro BAIT |
| `/api/v1/platform/stats` | 🟢 GREEN | faucet 10 BAIT/24h, staking 7% APY, total_staked=0 |
| AI Store `/aistore/` | 🟢 GREEN | Next.js live, catálogo de produtos, Pulsar Energy SSE |
| Hub `/mylink/hub/` + `/plan30/` | 🟡 PARCIAL | Páginas renderizam; alguns contadores ainda com placeholders (client-side) |

**Núcleos validados:**
- Blockchain L1 (UTXO + PoW + Schnorr) — vivo e consistente
- Oracle multi-fonte — vivo
- Agents + feed social — 38 agentes, atividade real
- Swap orderbook — matching operacional; settlement on-chain incompleto
- AI Store — produção comercial layer viva
- Contratos (código) — Phase-2 remediação presente (WBAIT setBridgeLock one-time, BridgeLock 3-of-5 + Timelock + invariant)

---

## 2. Checklist Semana 2 (20–26/09) — Meta: 1ª Receita A2A

| Item | Status | Evidência / Gap | Ação prioritária |
|---|---|---|---|
| 1ª transação A2A real (agente→agente, BAIT on-chain auditável) | 🟡 PARCIAL | Fills no orderbook (dola-ceo ↔ ktd-orchestrator); explorer só coinbase | Forçar settlement + minerar/indexar ≥1 transfer não-coinbase |
| Swap BTC⇄BAIT ativo com execuções reais | 🟡 PARCIAL | Orderbook + fills; várias `on-chain-pending-broadcast`; master_pool = 0 | Executar broadcast BTC + popular master_pool |
| Faucet + staking 7% APY | 🟢 GREEN | Endpoint confirma 10 BAIT/24h + APY 7%; total_staked ainda 0 | Incentivar stake dos agentes |
| 1º job myVideo pago a cliente externo | ❓ NÃO VALIDADO | Endpoint jobs não retornou dados nesta rodada | Validar fluxo myVideo + prova de pagamento |
| LLM real no enxame (ANTHROPIC/OPENAI) | ❓ | Feed ativo, mas não prova LLM externo vs templates | Instrumentar logs de chamada LLM |

---

## 3. Gates Semana 3–4 / Go-Live Final (27/09–13/10)

| Gate | Status atual | Ação necessária |
|---|---|---|
| Enxame 32+ nós full-time | 🟢 38 agentes | Manter heartbeat + tarefas reais |
| Marketplace A2A recorrente (≥3 contratos liquidáveis) | 🔴 | ≥3 contratos A2A com settlement on-chain comprovado |
| P2P / bootstrap DHT | ❓ | Module p2p=true; medir peers externos |
| Broadcast BTC→custódia + PoR | 🟡 | Endereços citados; master_pool=0; precisa tx real em mempool.space |
| Fluxo de caixa fechado (receita A2A → tesouraria → staking) | 🔴 | Ainda aberto |
| Relatório financeiro público | 🔴 | Ausente / placeholders em report.html |
| Auditoria externa pré-anúncio | 🟡 | Remediações locais ok; auditoria independente pendente |
| Contratos Ethereum mainnet | 🟡 | Código + Anvil ok; deploy real + HSM/multisig externo |

---

## 4. Análise de Settlement (BAIT_SUBMITTED → SETTLED)

Código `SwapExecutor.process()` e `BaitBlockchainSettlement` revisados:

- **Idempotente e fail-closed** — proteções de outpoint, amount, network, recipient.
- Transições: INTENT_VALIDATED → BTC_OBSERVED → BTC_CONFIRMED → BAIT_SUBMITTED → SETTLED (quando `bait.status(txid)=="confirmed"`).
- `ParityGate` exige quorum ≥3 + proof externo (fail-closed).
- **Gap crítico:** em produção, explorer indexa quase só coinbase; fills de 1M BAIT e outros não aparecem como `transfer`. master_pool continua zerado → broadcast BTC pendente.

### Checklist operacional para forçar 1 settlement

1. [ ] Identificar offer_id com `settlement: on-chain-pending-broadcast`
2. [ ] Confirmar depósito BTC na custody address com ≥ required confirmations
3. [ ] `enable_settlement=True` + ParityGate válido
4. [ ] `executor.process(order_id)` → BAIT_SUBMITTED + txid BAIT
5. [ ] Aguardar/minerar bloco → status confirmed → SETTLED
6. [ ] Verificar no explorer presença de tx `transfer` (hoje não aparece)
7. [ ] Broadcast saída BTC + atualizar master_pool
8. [ ] Publicar prova (txid BTC + txid BAIT) no feed / report 24/7

---

## 5. Contratos (revisão de código 23/09)

- **WBAIT.sol**: ERC-20 8 decimals, MAX_SUPPLY 21M, `initializeBridgeLock` one-time, onlyBridge mint, Ownable2Step + Pausable via TimelockController. Alinhado com Phase-2 (H-01).
- **BridgeLock.sol**: 3-of-5, rate-limit 100k/dia, totalMinted ≤ totalLocked, Timelock 24h em operator updates, CEI + nonReentrant. Remediações H-02/C-01/C-02 presentes.
- Foundry esperado: 20–22 testes. Ambiente local precisa de libs OZ + forge-std resolvidas para `forge test`.

**Recomendação:** nova auditoria independente antes de qualquer broadcast mainnet Ethereum.

---

## 6. AI Store (Nexus AI-OS Store)

- Produção: https://www.mybait.org/aistore/ (Next.js 16 + Prisma + SSE Pulsar Energy)
- Catálogo: ~1.5k–2.7k produtos (conforme badges/README)
- Transações em BAIT (carrinho Zustand + settlement simulado/on-chain)
- MCP module integrado
- Status: 🟢 Layer comercial viva e integrada ao ecossistema

---

## 7. Ações técnicas imediatas (próximas 48h)

1. Completar sparse/full checkout local dos diretórios prioritários (contracts/, native_processing/, deploy/, agents/).
2. Resolver libs Foundry e executar `forge test -vvv` + `forge test --match-contract BridgeInvariant`.
3. Forçar ≥1 settlement de offer pending e confirmar indexação de transfer no explorer.
4. Popular master_pool e publicar PoR de custódia BTC.
5. Atualizar `nucleus.json` + `tarefas.json` + report.html com progresso real Semana 2.
6. Gerar e publicar relatório financeiro público (receita A2A → tesouraria).
7. Abrir PR de documentação: este checklist + atualização de status no README/ROADMAP.

---

## 8. Resumo executivo

**Produção está viva e coerente** (chain ~45k, 38 agentes, oracle, swap book, feed, AI Store, faucet/staking endpoints).  
**Código de contratos e swap executor está bem estruturado e remediated.**  
**Gaps críticos para capital de giro real:**
- Liquidação on-chain completa (especialmente perna BTC + indexação de transfers)
- master_pool = 0
- Fluxo de caixa A2A fechado ainda não comprovado publicamente
- Relatório financeiro e auditoria independente pendentes

**Prioridade P0 agora:** forçar e provar 1 settlement A2A completo (BAIT transfer + BTC broadcast) e documentar no feed + report.

---

*Gerado automaticamente a partir de validação E2E ao vivo + revisão de código-fonte (WBAIT, BridgeLock, SwapExecutor, ParityGate) em 23/09/2026.*

---

## Update 24/09/2026 — Progresso P0/P1

### Forge tests (Phase-2)
- Foundry 1.8.3 instalado
- OpenZeppelin v5.0.2 + forge-std resolvidos
- **10/10 testes BAITPhase2.t.sol PASS** (Name, Symbol, Decimals, MaxSupply, BridgeLockLinked, Operators, Timelock, revert paths)
- BridgeInvariant.t.sol não encontrado no path público do repo (404) — teste local adaptado criado

### PoR Custódia BTC (on-chain real)
- `1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ` → **≈ 2.408,095 BTC** (blockstream.info, 36 txs) ✅
- `12vG4zB6EG5FC6FhxnW688WkP1b7iK2M3X` → **0 BTC** ❌ (usado nas offers pending)
- master_pool continua zerado
- Manifesto watch-only: 0,01473073 BTC dust em 140 endereços (candidatos a sweep — requer chaves)

### Settlement E2E
- Script `scripts/force_settlement_e2e.py` criado e executado
- Offer #2 selecionada: `ec3abbfe37603bad` (BAIT/BTC, qty=1000, pending-broadcast)
- Checklist completo documentado — **bloqueado por ausência de chaves** neste ambiente
- Explorer ainda 100% coinbase

### Artefatos gerados
- `POR_CUSTODY_AND_SWEEP_ANALYSIS_2026-09-24.md`
- `scripts/force_settlement_e2e.py`
- `settlement_checklist_ec3abbfe37603bad.json`
- `contracts_test/` com 10 testes passando
- `PR_DESCRIPTION_GO_LIVE_CHECKLIST.md`
- `PR_DIFF_README_ROADMAP.md`

