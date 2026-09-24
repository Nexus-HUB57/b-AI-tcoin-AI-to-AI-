# Plano de Sweep → Custódia Oficial MyLink Fund

**Data:** 24/09/2026  
**Endereço oficial de destino (Fundo MyLink):**  
`bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s`

## 1. Estado on-chain do destino (blockstream.info, 24/09)

| Campo | Valor |
|---|---|
| funded_txo_count | 0 |
| funded_txo_sum | 0 |
| spent_txo_count | 0 |
| tx_count | 0 |
| **Saldo atual** | **0 BTC** |

O endereço está pronto para receber. Ainda não possui histórico.

## 2. Fontes de entrada candidatas ao sweep

### A) Dust residual do manifesto watch-only (0,01473073 BTC)
- 140 endereços com saldo < 0,001 BTC
- Soma exata: **0,01473073 BTC**
- Requer: inventário de UTXOs + chaves das 140 carteiras + política de fee
- **Destino obrigatório:** `bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s`
- BurnAddresses: **não usar** — política definida pelo operador: sweep **sempre** para a custódia oficial

### B) Consolidação futura de saldos operacionais
- Qualquer saída de payout de swap / settlement BTC
- Qualquer residual pós-operacional de agentes
- Qualquer consolidação de master_pool quando for populado

## 3. Política fixa (a partir de 24/09/2026)

```
SWEEP_DESTINATION = bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s
POLICY = "always_to_official_mylink_fund_custody"
BURN_ADDRESSES = disabled for operational sweeps
```

Qualquer script de sweep (fund_guardian, chimera7, motor de consolidação) deve:
1. Validar que o output principal aponta para `bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s`
2. Rejeitar (fail-closed) se o destino for outro endereço
3. Publicar txid no feed + atualizar master_pool + PoR

## 4. Passos operacionais (nó autorizado com chaves)

1. [ ] Inventariar UTXOs dos 140 dust addresses (Bitcoin Core / Esplora)
2. [ ] Calcular fee (ex.: 5–20 sat/vB) e valor líquido
3. [ ] Construir PSBT / tx com:
   - Inputs: todos os UTXOs dust selecionados
   - Output único: `bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s` = soma − fee
4. [ ] Assinar (multisig / HSM / agentes autorizados)
5. [ ] Broadcast
6. [ ] Aguardar ≥1 confirmação
7. [ ] Verificar saldo em `bc1qtydmz…` via blockstream/mempool
8. [ ] Atualizar `master_pool` e publicar PoR no feed + report.html

## 5. Relação com settlement de offers

- Offers pending usam hoje `12vG4z…` (vazio) ou `1Kj6epy…` (~2.408 BTC)
- A partir desta política, **payouts de settlement BTC** também devem direcionar residual/change para `bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s` quando aplicável
- O endereço `1Kj6epy…` permanece como custody operacional verificável (~2.408 BTC); a consolidação estratégica para o Fund MyLink fica a critério do operador

## 6. Evidência de execução (template para o feed)

```
SWEEP EXECUTADO
destino: bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s
txid: <txid>
amount_btc: <valor líquido>
fee_sats: <fee>
utxos: <N>
policy: always_to_official_mylink_fund_custody
ts: <unix>
```

---
*Nenhuma chave acessada. Nenhuma tx transmitida neste ambiente.*
