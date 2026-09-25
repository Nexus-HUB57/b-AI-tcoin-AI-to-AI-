# Playbook de incidente: divergência de `tip_hash`

## Objetivo

Este playbook define a resposta quando `scripts/verify_public_pool.py` retorna `NO-GO` porque os nós públicos informam `tip_hash` diferentes. A divergência deve ser tratada como um incidente de integridade de rede até que uma causa benigna seja comprovada.

> Um `tip_hash` divergente não prova sozinho que houve uma violação de consenso. Ele prova que os nós não apresentaram a mesma ponta observável no momento da coleta. A resposta deve distinguir atraso de sincronização, reorganização legítima, backend apontando para cadeias diferentes e falha real de consenso.

## Regra imediata

Ao primeiro `NO-GO` por divergência de `tip_hash`:

1. congelar novos deploys e mudanças de configuração;
2. não executar `terraform apply`, migrações ou purge de dados;
3. não transmitir blocos, transações, payouts ou recompensas;
4. não reiniciar todos os nós simultaneamente;
5. preservar logs e artefatos do GitHub Actions;
6. marcar a rede como `NO-GO` até a causa ser classificada;
7. abrir um registro de incidente com timestamp UTC.

A prioridade é preservar evidência. O operador não deve apagar estado local, limpar bancos ou alterar o tip para fazer os nós parecerem convergentes.

## Severidade

| Nível | Condição | Decisão |
|---|---|---|
| SEV-1 | Divergência persiste em duas ou mais coletas, ou há diferença de genesis, rede, protocolo ou chainwork | Pausar mineração e qualquer payout; escalar imediatamente ao responsável de consenso |
| SEV-2 | Divergência isolada a um nó, com os demais convergentes | Isolar o nó divergente de novas operações; investigar sincronização e runtime |
| SEV-3 | Uma única coleta divergente, corrigida na repetição e explicada por avanço normal da cadeia | Registrar evidência; manter monitoramento reforçado |

A severidade nunca deve ser reduzida apenas porque a altura dos nós é igual. O hash é a evidência mais forte de que eles estão na mesma ponta.

## Fase 1 — Contenção sem mutação

O responsável pelo incidente deve registrar:

- horário UTC da primeira falha;
- SHA do workflow e do repositório;
- ID da execução do GitHub Actions;
- lista de origens consultadas;
- `chain_height`, `tip_hash` e `genesis_hash` de cada nó;
- `node_id`, `protocol_version` e `network`, quando disponíveis;
- contagem de peers e handshakes;
- operadores, provedores, regiões e ASNs declarados no manifesto;
- estado de qualquer pool ou canal de trabalho;
- últimos blocos aceitos e rejeitados, sem incluir segredos.

Reexecutar a auditoria duas vezes, com intervalo de 30 a 60 segundos, usando exatamente as mesmas origens:

```bash
python3 scripts/verify_public_pool.py \
  --api https://node-a.example.org/api \
  --api https://node-b.example.org/api \
  --api https://node-c.example.org/api \
  --api https://node-d.example.org/api \
  --min-peers 3 \
  --require-tip-hash \
  > evidence/tip-divergence-$(date -u +%Y%m%dT%H%M%SZ).json
```

Se a primeira coleta foi feita pelo GitHub Actions, preservar o artefato original antes de executar qualquer diagnóstico adicional.

## Fase 2 — Classificação inicial

### Atraso temporário

Classificar como atraso somente se:

- um único nó estiver atrás;
- o nó atrasado continuar com `chain_valid: true`;
- seus peers e handshakes estiverem ativos;
- ele alcançar o mesmo `tip_hash` em uma nova coleta;
- não houver divergência de genesis, rede ou protocolo;
- não houver bloco inválido ou reorg inesperado nos logs.

Mesmo nesse caso, o resultado histórico continua `NO-GO` até a coleta posterior ser aprovada.

### Backend ou cache incorreto

Investigar se o domínio público aponta para uma réplica antiga, cache, proxy ou processo diferente do daemon esperado. Comparar:

- headers HTTP e timestamp de resposta;
- versão exposta pelo status;
- SHA implantado, se o backend o expuser;
- `tip_hash` consultado diretamente no host e através do domínio público;
- configuração do reverse proxy;
- processo e arquivo de configuração efetivamente carregados.

Não aceitar uma resposta de cache como prova de convergência. O cache deve ser identificado e corrigido pelo operador autorizado, preservando os artefatos anteriores.

### Reorganização legítima

Uma reorganização somente pode ser classificada como legítima quando existir:

- regra de seleção de cadeia documentada;
- chainwork ou critério equivalente comparável;
- logs de fork com tip anterior, tip novo, altura do fork e motivo;
- validação independente dos blocos concorrentes;
- convergência posterior de todos os nós.

A altura isolada não é suficiente. Uma cadeia com a mesma altura pode ter um `tip_hash` diferente.

### Divergência de consenso

Classificar como incidente de consenso se houver qualquer combinação de:

- divergência persistente após reconexão;
- mesmo genesis, mas blocos incompatíveis na mesma altura;
- `chain_valid` falso em qualquer nó;
- regras, dificuldade, timestamp ou coinbase aceitos de forma diferente;
- um pool ou nó aceitando bloco rejeitado por outros;
- diferença de binário ou SHA entre operadores;
- mensagens P2P de protocolo, rede ou genesis incompatíveis.

Nesse caso, pausar mineração externa e payouts. Não tentar resolver escolhendo manualmente um `tip_hash` ou copiando o estado de um nó para outro.

## Fase 3 — Diagnóstico controlado

O diagnóstico deve ser somente leitura sempre que possível. Para cada nó, coletar:

1. resposta de `/status`;
2. resposta de `/p2p/status`;
3. resposta de `/p2p/peers`;
4. logs do daemon no intervalo do incidente;
5. SHA do artefato executado;
6. configuração de rede sem secrets;
7. conectividade com seeds;
8. horário do sistema;
9. estado de sincronização de headers e blocos;
10. eventos de fork, reorg, rejeição e recuperação.

Comparar os nós em uma matriz:

| Campo | Node A | Node B | Node C | Node D |
|---|---|---|---|---|
| `network` |  |  |  |  |
| `genesis_hash` |  |  |  |  |
| `chain_height` |  |  |  |  |
| `tip_hash` |  |  |  |  |
| `chain_valid` |  |  |  |  |
| `node_id` |  |  |  |  |
| `protocol_version` |  |  |  |  |
| `peer_count` |  |  |  |  |
| `handshake_peers` |  |  |  |  |
| código implantado |  |  |  |  |

Não incluir tokens, chaves privadas, credenciais, mnemonics ou conteúdo de arquivos `.env` nessa matriz.

## Fase 4 — Isolamento de um nó divergente

Se a divergência estiver limitada a um nó, o operador pode removê-lo temporariamente do conjunto público de seeds ou do pool, desde que a ação seja autorizada, reversível e registrada. O nó isolado não deve receber novos trabalhos econômicos nem ser usado para confirmar payouts.

Não apagar o diretório de dados. Preservar uma cópia ou snapshot autorizado para investigação. Não substituir a cadeia por cópia de outro nó antes de uma decisão formal do responsável de consenso.

Se a divergência envolver dois ou mais nós, manter a rede em `NO-GO` e escalar como SEV-1. Não declarar uma cadeia canônica por votação administrativa.

## Fase 5 — Recuperação

A recuperação exige todos os critérios abaixo:

- causa raiz documentada;
- correção revisada e identificada por SHA;
- nenhum segredo introduzido nos artefatos;
- todos os nós executando o mesmo protocolo aprovado;
- mesmo `genesis_hash`;
- mesmo `tip_hash` e altura em três coletas consecutivas;
- pelo menos três handshakes por nó;
- `chain_valid: true` em todos;
- teste de restart de um nó por vez aprovado;
- nenhum bloco ou payout pendente sem reconciliação;
- auditoria `verify_public_pool.py --require-tip-hash` retornando `GO`;
- revisão de pelo menos dois responsáveis técnicos para SEV-1.

Após a recuperação, manter monitoramento reforçado por um período de soak definido pelo conselho técnico. O incidente só deve ser encerrado após esse período sem nova divergência.

## Rollback

Se o incidente começou após um deploy, usar o workflow verificado com o último SHA conhecido como saudável. O rollback deve ser manual, com aprovação do ambiente `production`, e deve passar novamente pelo preflight e pela auditoria pública.

Nunca fazer rollback para uma branch flutuante. Usar somente um SHA imutável que tenha evidência anterior de saúde.

## Encerramento e relatório

O relatório final deve conter:

- resumo e severidade;
- linha do tempo UTC;
- nós afetados;
- tip hashes observados;
- causa raiz;
- impacto em mineração, pools, transações e payouts;
- ações de contenção;
- SHA corrigido ou rollback aplicado;
- evidências anexadas;
- testes de recuperação;
- medidas preventivas;
- decisão formal de retorno a `GO`.

O incidente não deve ser encerrado com base apenas em “o site voltou”. A condição de encerramento é a convergência verificável dos nós e a ausência de divergência de consenso não explicada.

## Referências

[1]: ../scripts/verify_public_pool.py "Auditor somente leitura da pool pública"
[2]: ../docs/PUBLIC_PEER_PROVISIONING_RUNBOOK.md "Runbook de provisionamento de peers públicos"
[3]: ../.github/workflows/verify-public-pool.yml "Workflow automático de auditoria da pool pública"
[4]: ../docs/EXTERNAL_P2P_MINING_ROADMAP_BLUEPRINT_HANDBOOK.md "Roadmap e gates de mineração P2P externa"
