# PoR Custódia BTC + Análise de Sweep — 24/09/2026

## 1. Validação on-chain real (blockstream.info)

| Endereço | Papel | funded_txo_sum | spent | Saldo estimado | tx_count | Status |
|---|---|---:|---:|---:|---:|---|
| `1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ` | Custody principal (citado em offers + binance-custody) | 240.809.510.118 sats | 100.000.000 sats (1 BTC) | **≈ 2.408,095 BTC** | 36 | 🟢 REAL e verificado |
| `12vG4zB6EG5FC6FhxnW688WkP1b7iK2M3X` | Custody citado em swap/book + pending offers | 0 | 0 | **0 BTC** | 0 | 🔴 Vazio |

Fonte: `https://blockstream.info/api/address/<addr>` em 24/09/2026.

**Conclusão PoR parcial:** o endereço `1Kj6epy…` possui saldo real e significativo (~2.408 BTC). O endereço `12vG4z…` (usado como custody nas offers pending) está vazio. `master_pool` na API continua `{addresses:0, btc:0, utxos:0}`.

## 2. Manifesto watch-only (`mylink_btc_mainnet_watch_only.json`)

- Instantâneo declarado: **2026-09-21T13:54:16 UTC**
- 221 endereços, total declarado **97.000,06100989 BTC**
- Coerência aritmética interna: OK (soma = total)
- **140 endereços com < 0,001 BTC** somam exatamente **0,01473073 BTC** (pó/residual)
- **0 endereços** entre 0,001 e 1.000 BTC (lacuna total)
- 81 endereços ≥ 1.000 BTC concentram praticamente todo o saldo
- Gini ≈ 0,689 | HHI ≈ 0,0165

### P1–P10 (maiores saldos declarados)

| Pos | Endereço | Saldo declarado |
|---|---|---:|
| P1 | `16Jka2DrvEGGJ6ks2kXRpxmQZLQmAFRoGk` | 5.000,00203131 BTC |
| P2 | `12ytiN9oWQTRGb6JjZiaoWMAvF9nPWdGX1` | 5.000,00120471 BTC |
| P3 | `15DtovKcGFiAJmyVfbjvCXHyjtyoZhyyj4` | 3.000,00167753 BTC |
| P4 | `13dSnmhFeX3qqbsi4thXXad4ggTh6VCESG` | 2.000,00541441 BTC |
| P5 | `16w8WZ8Ub1Whk6SP4cw4op5cgyRVsb77T8` | 2.000,00224447 BTC |
| P6 | `16y2tVCgnwGM6c3kPPuQDJrSadQqcddUm6` | 2.000,00220887 BTC |
| P7 | `18KHS8ndbKJ1iEtTxv44Ree3Fs7oCURg83` | 2.000,00219001 BTC |
| P8 | `13RwLs69Y7xPrTM5E2aa9RxiDSyeX6jEyw` | 2.000,00115790 BTC |
| P9 | `16maYEFESxYegRrDrm8AzmhYtGdHwHnvnx` | 1.999,99944917 BTC |
| P10 | `1nJ39zzTMJCygGxw3PZXKydSk7mNnC7SQ` | 1.000,00344068 BTC |

### P41–P50 (amostra intermediária)

Todos ~1.000,0001 BTC (agrupamento estreito).

> **Limite crítico do manifesto:** é watch-only, internamente coerente, mas estatisticamente atípico (lacuna 0,001–1.000 BTC + saldos repetidos). **Não prova spendability, titularidade comum nem estado atual da cadeia** além do instantâneo de 21/09. A revisão oficial recomenda verificação independente autorizada antes de qualquer agregação ou gasto.

## 3. Dust residual 0,01473073 BTC — candidatos a sweep

Os 140 endereços < 0,001 BTC somam exatamente o valor citado no pedido. Top dust:

| Endereço | Saldo | txs |
|---|---:|---:|
| `13nAJw8jw7BiYKLnad9YGdPxybK9mgPkM6` | 0,00092831 | 27 |
| `17nmFFPSANbPGgdtoEEuc6xbHoaP1n6ZBb` | 0,00082504 | 26 |
| `18E3AWaadnUPQ1aMpfEoyTXN49NYAZzbpD` | 0,00082504 | 26 |
| `13QxkdrhfeQ6aCF4TBWg8knQGBmiwL2rpV` | 0,00081957 | 25 |
| … (136 restantes) | … | … |
| **Total** | **0,01473073 BTC** | |

**Ação de sweep proposta (requer chaves):**

1. Inventariar UTXOs não gastos desses 140 endereços (via Bitcoin Core / electrum / esplora).
2. Construir transação consolidada:
   - Inputs: todos os UTXOs dust
   - Output 1: **0,01473073 BTC − fee** → endereço de Custódia oficial (`1Kj6epy…` ou endereço protegido)
   - Output 2 (opcional): burn address (ex.: `1BitcoinEaterAddressDontSendf59kuE` ou OP_RETURN) se política de burn pós-sweep existir
3. Assinar com as chaves correspondentes (multisig / HSM / agentes autorizados).
4. Broadcast e aguardar confirmações.
5. Atualizar `master_pool` e publicar PoR atualizado.

**Bloqueio atual:** este ambiente **não possui chaves privadas**. O motor de sweep (se existir em `scripts/` ou agentes) deve ser invocado pelo nó autorizado (chimera7 / fund_guardian / bridge operator).

## 4. master_pool e offers pending

- `master_pool` (API): `{ "addresses": 0, "btc": 0, "utxos": 0 }`
- 12 offers com `settlement: on-chain-pending-broadcast`
- Custody referenciada nas pending: majoritariamente `12vG4z…` (vazio on-chain)

Isso explica por que o broadcast BTC de saída não ocorre: o pool de liquidez operacional para payout está zerado no lado da API, e o endereço de custody usado nas offers abertas não tem saldo.

## 5. Recomendações imediatas

1. **Publicar PoR assinado** do endereço `1Kj6epy…` (saldo real ~2.408 BTC) no feed + report.html.
2. **Decidir custody oficial** para offers futuras: migrar de `12vG4z…` (vazio) para `1Kj6epy…` ou endereço multisig protegido.
3. **Invocar motor de sweep** (agentes fund_guardian / chimera7) sobre os 140 dust addresses **somente após** prova de controle das chaves e política de burn/custody aprovada.
4. **Forçar 1 settlement** de offer pending (ver `scripts/force_settlement_e2e.py`) e indexar a tx `transfer` no explorer.
5. Atualizar `master_pool` após qualquer consolidação real.

## 6. Evidências

- blockstream.info API (24/09/2026)
- `wallet_reports/agent_distribution_review.md`
- `wallet_reports/mylink_btc_mainnet_watch_only.json` (snapshot 21/09)
- `deploy/binance-custody-addresses.json`
- `/api/v1/swap/book` live

---
*Documento gerado em 24/09/2026 — validação descritiva + on-chain pública. Nenhuma chave acessada, nenhuma tx transmitida.*


## 7. Custódia oficial Fundo MyLink (política 24/09)

**Endereço oficial de sweep/consolidação:**  
`bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s`

- Saldo atual (blockstream 24/09): **0 BTC** (pronto para receber)
- Política: **todo sweep operacional** deve apontar para este endereço
- BurnAddresses: desabilitados para sweeps operacionais
- Ver `SWEEP_PLAN_OFFICIAL_CUSTODY.md`
