# Protocolo formal de validação BIP-340

## Escopo

Este protocolo valida a implementação `baitcoin_core/cryptography/schnorr.py` contra o conjunto oficial de vetores mantido pelo projeto Bitcoin BIPs. A validação não usa Bitcoin Mainnet, não assina transações reais e não movimenta BTC.

## Fonte normativa

- [BIP-340 — Schnorr signatures for secp256k1](https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki)
- [CSV oficial de vetores](https://raw.githubusercontent.com/bitcoin/bips/master/bip-0340/test-vectors.csv)
- [Implementação de referência](https://github.com/bitcoin/bips/blob/master/bip-0340/reference.py)

O CSV foi versionado em `tests/data/bip340_test_vectors.csv` para que a suíte possa ser executada offline depois da revisão da origem.

## Critérios

A implementação precisa reproduzir os `tagged_hash` oficiais para `BIP0340/aux`, `BIP0340/nonce` e `BIP0340/challenge`; validar chaves privadas em `1..n-1`; derivar a chave pública X-only com Y par; validar `r`, `s`, `lift_x`, ponto no infinito e paridade de R; e reproduzir assinaturas determinísticas quando `aux_rand` é fornecido.

## Resultado

| Critério | Resultado |
|---|---:|
| Vetores oficiais | 19/19 |
| Verificações corretas | 19/19 |
| Vetores positivos aceitos | 9/9 |
| Vetores negativos rejeitados | 10/10 |
| Chaves públicas oficiais | 8/8 |
| Assinaturas determinísticas | 8/8 |

Execução reproduzível:

```bash
PYTHONPATH=. python3 -m pytest -q tests/test_schnorr_bip340.py
```

## Gate de release

A aprovação acima cobre a semântica dos vetores e não constitui auditoria de side channels, custódia, HSM, Taproot completo, multisig, produção ou compatibilidade de consenso de qualquer rede. Antes de usar a implementação em custódia ou broadcast, é necessária revisão independente da biblioteca criptográfica e do modelo de ameaças.
