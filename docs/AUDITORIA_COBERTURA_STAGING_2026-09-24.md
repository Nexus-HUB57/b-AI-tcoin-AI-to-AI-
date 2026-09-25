# Relatório de auditoria, cobertura e staging

**Repositório:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`  
**Branch auditada:** `audit/baith-obscura-20260923`  
**Commit auditado:** `cfe51edfc7bc66afe84ea823d67a9160a70fd920`  
**Data:** 24 de setembro de 2026  
**Autor:** **Manus AI**

## Conclusão executiva

A branch auditada está sincronizada com o remoto e contém a correção de concorrência do swap book JSON. Os testes específicos de swap, P2P, BAITHex, HSM/MPC, Obscura e SDK mobile passaram. O teste concorrente do MyLink também confirmou que a correção elimina a perda de ofertas observada anteriormente.

O deploy de homologação **não foi executado**. O repositório não possui um ambiente GitHub `staging`. Existe apenas o ambiente `production`. Além disso, o workflow que aceita a opção textual `staging` mantém o job de deploy fixado em `environment: production` e usa o mesmo caminho SSH de produção. Dispará-lo para a branch auditada poderia alterar o ambiente produtivo. A execução foi, portanto, bloqueada de forma deliberada.

Foi disparada somente a validação não destrutiva do workflow **Deploy to Render**, usando o commit auditado. Essa validação falhou no controle de consistência de conteúdo porque `netlify/index.html` não contém o texto exigido `67 REST`. Nenhuma etapa de deploy foi executada por esse workflow.

## Identificação e integridade da branch

A verificação local confirmou:

| Item | Resultado |
|---|---|
| Branch | `audit/baith-obscura-20260923` |
| Commit | `cfe51edfc7bc66afe84ea823d67a9160a70fd920` |
| Rastreamento remoto | `origin/audit/baith-obscura-20260923` |
| Estado local | Limpo antes da auditoria |
| Arquivos Python rastreados | 474 |
| Arquivos de teste | 49 |
| Funções ou métodos de teste identificados estaticamente | 907 |
| Arquivos alterados em relação a `origin/main` | 103 |

O commit auditado é o commit que adiciona o lock de processo e o lock de arquivo ao ciclo de leitura, alteração e gravação do swap book.

## Escopo funcional auditado

A auditoria cobriu quatro áreas principais. A primeira foi o processamento nativo de intents, incluindo assinatura, validação, sincronização e execução. A segunda foi a malha P2P TCP, incluindo fan-out e deduplicação. A terceira foi a composição BAITHex–Obscura e seus limites de autorização. A quarta foi o handler HTTP local do MyLink, com foco na persistência concorrente do book e na idempotência da liquidação.

Também foram executados os contratos estruturais dos SDKs mobile. Esses testes verificam a existência dos providers criptográficos de produção, as dimensões de chaves x-only, os formatos de endereço, os campos de transação e a consistência entre Swift e Kotlin.

## Resultados dos testes executados

### Suíte funcional auditada

A execução combinada dos testes selecionados produziu:

```text
116 passed, 2 warnings in 2.54s
```

Os testes cobriram:

- `native_processing`;
- P2P swap load;
- E2E de stress do swap;
- E2E P2P TCP;
- bridge handoff;
- swap lifecycle;
- BAITHex;
- HSM/MPC;
- integração Obscura;
- SDK mobile nativo.

Os dois warnings são preexistentes e não representam falha funcional. Eles indicam testes que retornam uma tupla em vez de retornarem `None` depois de executar suas assertions.

### Smoke test do MyLink

O script `tests/test_mylink_routes.py` foi executado em um `HOME` temporário para evitar estado residual. Todos os checks passaram:

```text
RESULTADO: TODOS PASSARAM
```

O smoke cobre feed, criação de oferta, consulta do book, execução, preenchimento, validação de endereço e dispatch das rotas.

### Testes P2P e E2E de stress

Os testes existentes de carga e stress passaram:

```text
tests/test_p2p_swap_load.py              1 passed
tests/test_swap_stress_smoke_e2e.py      2 passed
```

O primeiro teste propaga 30 intents por uma malha de cinco nós. O segundo executa o fluxo E2E e uma malha de seis nós com 48 intents.

### Teste concorrente do handler MyLink

Foi executada uma carga direta com 64 ofertas concorrentes usando 16 workers. Antes do lock, 64 ofertas eram aceitas em memória, mas somente três sobreviviam no arquivo JSON por causa da condição de corrida no padrão `load → modify → save`.

Após a correção, o resultado foi:

| Métrica | Resultado |
|---|---:|
| Ofertas submetidas | 64 |
| Ofertas aceitas | 64 |
| Ofertas persistidas | 64 |
| Liquidações submetidas | 64 |
| Liquidações concluídas | 64 |
| Fills persistidos | 64 |
| Falhas | 0 |
| Tempo de criação das ofertas | 45,63 ms |
| Tempo de liquidação | 75,77 ms |

A idempotência também foi verificada com 32 tentativas concorrentes para o mesmo `offer_id`. Somente uma tentativa foi aceita. As outras 31 foram rejeitadas com HTTP 404 e apenas um fill foi persistido.

## Cobertura de código

A medição foi realizada com `coverage` sobre os módulos selecionados para esta auditoria. O conjunto medido incluiu `ops`, `native_processing`, `baith_exchange`, `baitcoin_obscura` e `baitcoin_core/network/p2p_real`. O smoke MyLink foi anexado à medição para incluir a execução real das rotas.

O resultado agregado foi:

| Escopo medido | Instruções | Cobertura |
|---|---:|---:|
| Módulos selecionados | 3.978 | 44% |
| `ops/mylink_routes.py` | 274 | 74% |
| `native_processing/swap_engine.py` | 76 | 87% |
| `native_processing/swap_sync.py` | 108 | 84% |
| `native_processing/webhook_auth.py` | 140 | 79% |
| `native_processing/bridge_handoff.py` | 101 | 88% |
| `native_processing/swap_executor.py` | 239 | 62% |
| `native_processing/swap_protocol.py` | 126 | 75% |
| `baitcoin_core/network/p2p_real/node.py` | 378 | 66% |
| `baitcoin_core/network/p2p_real/protocol.py` | 164 | 74% |
| `baitcoin_obscura/bridge.py` | 260 | 58% |
| `baith_exchange/obscura.py` | 34 | 100% |

A cobertura agregada não deve ser interpretada como cobertura de todo o repositório. Ela é uma medição dirigida aos módulos relevantes para swap, processamento nativo, P2P, BAITHex e Obscura. Scripts operacionais e módulos não exercitados pelo conjunto selecionado permanecem com cobertura parcial ou nula.

As áreas prioritárias para aumentar a cobertura são `baitcoin_obscura/bridge.py`, `native_processing/swap_service.py`, `native_processing/native_adapters.py`, `native_processing/swap_executor.py` e os caminhos excepcionais de `baitcoin_core/network/p2p_real/node.py`.

## Validação CI da branch

Foi disparado o workflow `Deploy to Render` manualmente sobre a branch auditada e sobre o commit `cfe51edfc7bc66afe84ea823d67a9160a70fd920`.

**Execução:** [GitHub Actions run 36031179431](https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/actions/runs/36031179431)

O resultado foi `failure`. Os seguintes passos passaram:

- instalação de dependências;
- validação de imports;
- validação do servidor API;
- validação dos arquivos HTML;
- verificação de sintaxe JavaScript.

O passo que falhou foi **Check content consistency**, com a mensagem:

```text
ERROR: netlify/index.html missing 67 REST
```

O workflow exige que `netlify/index.html` contenha `67 REST`. A falha é de consistência de conteúdo e não foi causada pelos módulos de swap auditados.

## Deploy de homologação

O deploy de staging não foi executado por falta de um alvo de homologação seguro e configurado.

A inspeção dos ambientes GitHub encontrou somente:

```text
production
```

O workflow `go-live.yml` declara uma opção de input chamada `staging`, mas o job de deploy contém:

```yaml
environment: production
```

O job também usa os segredos e o VPS configurados para produção. Portanto, a seleção textual `staging` não cria isolamento real. Ela não deve ser usada como substituta de um ambiente de homologação.

O workflow `deploy.yml` também não oferece staging. Ele executa transferência SSH para o VPS configurado e suas validações apontam diretamente para `https://www.mybait.org`.

Para permitir um deploy de homologação seguro, é necessário configurar um ambiente GitHub `staging`, segredos separados e um destino separado. O workflow deve usar o ambiente selecionado de forma dinâmica e deve impedir que um input `staging` reutilize `environment: production` ou o VPS produtivo.

## Riscos e recomendações

O principal risco bloqueador é a ausência de separação real entre staging e produção. A branch não deve ser publicada por um workflow que tenha apenas uma opção nominal de staging, mas continue conectado ao VPS produtivo.

O segundo ponto é a falha de consistência de conteúdo em `netlify/index.html`. Antes de qualquer publicação web, esse arquivo deve ser alinhado ao contrato que exige `67 REST`, ou o teste CI deve ser atualizado se o contrato correto tiver mudado.

A correção de concorrência do swap book funcionou no teste de carga, mas o armazenamento continua sendo um arquivo JSON. Para múltiplos processos de alta taxa, SQLite transacional ou outro armazenamento com operações atômicas seria mais robusto. O lock atual reduz o risco de corrupção e perda de atualização entre threads e processos no mesmo host, mas não substitui uma camada de persistência transacional distribuída.

## Estado final

A branch auditada está tecnicamente validada para os fluxos locais cobertos por este relatório. O estado de CI web está bloqueado por uma divergência de conteúdo conhecida. O deploy de staging permanece pendente até que um ambiente isolado seja configurado.

A `main` não foi alterada durante esta auditoria.

## Referências

[1]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/tree/audit/baith-obscura-20260923 "Branch audit/baith-obscura-20260923"

[2]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/commit/cfe51edfc7bc66afe84ea823d67a9160a70fd920 "Commit de correção de concorrência do swap book"

[3]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/actions/runs/36031179431 "Execução CI Deploy to Render da branch auditada"

[4]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/actions "Histórico de workflows GitHub Actions do repositório"
