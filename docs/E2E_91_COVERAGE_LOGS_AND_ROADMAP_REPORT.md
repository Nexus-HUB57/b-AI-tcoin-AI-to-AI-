# Relatório E2E: 91 Testes, Cobertura, Logs e Próximas Fases

**Data da análise:** 15 de setembro de 2026
**Branch analisada:** `fix/phase-remediation-local-validation` após o merge do PR #26 em `main`
**Escopo:** validação local, sem deploy, broadcast, RPC Mainnet, assinatura de transação ou movimentação financeira.

## 1. Sumário executivo

A suíte nominalmente reportada como **91 testes E2E aprovados** foi reproduzida por `pytest --collect-only` com exatamente 91 casos nos 13 arquivos de teste selecionados. A execução funcional anterior da mesma composição terminou com **91 passed**, com um `PytestCollectionWarning` não bloqueante em `TestnetManager` por possuir construtor próprio.

A cobertura foi medida separadamente com `coverage.py`, usando os mesmos 91 testes e limitando a instrumentação a `baitcoin_core`, `native_processing`, `baitcoin_bridge` e `scripts`. O resultado foi **37% de cobertura de linhas executáveis: 3.605 de 9.804 statements cobertos**. Esse valor representa a cobertura dessa suíte focada, não uma afirmação de cobertura total do sistema. Não havia relatório de cobertura versionado anteriormente no repositório.

O teste de estresse do mempool foi executado isoladamente e passou em **709,64 segundos**. Ele insere 10.000 transações sintéticas pelo `FeeMarket`, minera um bloco e confirma que as transações sem inputs/UTXOs válidos permanecem no mempool, evitando descarte silencioso. O cenário de swap TCP foi validado em dois níveis: um smoke com dois nós e handoff completo `intent → confirmação BTC sintética → lock → proof → mint`, e estresses concorrentes com 5 nós/30 intents e 6 nós/48 intents, incluindo reenvio e deduplicação.

## 2. Composição dos 91 testes

| Arquivo | Responsabilidade | Casos coletados |
|---|---|---:|
| `tests/test_swap_stress_smoke_e2e.py` | Smoke TCP completo, executor, bridge e malha P2P com deduplicação | 2 |
| `tests/test_p2p_swap_tcp_e2e.py` | Sincronização de intents por TCP real e regressões de framing/agent ID | 3 |
| `tests/test_p2p_swap_e2e.py` | Fluxo real TCP entre dois nós | 1 |
| `tests/test_p2p_swap_load.py` | Carga concorrente em malha completa, 5 nós e 30 intents | 1 |
| `tests/test_canonical_address_swap_e2e.py` | Endereços canônicos e fluxo de swap | 1 |
| `tests/test_swap_bridge_handoff.py` | Handoff lock/proof/mint e idempotência | 1 |
| `tests/test_native_swap_executor.py` | Estados e invariantes do executor nativo | 8 |
| `tests/test_lnd_mainnet_adapter_local.py` | Settlement simulado, idempotência, pausa e estados inválidos | 3 |
| `tests/test_lnd_channel_authorization_local.py` | Autorização de relayer e rotação/reconexão LND | 4 |
| `tests/test_lnd_monitor_rotation_local.py` | Monitoramento e rotação local | 3 |
| `tests/test_approval_and_macaroon_local.py` | Gate de aprovação e macaroons | 2 |
| `tests/test_bridge_authorization_handoff_local.py` | Assinaturas e autorização do bridge handoff | 4 |
| `tests/test_phase_b_network.py` | Gossip, block sync, nó independente e testnet local | 58 |
| **Total** |  | **91** |

A composição foi confirmada diretamente pelo coletor do pytest, não inferida a partir de nomes de arquivos. O único aviso de coleta foi `PytestCollectionWarning` para `TestnetManager`, que não impede os 91 casos funcionais.

## 3. Cobertura de código atual

A medição foi executada com:

```text
python3 -m coverage run --source=baitcoin_core,native_processing,baitcoin_bridge,scripts -m pytest -q <mesmos 13 arquivos>
python3 -m coverage report -m
```

### 3.1 Resultado agregado

| Escopo instrumentado | Statements | Cobertos | Não cobertos | Cobertura |
|---|---:|---:|---:|---:|
| `baitcoin_core`, `native_processing`, `baitcoin_bridge`, `scripts` | 9.804 | 3.605 | 6.199 | **37%** |

### 3.2 Módulos relevantes

| Módulo | Cobertura | Interpretação |
|---|---:|---|
| `native_processing/bridge_handoff.py` | 92% | Handoff principal bem exercitado, embora ainda existam ramos de erro não cobertos. |
| `native_processing/swap_sync.py` | 87% | Deduplicação e convergência estão fortemente cobertas. |
| `native_processing/swap_protocol.py` | 79% | Assinatura e protocolo possuem cobertura razoável, com casos negativos restantes. |
| `native_processing/swap_executor.py` | 73% | Fluxos principais cobertos; ramos de falha e recuperação ainda devem crescer. |
| `native_processing/swap_service.py` | 55% | O smoke cobre a integração central, mas não todos os caminhos operacionais do serviço. |
| `baitcoin_core/network/p2p_real/node.py` | 65% | TCP e gossip principais cobertos; desconexões, timeouts e recuperação precisam de mais cenários. |
| `baitcoin_core/network/p2p_real/protocol.py` | 73% | Framing e mensagens principais exercitados; vários tipos de mensagem permanecem parciais. |
| `baitcoin_core/network/gossip.py` | 88% | Gossip local possui boa cobertura. |
| `baitcoin_core/blockchain/chain.py` | 51% | Reconstrução persistente, validações e caminhos de erro ainda têm lacunas. |
| `baitcoin_core/blockchain/mempool.py` | 28% | A suíte atual usa principalmente `FeeMarket`; a classe `Mempool` legada precisa de suíte própria ou descontinuação explícita. |
| `baitcoin_core/consensus/difficulty.py` | 33% | Ajustes de dificuldade e limites de época estão pouco exercitados. |
| `baitcoin_core/consensus/pouw.py` | 24% | PoUW/PoAS possui grande área sem cobertura comportamental. |
| `baitcoin_core/consensus/zkml_real/verifier.py` | 32% | Verificação real e caminhos inválidos ainda não estão cobertos de forma suficiente. |
| `baitcoin_core/network/peer_discovery/dht.py` | 0% | Sem cobertura nesta suíte. |
| `baitcoin_core/network/p2p_bridge.py` | 0% | Sem cobertura nesta suíte. |
| `baitcoin_core/contracts/contract_engine.py` | 0% | Sem cobertura nesta suíte; não confundir com os testes Solidity Foundry. |
| `baitcoin_bridge/anchor.py` | 25% | Ancoragem e caminhos de persistência/erro precisam de testes direcionados. |
| `baitcoin_bridge/pool.py` | 25% | Pool e limites operacionais pouco exercitados. |
| `scripts/validate_e2e_comprehensive.py` | 0% | O script de validação não foi contado como código coberto pela própria suíte. |

### 3.3 Limitações da medição

A medição não inclui JavaScript/TypeScript, contratos Solidity como linhas Python, scripts de deploy externos ou comportamento de uma rede pública. Também não representa cobertura de produção. O repositório não possuía `.coveragerc`, `coverage.xml`, `htmlcov` ou um relatório equivalente versionado antes desta análise.

## 4. Análise do estresse do mempool

O teste `TestMempoolStress.test_mempool_10000_transactions` foi executado isoladamente e passou em **709,64 s**. A execução realizou 10.000 inserções pelo caminho de produção `Blockchain.add_transaction`, usando o `FeeMarket`.

O resultado importante não é apenas a capacidade de armazenar 10.000 entradas. As transações do cenário não possuem inputs/UTXOs válidos; portanto, o `TransactionVerifier` rejeita sua inclusão no bloco. O estado final esperado é que as 10.000 transações permaneçam no `FeeMarket`. Isso confirma uma propriedade de segurança: transações inválidas não são removidas silenciosamente como se tivessem sido liquidadas.

O teste originalmente usava `blockchain.mempool.append(tx)` e esperava que a mineração removesse 1.000 entradas. Essa expectativa estava desalinhada com a implementação atual, que usa `FeeMarket` e seleção por peso, não uma lista fixa de 1.000 transações. O teste foi corrigido para refletir o contrato vigente.

Não foi produzido um log de métricas por transação, throughput ou uso de memória. O artefato disponível é o output do pytest, suficiente para confirmar duração e resultado, mas insuficiente para um benchmark de capacidade de produção.

## 5. Análise do swap TCP e estresse P2P

### 5.1 Smoke E2E de dois nós

O smoke `test_swap_smoke_e2e_signed_tcp_executor_bridge` percorre o caminho local completo: cria e assina uma intenção, propaga-a por TCP, admite-a no nó remoto, avança o executor até `btc_confirmed`, inicia o lock do bridge, submete provas e alcança `minted`. O teste também repete a submissão do handoff e confirma idempotência pelo mesmo `event_id`.

### 5.2 Malha de seis nós

O teste `test_swap_stress_e2e_mesh_deduplicates_broadcasts` cria 6 nós TCP, 6 stores SQLite e 6 engines. Cada nó origina 8 intents, totalizando **48 intents**. A primeira transmissão deve convergir para todos os nós; a retransmissão completa deve continuar sendo aceita pelos peers, sem aumentar o número de registros persistidos. O teste verifica 48 IDs em cada store, estado `pending`, fan-out mínimo de 5 e tempo total abaixo de 20 segundos no contrato do teste.

### 5.3 Carga concorrente de cinco nós

O teste `test_p2p_swap_concurrent_multi_node_load` usa uma malha completa de 5 nós e 6 intents por nó, totalizando **30 intents**. Cada broadcast deve alcançar pelo menos os outros 4 nós. A segunda transmissão dos mesmos intents verifica idempotência e a contagem persistida permanece em 30 por store.

### 5.4 Logs disponíveis e lacunas

Não há arquivos de log TCP ou swap versionados no repositório. Os outputs de terminal preservados no sandbox confirmam os resultados dos pytest, mas não registram, em formato estruturado, latência por mensagem, perda, retransmissões, tamanho de filas, CPU, memória, sockets abertos ou distribuição de tempo por fase. Para uma validação operacional futura, deve ser criado um harness que grave JSONL/JSON com essas métricas e um identificador de execução.

## 6. Próximas fases e pendências documentadas

| Prioridade | Fase ou pendência | Estado observado | Próxima ação recomendada |
|---|---|---|---|
| P0 | Reexecutar CI Python 3.12/3.11 e Slither após o merge do PR #26 | Checks antigos tinham falha/cancelamento; Foundry passou | Confirmar checks novos e corrigir falhas reais, sem tratar bootstrap do runner como finding de contrato. |
| P0 | Auditoria independente dos dois achados HIGH remediados | Código local corrigido; relatório histórico ainda registra auditoria independente pendente | Rodar auditoria reproduzível em commit do `main` e versionar o resultado. |
| P1 | Cobertura de bridge, pool, watcher e anchor | Entre 25% e 39% nos módulos críticos | Criar testes de falha, reorg, timeout, assinatura inválida, rollback e recuperação. |
| P1 | Cobertura de consenso e cadeia | `chain.py` 51%, dificuldade 33%, PoUW 24%, verifier zkML 32% | Testar reorg, fork, DAA, limites de PoUW/PoAS, provas inválidas e reconstrução persistente. |
| P1 | Cobertura de mempool | `mempool.py` 28%; `FeeMarket` é o caminho atual | Decidir se `Mempool` será removido/isolado ou cobri-lo completamente, incluindo expiração, eviction, dedupe e taxas. |
| P1 | Observabilidade do estresse TCP | Sem métricas estruturadas de latência e recursos | Adicionar relatório JSON de cada execução com fan-out, latência, duplicatas, timeouts, CPU e memória. |
| P1 | DHT e P2P bridge | 0% nesta medição | Definir contrato operacional e adicionar testes de integração antes de declarar prontidão. |
| P2 | Testnet pública e RPC externo | Não executados nesta validação segura | Preparar somente quando houver RPC, credenciais e procedimento aprovados; manter dry-run separado. |
| P2 | Broadcast de custódia BTC | Explicitamente adiado na documentação da Fase 2 | Exigir WIF por canal seguro, assinatura air-gap canário, push autorizado, txid, confirmação e atualização auditável. |
| P2 | Ponte Motor Swap ↔ Exchange A2A | Listada como pendência futura | Implementar settlement BTC/BAIT com autorização, idempotência, reconciliação e testes de falha. |
| P2 | Preload/healthcheck do `mylink-routes` | Documentado como necessário para eliminar 502 cold-start | Adicionar readiness probe, warm-up e teste de reinício. |
| P2 | Runtime de `mybait.org` | Sincronização não declarada; falta mecanismo autorizado de deploy | Definir workflow/credencial de release e publicar SHA/capability no endpoint de status. |
| P3 | Explorer/SDK e falhas históricas | Relatório documenta falhas de serialização e métricas stale | Corrigir fixtures de chave Schnorr, canonical JSON, confirmações e cálculo de taxas; adicionar regressão. |

## 7. Conclusão

Os 91 testes E2E aprovados demonstram boa cobertura funcional do caminho de swap TCP local, sincronização, deduplicação, handoff bridge, adaptador Lightning simulado e componentes da rede de testnet. Eles não demonstram prontidão Mainnet nem cobertura integral do repositório.

A principal conclusão de cobertura é assimétrica: o caminho novo de swap possui módulos entre aproximadamente 55% e 92%, enquanto partes importantes do ecossistema permanecem abaixo de 40% ou sem execução. A próxima etapa tecnicamente mais segura é transformar os outputs atuais em métricas estruturadas, elevar cobertura dos componentes críticos de bridge/consenso/mempool e reexecutar os checks de CI e auditoria independente no `main` mesclado.
