# Síntese Pós-Auditoria — Bloqueadores de Lançamento

**Data:** 2026-09-23
**Escopo:** contratos/deploy, OPSEC/CI, swap/settlement e AI Store/integrations
**Modo:** leitura estática, histórico Git e testes locais; nenhuma transação, assinatura ou broadcast foi executado.

## Veredicto

O ecossistema **não está pronto para produção real 100% Green**. Há respostas HTTP saudáveis e testes locais parciais, mas o caminho econômico e de custódia contém findings críticos que podem produzir saldo fantasma, mint indevido, duplicação de liquidação ou exposição de material sensível.

## Bloqueadores críticos

| ID | Área | Evidência resumida | Decisão |
|---|---|---|---|
| F-OPSEC-01 | Git/OPSEC | `wallet_reports/consolidated_wallets.csv` é rastreado, contém coluna `private_key` e registros não vazios no histórico | congelar deploy; revogar/rotacionar chaves; remover e reescrever histórico com procedimento seguro |
| F-SET-01 | Swap | rota marca `filled`/`settled=true` sem criar, transmitir ou confirmar transação | bloquear `settled` até txid + confirmações + reconciliação |
| F-SET-02 | Bridge | `BridgeManager` aceita authorizer ausente e prova/assinaturas textuais locais | tornar autorização criptográfica obrigatória fora de fixtures |
| F-AI-01 | AI Store | list/purchase/rate sem identidade/assinatura/replay protection efetivos | bloquear mutações econômicas sem autorização verificável |
| F-AI-02 | AI Store | compra retorna confirmação/txHash local sem liquidação on-chain | separar `recorded` de `confirmed` e integrar settlement idempotente |

## Achados altos adicionais

- scripts de deploy usam ABI antigo enquanto os construtores atuais exigem timelock;
- `TIMELOCK_ADDRESS` não é validado on-chain quanto a bytecode, roles e minDelay;
- `l1TxId` pode ser reutilizado com `requestId` diferente;
- reservas de UTXO e retries do custody sweep não são idempotentes;
- CI não possui secret scanning histórico fail-closed e usa permissões/actions mutáveis;
- workflow AI Store clona por referência mutável, desativa validação TLS e publica artefatos potencialmente sensíveis;
- a configuração de contratos ainda indica `deployed_at: null`, `deploy_tx_hash: null` e `verified_on_etherscan: false`.

## Validação executada

- Fusão Fund'DeCaNaMy + BAITHex read-only: **25 passed** após correção dos fixtures sintéticos.
- Smoke/stress Swap–BAITHex: **29 passed, 2 warnings** após instalação isolada de `ecdsa` e `embit`; os warnings são de testes legados que retornam tupla em vez de usar asserts. O resultado é local/regtest e não prova settlement mainnet.
- Probe público: endpoints de status, health, blockchain, agents, swap e stats responderam `200`; `/api/v1/mylink/fund` respondeu `502`. Isso não prova settlement ou custódia.
- `forge`, `solc`, `slither` e `anvil` não estão disponíveis no sandbox; compilação on-chain permanece pendente.

## Plano de remediação obrigatório

1. **Containment:** congelar deploy/listing/bridge/sweep real; mover ativos para chaves novas em ambiente seguro após avaliação; preservar evidência sem copiar segredos.
2. **Settlement:** implementar máquina durável `prepared → broadcasting → broadcast → confirmed → settled/reconciling`, reserva por outpoint, idempotency key e reconciliação pós-crash.
3. **Bridge:** consumir uma identificação canônica de evento L1 uma única vez, exigir proof/threshold verificável e testar replay.
4. **AI Store:** autenticação de agente, nonce/timestamp, autorização por recurso, schema, limites e liquidação real; remover `confirmed`/`txHash` sintéticos.
5. **CI/OPSEC:** secret scanning histórico, permissões mínimas, actions pinadas por SHA, TLS verificado, artefatos assinados e zero segredos/keystores no Git.
6. **Contracts:** sincronizar scripts ABI, validar timelock/roles/chain ID, operadores únicos, limites reservados, EIP-712 e resgate seguro de posições Uniswap.
7. **Evidence:** só promover para mainnet após Forge/Slither/invariant/fuzz, E2E de testnet, prova de custódia ETH e revisão independente.

## Decisão de release

**NO-GO para produção econômica e abertura de mercado.** O branch atual pode receber documentação, harness e correções read-only; nenhum gate deve habilitar signing, broadcast, mint, sweep ou settlement real enquanto os bloqueadores acima estiverem abertos.
