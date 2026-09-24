# Diff proposto — README.md + ROADMAP.md (PR docs)

## README.md — seção "Estado atual dos subsistemas" (atualizar)

```diff
 ### Estado atual dos subsistemas
 
 | Subsistema | Estado | Detalhes |
 |---|---|---|
-| Contratos wBAIT + BridgeLock | ✅ Compilado + Testado localmente | 22/22 testes Foundry passando após remediações, Solidity 0.8.20, OZ v5.0.0 |
+| Contratos wBAIT + BridgeLock | ✅ Compilado + Testado localmente | Phase-2: 10/10 testes BAITPhase2 (Timelock + setBridgeLock one-time) PASS em 24/09/2026; Solidity 0.8.20, OZ v5.0.2 |
 | Auditoria CertiK Agentic AI | ⚠️ Remediação local aplicada | H-01 e H-02 corrigidos no código; relatório histórico requer nova execução independente |
 | Parecer Howey | ✅ Completa | LIKELY_NOT_SECURITY, confiança 82% |
-| Validação End-to-End | ⚠️ Validação local | Fluxos locais passam; RPC, broadcast e confirmações de mainnet não foram executados |
+| Validação End-to-End | ⚠️ Produção parcial | Chain height 46k+, 38 agentes, swap fills; settlement on-chain e master_pool ainda incompletos (24/09) |
 | Deploy Mainnet Readiness | ⚠️ Parcial | Alternativas locais documentadas; itens que exigem RPC, ETH e hardware continuam externos |
+| Custódia BTC (PoR) | 🟡 Parcial | `1Kj6epy…` ≈ 2.408 BTC real on-chain; `12vG4z…` vazio; master_pool=0 |
+| AI Store | ✅ Produção | /aistore/ live (Next.js 16 + Pulsar SSE + BAIT commerce) |
```

## README.md — adicionar bloco "Validação 24/09/2026"

```markdown
### Validação de produção — 24/09/2026

| Check | Resultado |
|---|---|
| Chain height / valid | 46346 / true |
| Agents registered | 38 |
| Faucet + Staking APY | 10 BAIT/24h + 7% |
| Swap book fills | 10 fills registrados |
| Offers pending-broadcast | 12 |
| master_pool | {0 addresses, 0 BTC, 0 UTXOs} |
| Explorer non-coinbase | 0 (gap) |
| Custody `1Kj6epy…` (blockstream) | ≈ 2.408 BTC real |
| Forge Phase-2 tests | 10/10 PASS |
| Settlement force script | dry-run OK; execução real requer chaves |
```

## ROADMAP.md — Semana 2 / Go-Live (atualizar status)

```diff
 ### Semana 2 (20–26/09) — 1ª Receita A2A
 
-| [ ] 1ª tx A2A real on-chain
+| [~] 1ª tx A2A real on-chain — fills no orderbook; explorer ainda só coinbase
-| [ ] Swap BTC⇄BAIT com execuções reais
+| [~] Swap BTC⇄BAIT — orderbook vivo; 12 offers pending-broadcast; master_pool=0
 | [x] Faucet + staking 7% APY
-| [ ] 1º job myVideo pago
+| [ ] 1º job myVideo pago (não validado)
+| [x] PoR parcial custody `1Kj6epy…` (~2.408 BTC)
+| [x] Script force_settlement_e2e + checklist operacional
+| [x] Forge tests Phase-2 (10/10)
```

## Arquivos a incluir no PR

1. `docs/GO_LIVE_CHECKLIST_2026-09-23.md` (ou raiz)
2. `docs/POR_CUSTODY_AND_SWEEP_ANALYSIS_2026-09-24.md`
3. `scripts/force_settlement_e2e.py`
4. `contracts/test/BAITPhase2.t.sol` (opcional, se mergear testes adaptados)
5. Atualizações de README.md e ROADMAP.md conforme diffs acima

## Commit message sugerida

```
docs: GO_LIVE + PoR custody + force-settlement E2E (24/09)

- Validação produção height 46k+, 38 agents, 12 pending offers
- PoR on-chain: 1Kj6epy ≈ 2.408 BTC real; 12vG4z vazio
- Script force_settlement_e2e.py (dry-run + checklist)
- Forge Phase-2 tests 10/10 PASS (Timelock + setBridgeLock)
- Dust residual 0.01473073 BTC documentado para sweep
```
