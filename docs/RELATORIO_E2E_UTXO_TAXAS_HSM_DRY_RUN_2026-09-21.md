# Relatório E2E local: UTXO, taxas e assinatura HSM em dry-run

**Data:** 21 de setembro de 2026
**Branch:** `feat/hex-evm-dry-run`
**Ambiente:** sandbox local, sem RPC externo e sem broadcast

## Resultado executivo

A validação integrada local foi concluída com **81 testes aprovados**. O escopo cobriu o verificador UTXO, conservação de valor, cálculo de taxas, política de fee mínimo, auditoria HEX/swap, transporte P2P TCP, fluxo nativo de swap, validação integrada e um harness de assinatura compatível com uma interface HSM.

O componente HSM usado nesta etapa é um **mock exclusivamente de teste**. Ele gera uma chave efêmera em memória, libera somente a assinatura para o verificador e não expõe o material privado. Nenhum endpoint HSM real foi acessado. O harness não possui capacidade de RPC ou broadcast.

## Artefatos

| Arquivo | Função |
|---|---|
| `tools/hsm_signing_e2e_dry_run.py` | Harness local com interface `sign_digest`, UTXO de teste, assinatura Schnorr, verificação e bloqueio de broadcast |
| `tests/test_hsm_signing_e2e_dry_run.py` | Testes da assinatura mock, fee e rejeição de payload que não seja digest de 32 bytes |
| `tools/hex_tx_dry_run.py` | Auditoria de transação account-based HEX/EVM, sem chave, RPC ou transmissão |
| `tests/test_utxo_hex_swap_audit.py` | Casos existentes de paridade e depósito HEX/UTXO |

## Estrutura das ações E2E

| Etapa | Ação executada | Evidência |
|---|---|---|
| 1. Preparação | Criar UTXO local de `100.000 sats` associado à chave pública efêmera do signer mock | `MockHSMSigner` |
| 2. Construção | Criar transação de transferência com uma entrada e uma saída de `99.000 sats` | `Transaction` |
| 3. Digest | Calcular `tx_id` da transação sem assinatura | `Transaction.tx_id` |
| 4. Assinatura | Solicitar assinatura Schnorr ao signer mock via `sign_digest(32 bytes)` | assinatura de 64 bytes em memória |
| 5. Verificação | Validar existência da UTXO, ausência de double-spend, conservação de valor, assinatura e gas limit | `TransactionVerifier.verify()` |
| 6. Taxa | Calcular `fee = input_sum - output_sum` e tamanho estimado | `1.000 sats`, `291 bytes`, aproximadamente `3 sat/vB` |
| 7. Broadcast | Tentar avançar o fluxo operacional | bloqueado; o harness não possui RPC/broadcaster |
| 8. Auditoria | Emitir somente identificadores e métricas não secretas; assinatura é mascarada na saída CLI | sem chave privada ou segredo persistido |

## Comandos reproduzíveis

```bash
cd /home/ubuntu/p2p-test-repo

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
python3 -m pytest -q \
  tests/test_utxo_hex_swap_audit.py \
  tests/test_hsm_signing_e2e_dry_run.py \
  tests/test_hex_tx_dry_run.py \
  tests/test_native_processing.py \
  tests/test_p2p_swap_tcp_e2e.py \
  tests/test_e2e_full_validation.py
```

Resultado observado:

```text
81 passed in 1.07s
```

Execução do harness HSM local:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
python3 tools/hsm_signing_e2e_dry_run.py
```

Resultado resumido:

```text
fee_sats: 1000
estimated_size_bytes: 291
fee_rate_sat_vb: 3
broadcast: blocked
```

Execução do auditor HEX/EVM:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
python3 tools/hex_tx_dry_run.py \
  tests/fixtures/hex_evm_tx_dry_run.json \
  --native-balance-wei 10000000000000000
```

Resultado resumido:

```text
chain_id: 369
nonce: 42
calldata_bytes: 36
max_fee_native: 0.006
signing: blocked
broadcast: blocked
```

## Contrato para um HSM real

A implementação de produção deve substituir `MockHSMSigner` por um cliente de HSM ou custodiante que aceite apenas um identificador de chave e um digest canônico. O agente não deve receber seed, WIF, chave privada ou material equivalente. O adaptador real deve validar o `key_id`, impor allowlist de algoritmo e curva, retornar a assinatura e registrar auditoria sem segredo.

A integração de produção ainda requer endpoint autenticado, TLS/mTLS, política de autorização, proteção contra replay, controle de nonce, allowlist de contrato e rede, limite de valor, dupla aprovação e uma etapa independente para broadcast. Esses componentes não foram ativados nesta execução.

> **Conclusão:** o fluxo local de UTXO, taxas e assinatura simulada está validado. O resultado não representa assinatura HSM real, transmissão on-chain ou confirmação de bloco.


## Política dinâmica de taxa sat/vB

A política local usa `FeeEstimator` e `FeeMarket`:

| Parâmetro | Valor | Comportamento |
|---|---:|---|
| `MIN_FEE_RATE` | 1 sat/vB | Piso absoluto de aceitação e estimativa |
| `DEFAULT_FEE_RATE` | 10 sat/vB | Fallback quando não há histórico de blocos |
| `MAX_FEE_RATE` | 1.000.000 sat/vB | Teto contra valores absurdos |
| `BLOCK_MAX_WEIGHT` | 4.000.000 | Capacidade máxima simplificada do bloco |
| `BASE_TX_SIZE` | 100 bytes | Base do estimador de tamanho |
| histórico | 20 blocos | Janela mantida pelo estimador |

A estimativa é dependente do alvo de confirmação. Para o próximo bloco (`target_confirmations <= 1`), o estimador usa a mediana do histórico. Para 2–3 confirmações, usa o percentil aproximado de 25%. Para alvos maiores, usa o menor valor observado. Em todos os casos, o resultado é limitado pelo piso de 1 sat/vB.

O `FeeMarket` rejeita taxas abaixo de `min_fee_rate` ou acima de `MAX_FEE_RATE`, ordena o mempool por sat/vB decrescente e calcula `total_fee = fee_rate × tx_size`. A seleção para bloco respeita o peso máximo e retorna a mediana das taxas selecionadas.

Na validação executada, o histórico `[2, 4, 8, 16]` produziu:

```text
1 confirmação: 8 sat/vB
3 confirmações: 4 sat/vB
6 confirmações: 2 sat/vB
```

Esses valores são política do código local; não representam uma recomendação atual de fee para Bitcoin Mainnet nem consultam mempool externo.

## Simulação de rejeição do HSM

O teste `run_rejection_simulation()` usa um signer que rejeita deliberadamente qualquer digest válido com `HSM_REJECTED`. O orquestrador simulado executa:

1. Mantém a transação no estado `unsigned`.
2. Solicita assinatura ao HSM.
3. Recebe rejeição de política.
4. Transiciona para `signing_rejected`.
5. Mantém `mutation: none`.
6. Mantém `broadcast_attempted: false`.
7. Emite `pause_and_alert`.

Resultado observado:

```json
{
  "state": "signing_rejected",
  "error": "HSM_REJECTED: policy denied test key operation",
  "broadcast_attempted": false,
  "mutation": "none",
  "action": "pause_and_alert"
}
```

A rejeição é tratada como falha terminal para aquela tentativa. O fluxo não deve fazer retry automático sem uma nova autorização, uma nova avaliação de nonce e uma revisão da política do HSM.


## Recuperação pós-alerta operacional do HSM

Foi executado um fluxo de recuperação local após uma rejeição de assinatura. O agente não faz retry imediato: primeiro registra o alerta, pausa a execução e exige mitigação e revalidação independente.

O fluxo validado foi:

```text
ready
  → HSM_REJECTED
  → alerted
  → paused
  → payload_revalidated
  → signer_reauthorized
  → signed
  → broadcast blocked
```

A revalidação verificou digest, nonce, `chain_id` e limites. Após a mitigação, um signer de teste autorizado foi injetado e a assinatura foi aceita. Nenhuma UTXO, ordem ou ledger foi mutado e `broadcast_attempted` permaneceu `false`.

Quando a revalidação foi forçada a falhar, o estado permaneceu `paused`, com `mutation: none` e sem tentativa de broadcast. Esse é o comportamento esperado para impedir que a recuperação contorne uma mudança de payload, nonce, rede ou limite.

Resultado observado:

```json
{
  "audit_events": [
    "hsm_alert",
    "executor_paused",
    "payload_revalidated",
    "signer_reauthorized",
    "signature_accepted"
  ],
  "broadcast_attempted": false,
  "final_state": "signed",
  "mutations": []
}
```

Os testes de recuperação e assinatura passaram com `7 passed`; a regressão E2E dos componentes UTXO, taxas, swap, P2P e HEX/EVM passou com `79 passed`.


## Análise de escala do recovery HSM

A implementação atual de `RecoveryOrchestrator` não contém recursão, busca em árvore, retry automático ou fan-out interno. Cada recuperação executa um número constante de operações: validar estado, validar digest, chamar `revalidate()`, trocar o signer, solicitar uma assinatura e registrar eventos. Portanto, o custo por recuperação é **O(1)** e o custo de `n` recuperações independentes é **O(n)**.

Há três limites importantes antes de uma implantação em larga escala:

| Área | Observação | Risco |
|---|---|---|
| Eventos | `audit_events` cresce linearmente dentro de cada instância | memória cresce sem retenção ou limite |
| Concorrência | não existe limite no próprio orchestrator | fila externa deve impor backpressure |
| Recuperação | não há retry automático nem deduplicação global | retry deve ficar fora do signer e exigir revalidação |

O desenho não apresenta potencial exponencial no estado atual. Uma explosão combinatória só surgiria se uma camada externa combinasse cada alerta com múltiplos signers, payloads, nonces ou caminhos de retry sem deduplicação. Essa camada não existe no harness atual e não foi criada no teste.

## Stress test local

Foi executado o comando:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
python3 tools/hsm_recovery_stress_dry_run.py \
  --count 256 --workers 8
```

Resultado:

```text
requested:               256
completed:               256
failed:                    0
workers:                   8
elapsed_seconds:       1.104981
recovery_rate:       231.68 / second
broadcast_attempts:       0
mutations:                 0
```

Cada caso usou um artefato UTXO sintético e um digest independente. O fluxo simulou rejeição inicial, pausa, revalidação do artefato, reautorização do signer e nova assinatura. O método `broadcast()` foi chamado apenas para confirmar que o bloqueio dry-run permanece ativo; nenhuma rede, RPC, HSM real ou transação HEX foi acessada.

A regressão dos componentes UTXO, taxas, Swap, P2P e HEX/EVM permaneceu verde com **79 testes aprovados**. Os testes específicos de recuperação e stress passaram com **6 testes aprovados**.

## Recomendações para escala real

Antes de ampliar o fluxo, adicionar limite explícito de concorrência, fila bounded, chave idempotente por `(artifact_id, digest, nonce)`, TTL para eventos, métricas de fila e circuit breaker do HSM. A recuperação deve permanecer pausada quando houver divergência de digest, nonce, chain ID, contrato, UTXO ou limite. Nenhum aumento de throughput deve permitir retry automático de assinatura ou broadcast.
