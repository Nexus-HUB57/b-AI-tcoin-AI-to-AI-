# Boundary HSM/MPC para assinatura delegada

Este adaptador é uma fronteira **provider-neutral** entre o agente orquestrador e um HSM/MPC externo. Ele foi adicionado em pacote isolado para não modificar os módulos legados de bridge, relayer ou broadcast.

## Garantias

- O orquestrador envia somente `unsigned_tx_hex` e metadados de política.
- Nenhuma seed phrase, chave privada ou material criptográfico secreto entra no repositório.
- O signer só é habilitado explicitamente por `BAITCOIN_SIGNER_ENABLED=true`.
- O endpoint deve ser HTTPS e a credencial vem exclusivamente de `BAITCOIN_SIGNER_TOKEN`.
- Rede, destino, valor, tamanho do payload e `policy_id` são validados antes da chamada.
- A chamada exige `Idempotency-Key` para evitar duplicação.
- Respostas sem `request_id` ou `signed_tx_hex` hexadecimal são rejeitadas.
- Este pacote **não transmite** transações; broadcast continua sendo uma etapa separada e protegida.

## Contrato HTTP esperado

`POST $BAITCOIN_SIGNER_ENDPOINT`

```json
{
  "version": 1,
  "operation": "sign_raw_transaction",
  "network": "bitcoin-mainnet",
  "unsigned_tx_hex": "...",
  "destination": "...",
  "amount_sats": 240700000,
  "policy_id": "btc-mainnet-v1",
  "payload_sha256": "..."
}
```

Resposta mínima:

```json
{"request_id":"provider-request-id","signed_tx_hex":"..."}
```

O provider deve implementar sua própria política de quorum, HSM/MPC, allowlist e aprovação. O agente deve validar novamente a transação assinada (inputs, outputs, fee, rede e assinatura) antes de qualquer broadcaster separado.

## Habilitação controlada

Não habilitar em produção sem endpoint, contrato, política, auditoria e ambiente de testnet aprovados:

```bash
export BAITCOIN_SIGNER_ENABLED=true
export BAITCOIN_SIGNER_ENDPOINT=https://signer.example.internal/v1/sign
export BAITCOIN_SIGNER_TOKEN='injected-by-secret-manager'
```

O valor do token não deve ser salvo em `.env`, logs, commits ou tickets.

## Validação local

```bash
python3 -m pytest -q tests/security/test_hsm_mpc.py
```
