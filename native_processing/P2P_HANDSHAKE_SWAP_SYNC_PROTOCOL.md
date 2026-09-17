# Protocolo técnico — Handshake P2P e sincronização de swap

## 1. Objetivo

Este protocolo documenta a correção do handshake inbound do P2P BAIT para que um full node que entra posteriormente na rede possa receber e reconstruir intenções de swap BTC/BAIT já conhecidas por um peer.

A mesma conexão TCP deve continuar servindo para handshake, sync de cadeia, gossip de transações e sincronização de intents assinadas, sem confiar na ordem em que os nós foram inicializados.

## 2. Falha anterior

A conexão inbound era registrada usando o endpoint TCP remoto como identidade provisória. O fluxo de handshake não disparava de forma consistente a sincronização de swap depois que o `VERSION/VERACK` era concluído. Como consequência, um nó late-join podia manter uma conexão TCP viva e ainda assim não receber as ordens já armazenadas no peer.

A correção preserva o endpoint para roteamento da conexão, mas usa a identidade anunciada na mensagem `VERSION` para construir a requisição de sincronização. O mecanismo também funciona quando o peer remoto anuncia altura zero ou quando a lista inicial de seeds está vazia.

## 3. Sequência corrigida

### Nó iniciador

1. Abre TCP para o peer.
2. Registra a conexão como outbound.
3. Envia `VERSION` com `node_id`, altura, agente e capabilities.
4. Recebe `VERACK`.
5. Mantém o canal pronto para `SWAP_SYNC_RESPONSE`, `SWAP_INTENT`, `INV`, `TX` e `BLOCK`.

### Nó receptor inbound

1. Aceita TCP e registra endpoint provisório.
2. Envia seu `VERSION` imediatamente.
3. Recebe `VERSION` do iniciador.
4. Registra a versão, a altura e as capabilities anunciadas.
5. Envia `VERACK`.
6. Se a capability de swap estiver presente e existir `SwapSyncStore`, envia `SWAP_SYNC_REQUEST` com a identidade anunciada do peer e sequência inicial.
7. Aceita a resposta em lotes, valida cada `SwapIntent`, deduplica por `order_id` e atualiza o maior `origin_seq` observado.

## 4. Regras de identidade e replay

- `node_id` anunciado no `VERSION` é usado para a correlação lógica de sync.
- O endpoint `host:port` continua sendo usado somente para o mapa de transporte.
- A intenção é validada com assinatura Ed25519 antes de entrar no store.
- `order_id`, digest canônico e sequência de origem impedem conflito ou replay.
- Mensagens inválidas não derrubam o loop principal do peer.
- Um late-join pode requisitar novamente a partir de uma sequência conhecida sem duplicar ordens.

## 5. Gossip de transações BAIT

Após a transação BAIT entrar no mempool local, `BaitBlockchainSettlement` pode receber um `p2p_node` opcional e chamar `broadcast_tx(tx.to_dict())`. A propagação é best-effort:

- a confirmação local não depende do peer;
- falha de gossip é registrada, mas não desfaz a entrada local no mempool;
- o `tx_id` é usado para deduplicação pelo protocolo P2P;
- o settlement só chega a `settled` quando a blockchain local observa a transação em um bloco.

## 6. Máquina de estados de sincronização

| Evento | Ação do receptor |
|---|---|
| `VERSION` válido | Registrar peer, altura e capabilities |
| `VERACK` | Marcar handshake como concluído |
| `SWAP_SYNC_REQUEST` | Consultar intents após a sequência solicitada |
| `SWAP_SYNC_RESPONSE` | Validar, deduplicar e persistir intents |
| `SWAP_INTENT` | Validar assinatura, identidade e ordem; persistir se nova |
| `TX` | Registrar txid conhecido, notificar callback e retransmitir |
| desconexão | Liberar transporte; manter store persistente para retomada |

## 7. Testes de aceitação

O teste `tests/test_p2p_swap_tcp_e2e.py` cria dois nós em portas efêmeras, com `seeds=[]`, inicia o nó A, inicia o nó B, conecta B ao A e verifica que uma intenção previamente armazenada em A aparece no `SwapSyncStore` de B.

O harness `scripts/run_local_swap_full_nodes.py` adiciona a verificação operacional de uma transação BAIT: settlement no nó A, gossip para o nó B e confirmação após mineração local.

Critérios de aceitação:

1. handshake TCP conclui sem seed externo;
2. late-join recebe a intenção assinada;
3. tx BAIT é retransmitida quando há peer conectado;
4. deduplicação mantém um único registro por txid/ordem;
5. uma falha temporária de gossip não cancela o settlement local.

## 8. Limites operacionais

O P2P local não substitui autenticação de transporte, rate limiting, persistência de peers ou política de banimento de uma rede pública. Antes de Mainnet, devem ser definidos:

- allowlist/descoberta de peers;
- limites por IP e tamanho de mensagem;
- autenticação ou identidade criptográfica de transporte;
- métricas de handshake e sync;
- recuperação após restart;
- política de reorg e confirmação de transações recebidas.
