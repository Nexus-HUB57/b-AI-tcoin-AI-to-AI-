# Protocolo de teste local — Bitcoin Core regtest + full node BAIT

## Objetivo

Validar o motor de swap BTC/BAIT com um Bitcoin Core real em `regtest` e uma instância local da blockchain BAIT com dois nós P2P TCP. O procedimento não usa Mainnet, Testnet pública, RPC externo ou fundos reais.

## Pré-requisitos

- Linux amd64;
- Python 3.11+;
- dependências Python do repositório instaladas;
- binário `bitcoind` e `bitcoin-cli` do Bitcoin Core.

O harness utilizado nesta execução foi o Bitcoin Core **31.1.0**, instalado fora do sistema em `/home/ubuntu/work/swap-btc-bait/bitcoin-core`.

## Execução

No repositório `b-AI-tcoin-AI-to-AI-`:

```bash
PYTHONPATH=. python3 scripts/run_local_swap_full_nodes.py \
  --bitcoind /home/ubuntu/work/swap-btc-bait/bitcoin-core/bin/bitcoind
```

O script cria um diretório temporário isolado e, nesta ordem:

1. inicia `bitcoind` em `regtest` com RPC local;
2. cria uma wallet de teste;
3. minera funding e envia exatamente `0.001 BTC` para um endereço de depósito;
4. minera um bloco para obter uma confirmação;
5. consulta o depósito usando `BitcoinCoreReader` e RPC `scantxoutset`;
6. cria dois `P2PNode` BAIT em portas efêmeras;
7. conecta o nó B ao nó A e valida o canal TCP;
8. cria funding BAIT local para o bridge;
9. valida uma attestation de paridade fixture, explicitamente limitada ao regtest;
10. submete o settlement BAIT no nó A;
11. retransmite a transação para o nó B;
12. minera e confirma a transação BAIT;
13. encerra o daemon e remove o diretório temporário, salvo se `--keep-data` for usado.

## Resultado desta execução

| Verificação | Resultado |
|---|---|
| Bitcoin Core | `/Satoshi:31.1.0/` |
| Rede Bitcoin | `regtest` |
| Depósito observado | `0.001 BTC`, 1 confirmação |
| Settlement BAIT | `settled` |
| Altura BAIT | 2 |
| Conexões P2P BAIT | 2 registros de transporte |
| Transações BAIT propagadas | 1 |
| Mainnet/fundos reais | não utilizados |

O resultado completo desta execução foi:

```json
{
  "bait_height": 2,
  "bait_state": "settled",
  "bitcoin_chain": "regtest",
  "bitcoin_core": "/Satoshi:31.1.0/",
  "observed_confirmations": 1,
  "p2p_connections": 2,
  "p2p_gossiped_transactions": 1
}
```

## Retenção de artefatos

Para inspecionar o datadir efêmero do Bitcoin Core após a execução:

```bash
PYTHONPATH=. python3 scripts/run_local_swap_full_nodes.py \
  --bitcoind /home/ubuntu/work/swap-btc-bait/bitcoin-core/bin/bitcoind \
  --keep-data
```

O caminho do diretório preservado é impresso no JSON. Ele pode ser removido manualmente depois da inspeção.

## Critérios de aprovação

O teste é aprovado somente se todos os critérios forem verdadeiros:

- `bitcoin_chain == "regtest"`;
- o txid observado pelo `BitcoinCoreReader` é igual ao txid enviado;
- o executor chega a `bait_submitted` antes da confirmação BAIT;
- o txid BAIT é recebido pelo segundo nó P2P;
- o executor chega a `settled` somente depois de um bloco BAIT conter a transação;
- o daemon Bitcoin Core é encerrado no bloco `finally` do harness.

Este protocolo valida integração local e não é uma autorização para habilitar settlement em Mainnet. A ativação de produção exige gestão de chaves, limites de valor, monitoramento, política de peers e procedimento de reconciliação.

O verificador `lambda _attestation: True` usado pelo harness é deliberadamente uma fixture de regtest. Em produção ele deve ser substituído por verificação de assinatura e quorum de oráculo aprovado; sem essa substituição o settlement deve permanecer desabilitado.
