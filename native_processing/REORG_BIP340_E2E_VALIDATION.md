# Validação E2E — reorg e BIP-340

**Data:** 2026-09-07  
**Ambiente:** sandbox local, cadeia BAIT em memória e Bitcoin Core separado em `regtest`  
**BTC real/Mainnet:** não utilizado

## Reorg

O protocolo foi executado com uma cadeia canônica contendo dois blocos após o genesis e uma cadeia candidata contendo três blocos após o mesmo ancestor. O `BlockSync.resolve_longer_chain` validou altura, parent hash, Merkle root, coinbase e timestamp antes da troca atômica.

| Critério | Resultado |
|---|---|
| Cadeia candidata contínua | aprovado |
| Parent hash do ancestor | aprovado |
| Cadeia candidata mais longa | aprovado |
| Troca da cadeia canônica | aprovado |
| Rebuild do UTXO | aprovado |
| Rebuild do explorer | aprovado |
| Tip antigo removido do explorer | aprovado |
| Fork de bloco único rejeitado | aprovado |

A suíte `tests/test_reorg_protocol.py`, junto com `tests/test_phase_b_network.py` e `tests/test_blockchain_explorer.py`, passou com **119 testes**. O único aviso foi a coleta de uma classe de gerenciamento de testnet com `__init__`, sem falha de execução.

A implementação deliberadamente não aceita um bloco concorrente isolado como reorg: um peer precisa fornecer o sufixo contíguo da cadeia candidata. Isso evita trocar a cadeia com base em uma única evidência de altura.

## BIP-340

Os vetores foram executados por dois caminhos independentes:

1. Teste versionado: `PYTHONPATH=. python3 -m pytest -q tests/test_schnorr_bip340.py` — **1 passed**; o teste percorre os 19 registros.
2. Verificador independente: `PYTHONPATH=. python3 /home/ubuntu/work/swap-btc-bait/bip340/check_vectors.py` — `vectors=19`, `verify_correct=19`, `positive=9`, `negative=10`, `key_correct=8`, `sign_correct=8`.

| Critério | Resultado |
|---|---:|
| Vetores oficiais | 19/19 |
| Verificações corretas | 19/19 |
| Positivos aceitos | 9/9 |
| Negativos rejeitados | 10/10 |
| Chaves públicas | 8/8 |
| Assinaturas determinísticas | 8/8 |
| Compilação da implementação e teste | aprovada |

## Limites

Esta execução valida a semântica local do BIP-340 e a troca de cadeia no modelo de teste. Não constitui auditoria de side channels, revisão de consenso distribuído, segurança de HSM/MPC, Taproot completo, custódia, broadcast ou autorização para Mainnet.

O gate operacional permanece em `regtest/testnet` até que os bloqueadores de SDK mobile, gestão de chaves, attestation, API keys, custódia e operação de produção sejam encerrados.
