# Protocolo E2E — custódia de 1 BTC em regtest

## Limite operacional

Este protocolo usa exclusivamente um Bitcoin Core local em `regtest`. O valor de `1.00000000 BTC` é criado por mineração/funding local e não representa BTC real. O procedimento falha fechado se a rede retornada pelo daemon não for `regtest`.

## Execução

```bash
PYTHONPATH=. python3 scripts/run_local_swap_custody_1btc.py \
  --bitcoind /home/ubuntu/work/swap-btc-bait/bitcoin-core/bin/bitcoind
```

O harness cria wallets efêmeras `miner` e `custody`, minera maturidade, envia exatamente `100000000` satoshis para um endereço de custódia exclusivo, confirma o depósito, valida o outpoint através do `BitcoinCoreReader`, registra o evento em SQLite WAL, executa o settlement BAIT em dois nós P2P locais e verifica que a UTXO de custódia continua não gasta.

## Resultado validado

| Invariante | Resultado |
|---|---:|
| Rede | `regtest` |
| Depósito | `100000000 satoshis` |
| Saldo append-only de custódia | `100000000 satoshis` |
| Settlement BAIT | `settled` |
| Gossip BAIT | 1 transação propagada |
| BTC real | não utilizado |

## O que este protocolo não implementa

O harness não é uma carteira de produção e não implementa release, refund, PSBT, HSM, multisig, limites diários, monitoramento, reorg recovery ou broadcast Mainnet. O saldo de custódia é uma contabilidade de teste reconciliada contra o Bitcoin Core local; não é prova de reserva em rede pública.

Qualquer ativação de custódia real exige um adaptador separado, ledger append-only, reconciliação de reorg, política de release/refund, signer segregado, quorum operacional e aprovação explícita do operador.
