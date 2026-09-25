# Matriz de Remediação Cirúrgica E2E — Goal 1–10

## Estado atual

Esta entrega aplica guards fail-closed, idempotência e contratos mais honestos sem apagar histórico, keystores ou dados existentes. O lançamento econômico permanece **NO-GO** até os itens pendentes serem executados em ambiente seguro.

| # | Bloqueador | Correção aplicada nesta branch | Estado |
|---:|---|---|---|
| 1 | `settled=true` sem transação confirmada | `swap_execute_v2` exige `settlement_tx` hexadecimal de 64 caracteres e pelo menos uma confirmação; sem isso retorna `409 settlement_confirmation_required` | Implementado |
| 2 | Bridge sem autorização criptográfica | `BridgeManager` e `SwapBridgeHandoff` falham fora do modo local explícito quando `RelayerAuthorization` está ausente | Implementado; chaves reais pendentes |
| 3 | Replay de `l1TxId` | `BridgeLock` registra `consumedL1TxIds`, rejeita zero/replay e rejeita recipient zero | Implementado no contrato; Forge pendente |
| 4 | Rate limit apenas no mint | `BridgeLock` adiciona `dailyReserved` e reserva o limite no request antes de confirmações | Implementado no contrato; Forge pendente |
| 5 | Conflitos de intents ignorados | `NativeSwapService` transforma conflito do `SwapSyncStore` em erro terminal | Implementado |
| 6 | Parity digest divergente | payload nativo usa `ParityAttestation.digest()` canônico | Implementado |
| 7 | Sweep não retryava falhas | endereços só entram em `done_addrs` quando há `ok=true` e txid | Implementado; lock de outpoint persistente pendente |
| 8 | AI Store aceitava preço inválido/identidade anônima | validações de schema, preço positivo, tamanho, provider/buyer obrigatório e rotas mutáveis protegidas por identidade | Implementado |
| 9 | AI Store confirmava compra sem settlement | compra fica `pending_settlement`; rating exige compra `settled`; `settle_purchase` valida txid/confirmations | Implementado no runtime; settlement on-chain real pendente |
| 10 | CI/deploy permissivo e publicação de código | Foundry CI fail-closed, permissions mínimas, secret scan, SHA obrigatório do AI Store, TLS verificado e tarballs removidos | Implementado parcialmente; pinagem completa de actions e purge histórico pendentes |

## Ações deliberadamente não automatizadas

A branch não remove `wallet_reports/consolidated_wallets.csv`, keystores ou objetos Git históricos. Esses dados podem conter material sensível e a purga exige: congelamento operacional, inventário de saldos, geração de novas chaves em HSM/hardware wallet, migração controlada, revogação, preservação de evidência e aprovação do proprietário. Sem isso, remover arquivos pode destruir evidência ou causar perda de acesso.

A branch também não habilita `CUSTODY_ARMED`, signing, broadcast, mint, deploy ou settlement real. O modo `BAIT_ALLOW_INSECURE_LOCAL=1` existe apenas no fixture de testes e não deve ser configurado em produção.

## Validação

- Regressões de guards + Swap/BAITHex + Fund'DeCaNaMy: **36 passed, 2 warnings legados**.
- O resultado é local/regtest; não prova saldo, custódia, bytecode verificado, settlement mainnet ou readiness de IPO/listing.
- Forge/solc/Slither/anvil precisam ser executados no CI ou em ambiente com toolchain instalada antes de qualquer deploy.
