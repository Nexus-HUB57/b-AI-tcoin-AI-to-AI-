# Gate de prontidão Mainnet — Swap BTC/BAIT

**Data:** 2026-09-07 21:33 (-03:00)
**Estado:** BLOQUEADO — somente regtest/testnet controlada
**Escopo:** executor BTC/BAIT, full nodes nativos, SDK, explorer e custódia

## Conclusão

A validação local do motor Swap BTC/BAIT foi concluída com sucesso em `regtest`, mas isso não equivale a uma validação Mainnet. A transição para produção real e irreversível **não foi executada**. O gate permanece vermelho porque ainda existem achados críticos e altos no SDK mobile, gestão de chaves, attestation, autorização, OpenAPI, API keys e operação de custódia.

## Evidências aprovadas em ambiente controlado

| Verificação | Resultado |
|---|---|
| Matriz de fases, rede, contratos, mobile, swap, Schnorr e UTXO | 244 aprovados; 1 warning de coleta de classe sem impacto no resultado |
| E2E adicional de validação, persistência e ecossistema | 146 aprovados |
| Explorer | 55 aprovados; reorg local validado com rebuild canônico |
| Bitcoin Core local | `31.1.0`, cadeia `regtest` |
| Swap full node/P2P | settlement concluído; 1 confirmação observada; 2 conexões P2P; 1 transação propagada |
| Custódia simulada | `100000000` satoshis; saldo reconciliado; `real_btc_used: false` |
| BIP-340 | 19/19 vetores oficiais aprovados |

## Simulação de swap — execução atual

O harness completo foi executado novamente em Bitcoin Core `31.1.0` `regtest`. O depósito BTC foi observado pelo RPC/`BitcoinCoreReader` com uma confirmação, o settlement BAIT chegou a `settled`, a transação BAIT foi propagada por dois nós P2P e o diretório efêmero foi encerrado ao final.

| Evidência | Resultado |
|---|---|
| Rede Bitcoin | `regtest` |
| Depósito observado | `5bf42106854c0f83ec5b81fe2ed2c5d1bbfc62ea1a8f5f199d39aa97af7a6b92` |
| Settlement BAIT | `c9c9dc6e9a00abdbbd2b01dc2bf397e6ab376973e3d7c2612f4b28074d6ce749` / `settled` |
| Confirmações BTC | 1 |
| Conexões P2P | 2 |
| Transações BAIT propagadas | 1 |
| Cenário de custódia | `100000000` satoshis, `settled`, `real_btc_used: false` |

Este é um **fluxo atômico simulado de observação BTC → settlement BAIT**, não uma atomic swap Mainnet completa: o harness não executa release, refund, PSBT, multisig ou gasto do UTXO BTC. Portanto, a execução confirma a integração local, mas não remove o bloqueador de custódia real.

## Correções efetivas realizadas

O indexador do explorer agora aceita scripts genesis não-PubKey sem quebrar, produz endereços determinísticos e parseáveis, resolve entradas por outpoint quando há histórico indexado, contabiliza múltiplas saídas pelo índice correto, separa saldo nativo de saldo de token e reconstrói a partir da blockchain vinculada. A mineração também possui retry limitado para reduzir falhas probabilísticas de PoW em harnesses locais, preservando o mempool quando uma tentativa falha.

## Bloqueadores restantes

| ID | Status atual | Evidência |
|---|---|---|
| 1. Wallet mobile/crypto nativa | **ABERTO — crítico** | Swift/Kotlin ainda contêm caminhos placeholder; falta AEAD real, keystore e round-trip em dispositivo |
| 2. Assinatura/importação de wallet | **ABERTO — crítico** | Falta provar correspondência chave privada → chave pública → assinatura em todas as plataformas |
| 3. Biometria/attestation | **ABERTO — crítico/alto** | Falta challenge anti-replay, vínculo de dispositivo e verificação server-side |
| 4. SDK remoto | **ABERTO — alto** | Faltam transporte seguro obrigatório, erros tipados, valores Decimal/integer e remoção de falsos sucessos |
| 5. Explorer público | **PARCIAL — alto** | Reorg local passou; faltam deduplicação de produção, daemon init, API keys persistentes, rotação, rate limit atômico e OpenAPI/runtime |
| 6. Custódia real | **ABERTO — crítico** | Regtest passou; faltam multisig/HSM/MPC, segregação, limites, refund/release, monitoramento e incidentes |
| 7. Operação Mainnet | **ABERTO — crítico** | Faltam revisão externa, threat model, auditoria de dependências, observabilidade, rollback e aprovação de mudança |

## Critério de promoção futura

A promoção somente pode ser considerada após todos os bloqueadores críticos estarem fechados, os achados altos terem plano aprovado, a matriz de testnet passar sem warnings relevantes, o explorer demonstrar reconstrução após reorg, a custódia passar por ensaio com chaves descartáveis, e uma revisão humana independente aprovar o payload operacional. A promoção deve começar por um ambiente canário reversível; não se deve enviar fundos reais durante este ciclo.

## Comandos reproduzíveis

```bash
PYTHONPATH=. python3 -m pytest -q tests/test_blockchain_explorer.py
PYTHONPATH=. python3 -m pytest -q tests/test_phase_a_foundation.py tests/test_phase_b_network.py tests/test_phase_c_contracts.py tests/test_phase_d_mobile_native.py tests/test_phase_e_production.py tests/test_native_processing.py tests/test_native_swap_executor.py tests/test_p2p_swap_tcp_e2e.py tests/test_schnorr_bip340.py tests/test_utxo_hex_swap_audit.py
PYTHONPATH=. python3 scripts/run_local_swap_full_nodes.py --bitcoind /home/ubuntu/work/swap-btc-bait/bitcoin-core/bin/bitcoind
PYTHONPATH=. python3 scripts/run_local_swap_custody_1btc.py --bitcoind /home/ubuntu/work/swap-btc-bait/bitcoin-core/bin/bitcoind
```

Todos os comandos acima são locais e controlados. Nenhum comando deste relatório usa BTC real, transmite para Mainnet ou altera segurança, propriedade, billing ou acesso de conta.

## Relatórios relacionados

- [`SDK_EXPLORER_39_FAILURES_REPORT.md`](SDK_EXPLORER_39_FAILURES_REPORT.md)
- [`BIP340_VALIDATION_PROTOCOL.md`](../native_processing/BIP340_VALIDATION_PROTOCOL.md)
- [`CUSTODY_1BTC_REGTEST_PROTOCOL.md`](../native_processing/CUSTODY_1BTC_REGTEST_PROTOCOL.md)
- [`LOCAL_FULL_NODE_TEST_PROTOCOL.md`](../native_processing/LOCAL_FULL_NODE_TEST_PROTOCOL.md)
- [`REORG_BIP340_E2E_VALIDATION.md`](../native_processing/REORG_BIP340_E2E_VALIDATION.md)
- [`SWAP_BTC_BAIT_NATIVE.md`](../native_processing/SWAP_BTC_BAIT_NATIVE.md)

**Decisão operacional:** permanecer em regtest/testnet controlada; a simulação passou, mas os bloqueadores críticos permanecem. Não iniciar transição Mainnet irreversível neste estado.

## Referências

[1]: https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki
[2]: https://developer.bitcoin.org/examples/testing.html
[3]: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

## Anexo — estado do relatório de 39 falhas

O relatório detalhado versionado mantém a classificação integral dos 39 achados, evidências e correções propostas. O adendo inicial registra as correções do explorer e a validação BIP-340 já concluídas; a presença de resultados verdes em regtest não reduz automaticamente o gate de segurança para SDK mobile, custódia ou Mainnet.
