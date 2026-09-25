# Arquitetura — Pool público/externo Blockch'AI'n

## Objetivo

Liquidez BTC+BAIT **auditável** para completar swaps A2A sem depender de claims de custódia opaca.

## Componentes

1. **Deposit addresses** — por ordem ou por agente; observadas por `BitcoinCoreReader`
2. **Master pool** — UTXOs consolidados (warm) sob multisig/HSM
3. **BAIT bridge wallet** — Schnorr; `BaitBlockchainSettlement.submit`
4. **ParityGate** — quorum ≥ 3, fail-closed
5. **Public status API** — `master_pool.{addresses,btc,utxos}` + lista de txids recentes de payout
6. **PoR** — snapshot assinado periódico

## Regras

- Pool zerado + offers open = **circuit breaker** (não aceitar novos fills econômicos)
- Payout BTC só com allowlist + limite diário
- Settlement BAIT só com `enable_settlement=true` e attestation válida
- Scripts de produção: default dry-run; execute exige dual control

## Métricas de saúde

| Métrica | Saudável |
|---------|----------|
| pending-broadcast count | baixo / tendência ↓ |
| master_pool.utxos | > 0 se há open economic offers |
| explorer transfer ratio | > 0 nas últimas 100 txs |
| tempo INTENT→SETTLED | SLA definido |

## Fora de escopo deste doc

Chaves privadas, valores de funding, instruções de sweep de terceiros.
