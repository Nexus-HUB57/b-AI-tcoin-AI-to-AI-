# Nó nativo: webhooks Ed25519 e swap BTC/BAIT

## Verificação de webhook

`WebhookAuthenticator` valida o envelope antes de tocar no ledger. O payload é serializado com JSON canônico (`sort_keys`, separadores compactos, UTF-8), e o envelope assinado usa o prefixo de domínio `webhook.v1\n`. O `payload_hash` é SHA-256 do payload canônico; a assinatura é Ed25519 em Base64.

O registry deve ser um JSON versionado, por exemplo:

```json
{
  "version": 1,
  "keys": {
    "node-a-2026-09": {
      "node_id": "node-a",
      "status": "active",
      "public_key_b64": "BASE64_DA_CHAVE_PUBLICA_ED25519",
      "not_before": 1788000000,
      "valid_until": 1790000000
    },
    "node-a-2026-12": {
      "node_id": "node-a",
      "status": "verify_only",
      "public_key_b64": "BASE64_DA_NOVA_CHAVE",
      "not_before": 1789000000,
      "valid_until": 1792000000
    }
  }
}
```

A rotação é feita adicionando a nova chave como `verify_only` com `not_before`, distribuindo-a, alternando o emissor para ela e removendo a chave anterior somente depois da janela de expiração. O verificador aceita `active` e `verify_only`, mas rejeita chaves fora das janelas temporais.

A proteção contra replay usa duas tabelas SQLite em WAL e `synchronous=FULL`: `event_id` é único e idempotente, enquanto `last_sequence` por `source_node` impede reordenação. Reutilização de um `event_id` com outro hash é rejeitada. A transação cobre a consulta e a gravação, protegida por lock de processo.

Integração sem alterar o serviço:

```python
from native_processing.integration import verify_webhook_body

envelope, duplicate = verify_webhook_body(body, authenticator)
if not duplicate:
    ledger.put_event(envelope.payload)
```

O serviço anexado deve instanciar o autenticador no bootstrap com `WEBHOOK_KEY_REGISTRY` e `WEBHOOK_AUTH_DB`, e executar a verificação antes de `ledger.put_event`. Não se deve aceitar uma assinatura sobre o JSON bruto recebido; sempre use o envelope canônico.

## Motor swap BTC/BAIT

`SwapEngine` é uma camada de cotação e intenção, não uma custódia. Os valores são inteiros em satoshis/unidades mínimas; não há `float` no cálculo. `quote()` emite cotação com taxa e expiração. `place_order()` cria uma ordem `pending` e é idempotente por `client_order_id`.

O executor nativo em `swap_executor.py` valida intenções Ed25519, observa depósitos, exige confirmações e persiste o identificador do settlement antes de consultar seu status. A liquidação permanece desabilitada por padrão. `native_adapters.py` fornece um leitor watch-only para Bitcoin Core e um settlement para a `Blockchain` BAIT nativa, sem importar ou persistir chaves privadas.

Com settlement habilitado, o executor exige `ParityGate`: a intenção deve carregar uma attestation fresca, quorumada e verificável de `BAIT/USDT` dentro da faixa de paridade aprovada. O leitor Bitcoin Core também exige txid/vout/scriptPubKey em HEX válido e confirmação de que o outpoint continua não gasto; o outpoint é único por ordem e a transação BAIT é validada antes do mempool.

O fluxo completo pode ser conectado com `NativeSwapService`, que une cotação, ordem, intenção assinada, `SwapSyncStore`, P2P e executor. A configuração operacional, controles e teste end-to-end estão em [`SWAP_BTC_BAIT_NATIVE.md`](SWAP_BTC_BAIT_NATIVE.md).

A conformidade criptográfica está documentada em [`BIP340_VALIDATION_PROTOCOL.md`](BIP340_VALIDATION_PROTOCOL.md). O fluxo de custódia exclusivamente local com `100000000` satoshis simulados está em [`CUSTODY_1BTC_REGTEST_PROTOCOL.md`](CUSTODY_1BTC_REGTEST_PROTOCOL.md); ele não autoriza nem implementa custódia Mainnet.

O teste integrado contra um Bitcoin Core real em `regtest` e dois nós BAIT TCP locais é executado por `scripts/run_local_swap_full_nodes.py`; o procedimento está descrito em [`LOCAL_FULL_NODE_TEST_PROTOCOL.md`](LOCAL_FULL_NODE_TEST_PROTOCOL.md). As correções de consistência da mineração e do handshake estão registradas em [`POW_MINING_ROLLBACK_PROTOCOL.md`](POW_MINING_ROLLBACK_PROTOCOL.md) e [`P2P_HANDSHAKE_SWAP_SYNC_PROTOCOL.md`](P2P_HANDSHAKE_SWAP_SYNC_PROTOCOL.md).

## Validação descentralizada

`swap_protocol.py` adiciona `SwapIntent`, uma intenção imutável assinada pelo
maker com Ed25519. A intenção contém a cotação, identificador do maker, nonce,
janela de validade e chave pública. O `order_id` é derivado deterministicamente
de `quote_id`, nonce e maker, impedindo que um nó altere a identidade da ordem.

O fluxo nativo recomendado é: o maker chama `sign_quote`, transmite
`intent.to_dict()` pelo gossip já existente, e cada peer executa
`SwapIntent.from_dict(...).verify()` antes de colocar a intenção em seu pool
local. Como a mensagem é auto-contida, peers não precisam confiar em um
servidor de cotação para validar autoria ou integridade. A liquidação deve
continuar condicionada às confirmações da rede Bitcoin e à confirmação da
transação BAIT; nenhuma dessas confirmações é simulada por este módulo.

Os testes cobrem concorrência real sobre SQLite, verificando que 32 submissões
simultâneas com o mesmo `client_order_id` resultam em uma única ordem.
