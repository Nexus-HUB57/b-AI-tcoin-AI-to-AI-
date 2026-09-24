# Auditoria GO Mainnet + Pool Público/Externo — Blockch'AI'n

**Data:** 2026-09-24  
**Escopo:** repo `Nexus-HUB57/b-AI-tcoin-AI-to-AI-` + produção `mybait.org`  
**Decisão:** **NO-GO** para capital de giro / liquidação pública até gates abaixo  
**Tipo:** revisão de engenharia + evidência ao vivo (não substitui auditoria externa)

---

## 1. Resumo executivo

| Camada | Estado | Evidência |
|--------|--------|-----------|
| APIs / chain L1 BAIT | **Viva** | `/api/v1/status` height ~44935, `chain_valid=true`, modules on |
| Orderbook / matching | **Parcial** | fills e offers registrados |
| Settlement BAIT on-chain (explorer) | **Não evidenciado** | `/explorer/txs/latest` = 100% `coinbase` |
| Settlement BTC / master pool | **Vazio** | `master_pool: {addresses:0, btc:0, utxos:0}` |
| Pool público/externo | **Não operacional** | offers em `on-chain-pending-broadcast` |
| Contratos Ethereum mainnet | **Código local/Anvil** | README: testes locais ≠ mainnet |
| Claims Hub (3000+ BTC / valuation) | **Não verificáveis via pool swap** | custódia “protegida”; whale citada ≠ master_pool |

**Conclusão:** o sistema de **registro** (API, feed, matching) está up; o sistema de **liquidação econômica** (transfer BAIT indexada + BTC out + pool com UTXOs) **não** está pronto para GO mainnet público.

---

## 2. Evidência de produção (2026-09-24)

### 2.1 Status

- Network: `b'AI'tcoin Mainnet`, version `0.8.0-live`
- `chain_height` ≈ 44935, `utxo_count` ≈ 44936, `mempool_size` 0
- Oracle: BTC/ETH/SOL/BAIT presentes
- Staking APY 7%, `total_staked` reportado 0 em rodadas anteriores

### 2.2 Swap book

- Orders/trades filled (ex.: ktd-orchestrator ↔ dola-ceo, 100 BAIT)
- Fills até 1_000_000 BAIT registrados
- Múltiplas offers `status: open` + `settlement: on-chain-pending-broadcast`
- **`master_pool.addresses = 0`, `btc = 0`, `utxos = 0`**
- Custody address citada: `12vG4zB6EG5FC6FhxnW688WkP1b7iK2M3X`

### 2.3 Explorer

- Últimas txs: exclusivamente `tx_type: coinbase` (50 BAIT, agent `chimera7_defi`)
- **Zero** `transfer` de swap/A2A visível no endpoint público latest

### 2.4 Hub marketing vs pool

Hub afirma fundo / whale BTC; isso **não** equivale a:

- master_pool operacional para payout de swap
- PoR ligado às offers pending
- txs transfer no explorer BAIT

---

## 3. Conflito README vs realidade

| Badge / claim no README | Realidade observada |
|-------------------------|---------------------|
| `Go Live E2E VALIDATED` | Settlement público incompleto |
| `Readiness 100%` | RPC/ETH/HW e liquidação externa pendentes (texto do próprio README) |
| `Slither 0 HIGH` (em docs históricos) | Relatório JSON antigo tinha High; re-run necessário |
| Testes locais 20/20 | Não provam broadcast mainnet nem custódia |

**Ação:** alinhar badges a **NO-GO econômico** até gates da secção 5.

---

## 4. Arquitetura do pool público/externo (alvo)

### 4.1 Definição

**Pool público/externo** = conjunto de UTXOs BTC + saldo BAIT de settlement **auditável** usados para completar as duas pernas do swap, com:

1. Endereços de depósito observados
2. Política de sweep → master (multisig/HSM)
3. Broadcast de saída BTC com txid público (mempool.space)
4. Tx BAIT tipo `transfer` indexada no explorer
5. PoR periódico (endereços + saldos + Merkle ou lista assinada)

### 4.2 Estados obrigatórios antes de “público”

```
PENDING → INTENT_VALIDATED → BTC_OBSERVED → BTC_CONFIRMED
  → BAIT_SUBMITTED → SETTLED (txid BAIT confirmed)
  → BTC_PAYOUT_BROADCAST (txid BTC em mempool.space)
  → master_pool.utxos > 0 (ou explicitamente deplecionado com prova)
```

Hoje a maioria para em **pending-broadcast** com pool zerado.

### 4.3 Controles de segurança (não negociáveis)

| Controle | Requisito |
|----------|-----------|
| Signing | HSM / multisig; nunca hot key em agente autônomo sem quorum |
| Allowlist | Destinos BTC allowlisted; limites diários |
| Fail-closed | ParityGate quorum ≥ 3; sem attestation → sem settle |
| Idempotência | `order_id` único; sem double-pay |
| Preflight | Scripts read-only (ex. PR #48) antes de qualquer `--execute` |
| Transparência | Endpoint público `master_pool` + PoR; sem “custódia protegida” como única prova do pool de swap |

---

## 5. Gates GO Mainnet (econômico)

### P0 — Bloqueadores

- [ ] **≥1** offer sai de `on-chain-pending-broadcast` → `settled` com:
  - [ ] txid BAIT `transfer` no explorer
  - [ ] txid BTC em mempool.space / blockstream
- [ ] `master_pool.utxos ≥ 1` **ou** PoR que explique liquidez externa usada no payout
- [ ] Explorer deixa de ser 100% coinbase nas últimas N txs (amostra com transfer)
- [ ] README badges sem “100% readiness / GoLive VALIDATED” até os itens acima
- [ ] Ownership contratos Ethereum → Timelock/Safe (se deploy mainnet ETH for parte do GO)

### P1 — Operação

- [ ] Merge/review PRs abertos: #48 (checklist safe), #47 (FundDeCaNaMy NO-GO consciente)
- [ ] Re-run Slither/Foundry na branch de contratos remediated
- [ ] Relatório 24/7 sem placeholders contraditórios às APIs
- [ ] Política pública de pool (endereços hot/warm/cold + limites)

### P2 — Escala

- [ ] Batch confirm gas-tuned (`maxBatch` dinâmico já no phase-2)
- [ ] Monitoramento: alerta se `pending-broadcast` > limiar ou pool = 0 com offers open
- [ ] Auditoria externa pré-anúncio de capital de giro

---

## 6. Plano de desenvolvimento (sem mover capital neste ambiente)

| Fase | Entrega | Quem |
|------|---------|------|
| A | Docs NO-GO + gates (este arquivo) | Engineering |
| B | Preflight settlement read-only (PR #48) | Ops + eng |
| C | Popular master_pool com capital **autorizado** + PoR | Custody / multisig humano |
| D | 1 settlement completo documentado | Ops + proof público |
| E | Abrir pool externo (limites, SLA, API status) | Product + eng |
| F | Ethereum mainnet wBAIT só após Timelock + audit | Contracts |

**Este ambiente não possui chaves de custódia, não assina PSBT, não faz broadcast BTC/BAIT e não deve ser usado para “forçar” settlement real.**

---

## 7. PRs relacionados

| PR | Foco |
|----|------|
| #48 | GO_LIVE checklist + force_settlement preflight **read-only** |
| #47 | FundDeCaNaMy roadmap + **NO-GO** explícito pós-audit |
| #34 (histórico) | BridgeLock/WBAIT remediation |
| #36 | Calldata / Uniswap gas docs |

---

## 8. Decisão formal

```
GO_MAINNET_ECONOMIC = NO
GO_PUBLIC_EXTERNAL_POOL = NO
GO_API_OBSERVABILITY = YES (parcial)
GO_LOCAL_CONTRACT_DEV = YES (Anvil / testes)
```

Próximo incremento de valor: **uma liquidação completa com duas txids públicas**, não mais documentação de matching sem settlement.
