# BAITHex — PSBT e threshold signer 2-de-3

## PSBT

O fluxo segue os papéis públicos do BIP-174/Bitcoin Core:

| Papel | BAITHex | Responsabilidade |
|---|---|---|
| Creator | `baith-exchange` | Criar a transação unsigned e o envelope PSBT |
| Updater | UTXO/indexer adapter | Inserir prevouts, scripts e metadados verificáveis |
| Signer | threshold cluster | Produzir shares somente após a política local e quorum |
| Finalizer | verifier service | Montar scriptSig/witness e rejeitar incompletos |
| Extractor | broadcast gate | Extrair raw transaction após revalidação independente |

`decodepsbt`/parsing é diagnóstico, não prova de consenso. O BAITHex deve confirmar prevout, índice, scriptPubKey, valor, fee, fee rate, change, rede e destino através de fontes autenticadas. O raw signed deve ser decodificado novamente antes de qualquer transmissão.

## Threshold 2-de-3

A referência criptográfica pública é FROST/RFC 9591. O cluster deve ter três participantes identificados e exigir duas shares válidas. Cada sessão deve fixar:

- ciphersuite e domínio de aplicação;
- hash do payload autorizado;
- request ID e idempotency key;
- conjunto ordenado de participantes;
- nonce/commitment de uso único;
- autenticação entre identidade e signer ID;
- timeout e quarantine de share inválida;
- verificação individual e final da assinatura.

A configuração 2-de-3 não é uma aprovação de três pessoas: duas shares bastam. Duas shares comprometidas podem autorizar gastos. O coordenador não deve ter shares privadas, mas pode causar DoS; o serviço precisa de timeout, retry seguro e circuit breaker.

## Estado operacional desta entrega

O manifesto de cluster é somente configuração declarativa, com `allow_signing=false` e `allow_broadcast=false`. Nenhuma chave foi gerada, nenhum nonce foi criado e nenhum regtest/testnet foi iniciado. A política vigente exige Mainnet-only; a ativação real requer HSM/MPC externo, DKG auditado, secret manager e aprovação independente.

## Fontes públicas clean-room

- [BIP-174](https://github.com/bitcoin/bips/blob/master/bip-0174.mediawiki)
- [Bitcoin Core PSBT documentation](https://github.com/bitcoin/bitcoin/blob/master/doc/psbt.md)
- [Bitcoin Core repository](https://github.com/bitcoin/bitcoin)
- [rust-bitcoin](https://github.com/rust-bitcoin/rust-bitcoin)
- [rust-miniscript](https://github.com/rust-bitcoin/rust-miniscript)
- [RFC 9591 — FROST](https://www.rfc-editor.org/rfc/rfc9591.html)
- [Zcash Foundation FROST](https://github.com/ZcashFoundation/frost)
- [Bytemare FROST](https://github.com/bytemare/frost)

Essas fontes são referências públicas de protocolo e interfaces. O BAITHex não copia implementação proprietária.
