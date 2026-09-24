# Relatório de status: swap BTC/BAIT, BridgeManager e prontidão Mainnet

**Data da revisão:** 13 de setembro de 2026
**Repositório:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`
**Branch revisada:** `main`
**Commit revisado:** `329a6b4` — `security: verify relayer proof signatures before submission`
**Autor:** **Manus AI**

## 1. Conclusão executiva

O repositório está sincronizado com `origin/main` no commit `329a6b4`. O fluxo nativo de swap BTC/BAIT possui separação entre cotação, criação de intenção assinada, propagação P2P, admissão pelo executor, observação do depósito Bitcoin e liquidação. O handoff para o `BridgeManager` possui lock idempotente, submissão incremental de provas, autorização criptográfica Ed25519 por relayer, limiar N-of-M e mint idempotente.

A validação local dos fluxos de swap, autorização, bridge e rede P2P foi executada. Os testes específicos desses fluxos passaram. A bateria de readiness Mainnet também passou nos testes selecionados. Quatro expectativas legadas do SDK mobile foram alinhadas aos contratos atuais sem alterar a implementação de produção, e a execução final ficou verde nos testes selecionados.

A revisão não comprova uma operação real em Bitcoin Mainnet. Não foram usadas chaves privadas, assinadas transações reais, transmitidos hexadecimais assinados ou movimentados fundos. A prontidão de Mainnet foi avaliada por código, configuração e testes locais. A validação operacional real ainda requer infraestrutura, endpoints RPC, monitoramento, políticas de autorização e uma execução manual controlada pelo operador.

> **Status recomendado:** tecnicamente avançado para validação de integração e preparação operacional; **não aprovado, com as evidências disponíveis nesta sessão, para declarar liquidação real em Mainnet concluída**.

## 2. Estado do repositório

| Item | Resultado |
|---|---|
| Branch local | `main` |
| Commit local | `329a6b4` |
| Commit remoto | `329a6b4` |
| Divergência Git | Nenhuma |
| Alterações de trabalho antes da revisão | Nenhuma alteração de código indicada pelo status Git |
| Push do commit de segurança | Concluído anteriormente |
| Force-push ou reset nesta revisão | Não executado |

O último commit adicionou a verificação individual de assinatura Ed25519 no caminho `Relayer.relay_event()`. O `BridgeManager` remoto já possuía uma segunda camada de validação por `verify_one()`, e ambas as camadas permanecem alinhadas.

## 3. Fluxo completo do swap BTC/BAIT

O fluxo nativo é composto por etapas com responsabilidades separadas.

| Etapa | Componente | Estado ou resultado | Evidência |
|---|---|---|---|
| Cotação | `SwapEngine` | `SwapQuote` com montante, preço, validade e identificador | `native_processing/swap_engine.py` |
| Ordem | `SwapEngine.place_order()` | Ordem associada ao `order_id` determinístico | `native_processing/swap_engine.py` |
| Intenção | `sign_quote()` | `SwapIntent` assinada com Ed25519 | `native_processing/swap_protocol.py` |
| Propagação | `SwapSyncStore` e P2P | Admissão, deduplicação e gossip da intenção | `native_processing/swap_sync.py` e `baitcoin_core/network/p2p_real/` |
| Admissão | `SwapExecutor.admit()` | Validação da intenção e persistência do pedido | `native_processing/swap_executor.py` |
| Depósito | adaptador Bitcoin | Localização e validação do depósito | `native_processing/swap_executor.py` e adaptadores nativos |
| Liquidação | `SwapExecutor.process()` | Transição para settlement ou reconciliação | `native_processing/swap_executor.py` |
| Serviço | `NativeSwapService` | Orquestra engine, sync store, executor e P2P | `native_processing/swap_service.py` |

A intenção carrega identidade, montante BTC, montante BAIT, validade, nonce, chave pública e assinatura. O executor não deve receber uma intenção não validada pelo protocolo. A camada de serviço também verifica que o `order_id` criado pelo engine coincide com o `order_id` da intenção assinada.

## 4. Handoff para o BridgeManager

O `SwapBridgeHandoff` conecta uma `SwapIntent` válida ao ciclo lock/proof/mint da bridge. A intenção é validada antes de criar o lock. A correlação persistida em SQLite mantém a associação entre `order_id`, `transfer_id` e `event_id`.

### 4.1 Lock

`start_lock()` executa as seguintes verificações:

1. Valida a intenção e a assinatura Ed25519.
2. Valida `target_chain_id` e recipient.
3. Reutiliza o lock existente quando o mesmo `order_id` é repetido com os mesmos campos imutáveis.
4. Rejeita conflito de recipient, chain ou montante.
5. Persiste o resultado do lock antes de retornar.

A operação é idempotente no nível do `order_id`; uma repetição não cria uma segunda transferência.

### 4.2 Autorização criptográfica da prova

Cada relayer assina um envelope canônico com prefixo de domínio `bait.bridge.proof.v1`. O payload inclui:

```text
version
event_id
transfer_id
chain_id
amount_sats
proof
```

O `RelayerAuthorization` mantém um registry de chaves públicas Ed25519. O `Relayer` assina com sua chave privada e verifica individualmente a assinatura antes de chamar `BridgeManager.submit_proof()`. O `BridgeManager` remoto também verifica a assinatura, o evento e a prova antes de alterar o estado do evento.

Essa dupla verificação impede que uma assinatura válida seja reutilizada para outro evento, transferência, cadeia, montante ou prova. Assinaturas inválidas, signers desconhecidos, duplicatas e relayers sem autorização são rejeitados sem mutação do evento.

### 4.3 N-of-M e mint

O `BridgeConfig` padrão usa limiar de **3 assinaturas em um conjunto de 5 signers**. O handoff submete as assinaturas incrementalmente:

```text
1/3 → pending_proof
2/3 → pending_proof
3/3 → mint_wrapped()
```

O mint ocorre somente quando `ready_to_mint` é verdadeiro. `BridgeManager.mint_wrapped()` é idempotente: uma repetição retorna o resultado existente e não incrementa novamente os totais.

## 5. Evidência de validação executada

### 5.1 Fluxos de swap, bridge e rede

O comando de regressão integrado passou nos componentes relevantes, incluindo swap nativo, handoff, autorização, E2E TCP e rede P2P:

```text
72 passed, 1 warning in 0.40s
```

O warning é um `PytestCollectionWarning` preexistente relacionado à classe `TestnetManager` com construtor próprio.

### 5.2 Readiness Mainnet

A seleção de testes de produção, launcher e readiness passou:

```text
44 passed, 25 deselected in 5.04s
```

Esse resultado valida contratos e checklists locais. Ele não é prova de que um daemon público está sincronizado, de que os seed nodes estão acessíveis, de que um RPC externo está saudável ou de que uma transação foi confirmada na rede.

### 5.3 Suíte ampla

A execução final combinando swap, autorização, bridge, P2P, produção, readiness e fases relacionadas teve o seguinte resultado:

```text
256 passed, 1 warning in 6.01s
```

Antes do alinhamento, quatro expectativas estavam concentradas no SDK mobile:

| Teste | Divergência observada | Classificação |
|---|---|---|
| `TestMobileWallet::test_create_wallet` | Teste esperava `bait`; implementação usa o prefixo atual `b'` | Corrigido no teste |
| `TestMobileWallet::test_import_wallet` | Teste fornecia texto que não era uma chave hexadecimal de 32 bytes | Corrigido no teste |
| `TestMobileWallet::test_address_derivation` | Teste esperava o prefixo antigo | Corrigido no teste |
| `TestMobileSecurity::test_encrypt_decrypt_key_bundle` | Teste esperava `pbkdf2-sha256-xor`; implementação atual usa AES-256-GCM | Corrigido no teste, preservando AES-256-GCM |

Essas divergências não afetavam o fluxo BTC/BAIT, a autorização dos relayers, o BridgeManager ou o E2E TCP. Os testes foram atualizados somente para refletir contratos já implementados; a implementação AES-256-GCM não foi enfraquecida.

## 6. Avaliação de prontidão Mainnet

| Controle | Situação | Observação |
|---|---|---|
| Validação de intenção assinada | Passa localmente | Ed25519, identidade e validade verificadas |
| Gossip P2P de intenção | Passa nos testes E2E | Não substitui monitoramento de produção |
| Detecção e validação de depósito | Implementada no executor | Requer adaptador Bitcoin configurado e RPC real |
| Lock no BridgeManager | Passa localmente | Idempotência testada |
| Assinatura de relayers | Passa localmente | Verificação individual Ed25519 antes do submit |
| Limiar N-of-M | Passa localmente | Padrão 3 de 5 |
| Mint idempotente | Passa localmente | Repetição não duplica emissão |
| RPC Bitcoin Mainnet | Não comprovado nesta sessão | Requer endpoint, credenciais e health check operacional |
| Sincronização de daemon | Não comprovada nesta sessão | Requer inspeção do processo e altura de bloco real |
| Broadcast Bitcoin real | Não executado | Exige payload hexadecimal assinado e confirmação operacional |
| Confirmação on-chain | Não comprovada | Nenhuma transação foi transmitida nesta revisão |
| SDK mobile | Passa nos testes selecionados | Contratos de endereço, importação e AES-256-GCM alinhados |

## 7. Divergências e ações recomendadas

A primeira ação recomendada é separar claramente os contratos de teste e produção. O executor deve ser executado contra um adaptador Bitcoin real somente em ambiente controlado, preferencialmente regtest ou testnet, antes de qualquer operação Mainnet.

A segunda ação, concluída nesta revisão, foi alinhar os quatro testes mobile aos contratos atuais. O projeto deve manter o prefixo de endereço documentado, exigir chaves privadas hexadecimais de 32 bytes na importação e preservar AES-256-GCM. A expectativa antiga de `pbkdf2-sha256-xor` não deve ser restaurada, pois pode representar uma regressão criptográfica.

A terceira ação é validar a infraestrutura operacional sem tocar em fundos: endpoint RPC, rede configurada, altura de bloco, peer count, relógio do sistema, persistência, backups, alertas e rotação de chaves. Esses checks devem produzir evidências anexáveis antes do go-live.

A quarta ação é executar um ciclo completo em regtest ou testnet com um depósito controlado, três relayers independentes, prova válida, prova adulterada, signer desconhecido, duplicata e reinício entre proof e mint. O resultado esperado deve ser armazenado como artefato de auditoria.

A quinta ação é manter a publicação de transações Mainnet como operação manual. O operador deve revisar o destinatário, valor, taxa, inputs, change output e hexadecimal assinado antes de qualquer broadcast. Nenhuma chave privada deve ser enviada ao agente ou armazenada em arquivos do repositório.

## 8. Limites desta revisão

A revisão não acessou nem descriptografou chaves privadas. A revisão não criou ou assinou uma transação Bitcoin Mainnet. A revisão não transmitiu uma transação para um explorador ou para um nó Bitcoin. A revisão não declarou confirmação on-chain.

Portanto, o resultado é uma avaliação de código e testes locais. A expressão “Mainnet validada” deve ser reservada para uma execução operacional com evidência de RPC, txid, confirmações e auditoria do payload assinado.

## Referências

[1]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/tree/main "Repositório b-AI-tcoin-AI-to-AI-"

[2]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/blob/main/native_processing/swap_service.py "NativeSwapService"

[3]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/blob/main/native_processing/bridge_handoff.py "SwapBridgeHandoff"

[4]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/blob/main/baitcoin_bridge/authorization.py "RelayerAuthorization"

[5]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/blob/main/baitcoin_bridge/manager.py "BridgeManager"

[6]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/blob/main/baitcoin_bridge/relayer.py "Relayer"

[7]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/blob/main/baitcoin_mainnet/config.py "Mainnet configuration"
