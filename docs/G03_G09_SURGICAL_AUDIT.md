# G-03 → G-09 Surgical E2E Audit

**Network:** b'AI'tcoin Mainnet · height **~47853** · chain_valid=true  
**GO-LIVE financeiro:** **BLOCKED**

## Gate matrix

| Gate | Nome | Status | Motivo |
|------|------|--------|--------|
| G-03 | Transação A2A não-coinbase | **BLOCKED** | Últimas 20 txs 100% coinbase; nenhum transfer indexado |
| G-04 | Matching book/order/fill | **PARTIAL** | 22 offers, 10 fills, 2 orders, 1 trade — sem vínculo on-chain |
| G-05 | Depósito BTC | **BLOCKED** | Sem txid:vout público; pool.utxos=0; explorers BTC 429 neste run |
| G-06 | Settlement BAIT | **BLOCKED** | Nenhuma tx transfer; enable_settlement não público |
| G-07 | Payout BTC | **BLOCKED** | Sem HSM/PSBT; master_pool.btc=0 |
| G-08 | Master pool | **BLOCKED** | addresses=0 btc=0 utxos=0 |
| G-09 | ParityGate | **CODE_READY_PROD_PENDING** | Código + Chainlink em main (~15 bps); falta attestation prod quorum≥3 |

## Hard stops

- Não executar `enable_settlement`, broadcast ou sweep sem HSM/PSBT e 2 revisores
- Fills no book ≠ liquidação on-chain
- Explorer só coinbase ⇒ G-03/G-06 falham
- master_pool zerado ⇒ G-07/G-08 falham

## Next operator actions

1. Nó autorizado: gerar 1 transfer BAIT mínima ligada a `fill_id` → G-03
2. Publicar `txid:vout` depósito BTC + 3 confs → G-05
3. `process()` com ParityGate quorum3 → BAIT_SUBMITTED→SETTLED → G-06
4. PSBT payout + master_pool update → G-07/G-08
5. Expor `GET /api/v1/parity/latest` com proof_b64 → G-09 produção

## Re-run

```bash
python3 scripts/g03_g09_surgical_audit.py
python3 scripts/g03_g09_surgical_audit.py --json
```
