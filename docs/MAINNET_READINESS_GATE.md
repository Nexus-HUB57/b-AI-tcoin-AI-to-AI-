# Gate de prontidão Mainnet — Swap BTC/BAIT

**Data:** 2026-09-07  
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

## Correções efetivas realizadas

O indexador do explorer agora aceita scripts genesis não-PubKey sem quebrar, produz endereços determinísticos e parseáveis, resolve entradas por outpoint quando há histórico indexado, contabiliza múltiplas saídas pelo índice correto, separa saldo nativo de saldo de token e reconstrói a partir da blockchain vinculada. A mineração também possui retry limitado para reduzir falhas probabilísticas de PoW em harnesses locais, preservando o mempool quando uma tentativa falha.

## Bloqueadores restantes

1. **Wallet mobile e criptografia nativa:** Swift/Kotlin ainda contêm caminhos placeholder de bundle e precisam de implementação AEAD real, armazenamento seguro e testes de round-trip em dispositivo.
2. **Assinatura e importação de wallet:** é necessário provar que a chave importada, a chave pública e a assinatura pertencem à mesma carteira em todas as plataformas.
3. **Biometria e attestation:** challenge, anti-replay, vínculo de dispositivo e verificação server-side ainda precisam de prova criptográfica.
4. **SDK remoto:** transporte seguro obrigatório, envelopes de erro tipados, valores em inteiros/Decimal, operações remotas explícitas e ausência de falsos sucessos.
5. **Explorer público:** o reorg foi validado em harness local; ainda faltam deduplicação em produção, inicialização no daemon, API keys persistentes, rotação de segredo, rate limit atômico e contrato OpenAPI/runtime.
6. **Custódia real:** faltam política de multisig/HSM/MPC, segregação de funções, limites, reconciliação independente, circuito de refund/release, monitoramento, backups testados e plano de incidente.
7. **Operação Mainnet:** faltam revisão externa, threat model, auditoria de dependências, observabilidade, rollback de aplicação e aprovação explícita de mudança de rede.

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

**Decisão operacional:** permanecer em regtest/testnet controlada; não iniciar transição Mainnet irreversível neste estado.

## Referências

[1]: https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki
[2]: https://developer.bitcoin.org/examples/testing.html
[3]: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

## Anexo — estado do relatório de 39 falhas

O relatório detalhado versionado mantém a classificação integral dos 39 achados, evidências e correções propostas. O adendo inicial registra as correções do explorer e a validação BIP-340 já concluídas; a presença de resultados verdes em regtest não reduz automaticamente o gate de segurança para SDK mobile, custódia ou Mainnet.
