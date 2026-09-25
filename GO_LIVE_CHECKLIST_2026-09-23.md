# GO-LIVE CHECKLIST — b'AI'tcoin / BAITHex

**Versão:** 2026-09-23
**Estado atual:** **BLOQUEADO para go-live financeiro**
**Escopo:** validação da cadeia interna b'AI'tcoin, matching BTC/BAIT, settlement e readiness EVM.
**Fora do escopo:** autorização de sweep Bitcoin, broadcast Mainnet, prova de custódia ou declaração de reservas.

> **Regra de segurança:** endpoint disponível, offer preenchida ou estado `settled` em banco local não é prova de liquidação on-chain. Cada gate precisa de evidência identificável, reproduzível e independente.

## 1. Classificação dos ambientes

| Ambiente | Uso permitido | Estado |
|---|---|---|
| b'AI'tcoin Mainnet declarada pela API | Observação pública e reconciliação | Parcialmente observável |
| Bitcoin Mainnet | Somente watch-only até prova BIP-322, UTXO reconciliado e PSBT aprovado | Bloqueado |
| Ethereum Mainnet | Somente após tx hash, bloco, verificação de contrato e HSM/multisig comprovados | Não comprovado |
| Regtest/test fixtures | Testes automatizados locais sem valor econômico | Permitido para QA |

A expressão `b'AI'tcoin Mainnet` não significa Bitcoin Mainnet. Os relatórios devem manter essas redes separadas em todos os campos, dashboards e conclusões.

## 2. Gates obrigatórios

| ID | Gate | Critério de aprovação | Evidência exigida | Estado |
|---|---|---|---|---|
| G-01 | API e health | Todos os endpoints read-only essenciais respondem e o schema é válido | Snapshot com timestamp, URL, HTTP e hash do payload | Observado |
| G-02 | Cadeia | Altura, hash anterior, UTXO, mempool e consenso reconciliam em mais de uma fonte | Nó independente ou export reprodutível do estado | Pendente |
| G-03 | Transação A2A | Existe pelo menos uma tx não-coinbase identificável | txid, altura, inputs, outputs e relação com o order_id | Bloqueado |
| G-04 | Matching | Book, order, fill e idempotency key formam uma única intenção | Export imutável do ledger | Parcial |
| G-05 | Depósito BTC | UTXO correto, rede correta, recipient correto e confirmações suficientes | txid:vout, scriptPubKey, valor, altura e fonte independente | Bloqueado |
| G-06 | Settlement BAIT | `BAIT_SUBMITTED` só avança para `SETTLED` após tx confirmada | txid BAIT, bloco, confirmação e reconciliação | Bloqueado |
| G-07 | Payout BTC | Saída BTC é criada, assinada por política autorizada e confirmada | PSBT, payload hash, 2-de-3 ou HSM, txid e confirmação | Bloqueado |
| G-08 | Master pool | Pool possui endereços/UTXOs reconciliados e saldo positivo | Snapshot watch-only independente | Bloqueado; API observada em zero |
| G-09 | ParityGate | Attestation BAIT/USDT válida, quorum >= 3, não expirada e auditável | Envelope assinado, round_id, fontes e digest | Pendente |
| G-10 | Tesouraria | Receita A2A → tesouraria → staking reconciliada | Ledger, saldos antes/depois e txids | Bloqueado |
| G-11 | Contratos EVM | Deploy real, ownership, multisig, timelock e invariantes verificados | tx hashes, blocos, endereços e explorer | Não comprovado |
| G-12 | Segurança | Nenhum segredo no Git/logs; rotação concluída; signer separado | Varredura, rotação e relatório de incidente | Bloqueado |
| G-13 | Observabilidade | Reorg, mempool, confirmações, falhas e reconciliação monitorados | Runbook e alertas testados | Pendente |
| G-14 | Aprovação | Dois revisores independentes aprovam o lote e o payload final | Registro de aprovação com hashes | Pendente |

**Nenhum gate bloqueado pode ser contornado por configuração, variável de ambiente ou execução manual.**

## 3. Checklist para uma offer pending

O procedimento abaixo é um **runbook de pré-validação**. O script associado opera em `dry-run` por padrão e não transmite nada.

### Identidade e estado

- [ ] Registrar `offer_id`, `order_id`, `client_order_id`, `quote_id` e hash da intenção.
- [ ] Confirmar que a intenção não expirou e que o payload não mudou.
- [ ] Confirmar que a offer não está `SETTLED`, `REFUNDED` ou `RECONCILING`.
- [ ] Confirmar idempotency key e ausência de processamento concorrente.
- [ ] Confirmar que `settlement: on-chain-pending-broadcast` é apenas estado de pendência, não liquidação.

### Depósito e rede

- [ ] Confirmar rede explicitamente; nunca inferir Mainnet por nome de campo.
- [ ] Localizar `txid:vout` do depósito.
- [ ] Conferir recipient, scriptPubKey e valor contra a intenção.
- [ ] Confirmar número mínimo de confirmações.
- [ ] Confirmar que o outpoint não foi usado por outra ordem.
- [ ] Reconciliar o depósito em uma segunda fonte independente.

### Paridade e settlement BAIT

- [ ] Validar attestation de paridade com quorum de pelo menos 3 fontes.
- [ ] Confirmar `round_id`, validade temporal, tolerância e digest.
- [ ] Confirmar que o signer/bridge está externo ao processo de pré-validação.
- [ ] Produzir PSBT ou payload unsigned identificável; não assinar no servidor.
- [ ] Após assinatura autorizada, decodificar novamente inputs, outputs, fee e destinatário.
- [ ] Transmitir somente por broadcaster separado, depois de aprovação independente.
- [ ] Confirmar tx BAIT no explorer e em um segundo observador.
- [ ] Só então atualizar o estado para `SETTLED`.

### Payout BTC

- [ ] Confirmar que o destino pertence à allowlist aprovada.
- [ ] Confirmar que o `master_pool` possui UTXO suficiente.
- [ ] Construir PSBT com fee e change revisados.
- [ ] Obter quorum externo de assinatura.
- [ ] Confirmar txid, mempool e bloco.
- [ ] Publicar somente evidência pública mínima, sem chaves ou seeds.

## 4. Critérios de bloqueio imediato

Interromper e registrar `BLOCKED` se ocorrer qualquer um dos seguintes eventos:

- `master_pool.btc == 0`, `addresses == 0` ou `utxos == 0`;
- explorer mostra apenas `coinbase` e não há tx de settlement;
- o endereço de custódia não coincide com a allowlist aprovada;
- falta de txid, bloco ou confirmações independentes;
- attestation ausente, expirada ou sem quorum;
- payload ou outpoint alterado após admissão;
- qualquer chave privada, WIF, seed ou passphrase aparece em arquivo, log ou ambiente não autorizado;
- signer e broadcaster estão no mesmo processo sem separação de controle;
- deploy EVM não possui tx hash e bloco verificáveis;
- pedido para executar sweep, broadcast ou movimentar fundos sem PSBT e aprovação independente.

## 5. Resultado conhecido em 23/09/2026

A API pública foi observada respondendo, mas a amostra do explorer continuou composta por `coinbase`. O `swap/book` expôs matching/fills e `master_pool` zerado. Não foi comprovada transferência A2A não-coinbase, settlement BAIT confirmado, payout BTC, tesouraria reconciliada ou deploy EVM Mainnet.

Resultado operacional: **não liberar go-live financeiro** e **não executar sweep/broadcast**.

## 6. Comandos seguros

```bash
# Apenas pré-validação local; não assina nem transmite.
python3 scripts/force_settlement_offer.py \
  --db /path/to/executor.sqlite \
  --order-id <ORDER_ID> \
  --dry-run

# Validar o código sem rede ou carteira.
python3 -m py_compile scripts/force_settlement_offer.py
python3 -m py_compile scripts/validate_mybait_live_e2e.py
```

O comando de execução real permanece deliberadamente bloqueado neste repositório. A liberação exige um signer/HSM externo, PSBT, broadcaster separado, allowlist de destino, aprovação independente e evidência de reconciliação.

## 7. Aprovação

| Papel | Nome/ID | Data | Hash do payload | Assinatura/aprovação |
|---|---|---|---|---|
| Operador |  |  |  |  |
| Revisor independente 1 |  |  |  |  |
| Revisor independente 2 |  |  |  |  |
| Observador de reconciliação |  |  |  |  |

Sem os quatro registros preenchidos, o estado permanece **BLOQUEADO**.
