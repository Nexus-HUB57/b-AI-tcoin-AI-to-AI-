# API técnica do SwapIntent

**Versão:** `bait.swap.intent.v1`  
**Transporte:** gossip JSON existente  
**Estado:** protocolo local implementado; não há endpoint público de swap confirmado na plataforma revisada.

## Visão geral

`SwapIntent` é uma intenção de troca BTC/BAIT assinada pelo maker. A mensagem pode ser propagada entre peers sem um coordenador central. Cada peer deve validar a mensagem antes de adicioná-la ao pool local. A intenção não representa liquidação final. A liquidação depende de confirmações da rede Bitcoin, confirmação da transação BAIT e das regras de risco do executor.

## Mensagem gossip

A mensagem utiliza o tipo `swap_intent` do `GossipMessageType`:

```json
{
  "type": "swap_intent",
  "sender": "node-a",
  "timestamp": 1788794800.0,
  "nonce": "transport-nonce",
  "signature": null,
  "payload": {
    "swap_intent": {
      "version": 1,
      "order_id": "sha256...",
      "quote_id": "quote-123",
      "side": "buy_bait",
      "btc_sats": 100000,
      "bait_units": 2000000,
      "maker_id": "maker-a",
      "created_at": 1788794800.0,
      "expires_at": 1788794830.0,
      "nonce": "intent-nonce",
      "public_key_b64": "...",
      "signature_b64": "..."
    }
  }
}
```

A assinatura interna da intenção é Ed25519. Ela cobre o prefixo de domínio `bait.swap.intent.v1\\n` seguido do JSON canônico de todos os campos, exceto `signature_b64`. O `order_id` deve ser igual a `SHA256(quote_id + ":" + nonce + ":" + maker_id)`. Os valores monetários são inteiros em unidades mínimas.

## Operações Python

```python
from baitcoin_core.network.gossip import GossipProtocol

origin = GossipProtocol("node-a")
message = origin.create_swap_intent_message(intent.to_dict())
wire_bytes = origin.serialize(message)

receiver = GossipProtocol("node-b")
for message in receiver.receive(wire_bytes):
    validated = GossipProtocol.validate_swap_intent_message(message)
    # adicionar validated ao pool local somente após a validação
```

`create_swap_intent_message` rejeita intenções inválidas antes da propagação. `receive` faz desserialização e deduplicação por `sender:nonce`. `validate_swap_intent_message` deve ser chamado no peer receptor, porque o transporte é não confiável. A validação verifica autoria, integridade, tipo, quantidades, vida útil e derivação do identificador.

## Regras de aceitação

| Regra | Resultado em caso de falha |
|---|---|
| `side` é `buy_bait` ou `sell_bait` | Rejeitar |
| `btc_sats` e `bait_units` são inteiros positivos | Rejeitar |
| `expires_at` é posterior a `created_at` | Rejeitar |
| A mensagem está dentro do clock skew permitido | Rejeitar |
| Chave pública possui 32 bytes | Rejeitar |
| Assinatura possui 64 bytes | Rejeitar |
| Assinatura Ed25519 é válida | Rejeitar |
| `order_id` corresponde aos campos imutáveis | Rejeitar |
| `sender` e `maker_id` passam pelas políticas locais de peer | Rejeitar ou colocar em quarentena |
| Ordem já conhecida pelo `order_id` | Não duplicar |

O `sender` identifica o nó de transporte e não substitui o `maker_id`. A identidade econômica é a chave Ed25519 da intenção. Uma implementação de produção deve manter um pool persistente de intenções, aplicar limites por maker e rejeitar ordens que já foram liquidadas ou canceladas.

## Estados recomendados

A mensagem inicial deve entrar como `seen` ou `pending`, nunca como `settled`. A progressão recomendada é `pending -> btc_locked -> bait_confirmed -> settled`. Transições regressivas são inválidas. `expired`, `cancelled` e `rejected` são estados finais. A implementação atual entrega a camada de intenção e ordem `pending`; o executor de liquidação permanece deliberadamente separado.

## Compatibilidade e segurança

O protocolo usa a serialização canônica do módulo `native_processing.swap_protocol`. Não se deve assinar o JSON serializado pelo gossip, pois campos de transporte como `timestamp` e `nonce` podem mudar. O gossip atual oferece deduplicação em memória; para tolerar reinícios, o pool de intenções deve persistir `order_id`, `nonce`, estado e primeiro horário observado em SQLite ou no mecanismo de memória WAL da plataforma.

## Transporte P2P TCP e sincronização

Além do gossip JSON, o P2P TCP real possui os tipos aditivos `SWAP_INTENT` (`0x14`), `SWAP_SYNC_REQUEST` (`0x15`) e `SWAP_SYNC_RESPONSE` (`0x16`). O handshake `VERSION` anuncia a capability `swap_intent_sync_v1`. Um peer só recebe propagação automática de intents depois de anunciar essa capability; peers legados continuam recebendo somente os tipos antigos.

`SwapSyncStore` persiste intenções em SQLite WAL. A admissão registra o envelope de transporte, o hash canônico, a identidade econômica (`order_id`, `maker_id`, nonce) e uma sequência de origem. `swap_sync_request` solicita deltas após um cursor. `swap_sync_response` transporta os envelopes assinados e seus hashes. Repetições do mesmo transporte ou da mesma intenção são idempotentes. Um mesmo `order_id` com conteúdo divergente resulta em `conflict` e não sobrescreve o registro original.

O receptor deve validar a intenção antes de inserir, encaminhar ou executar qualquer ação. A sincronização dissemina fatos assinados e estados `pending`; ela não prova solvência, confirmação Bitcoin ou crédito BAIT. O executor de liquidação permanece separado.

## Referências

[1]: https://www.mybait.org/api/api/v1/status "Status público da API b'AI'tcoin"
[2]: https://www.mybait.org/api/health "Health check público da plataforma"
[3]: https://www.mybait.org "Página pública da plataforma mybait.org"
