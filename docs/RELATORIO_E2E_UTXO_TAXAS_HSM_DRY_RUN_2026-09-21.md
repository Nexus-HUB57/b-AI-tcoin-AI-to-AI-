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
