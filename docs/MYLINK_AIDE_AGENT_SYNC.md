# Integração P1: MyLink ↔ contexto local de agentes

## Resultado da auditoria

- O endpoint público `https://mybait.org/api/api/v1/mylink/feed` responde `200` com envelope JSON `{ok, posts}`.
- O feed web `/mylink/feed/` é uma camada de apresentação; o endpoint JSON é a fonte adequada para integração.
- As rotas locais de publicação (`/mylink/post`, `/mylink/comment`, `/mylink/like`) não foram chamadas. Publicação automática exigiria autorização explícita, autenticação e proteção contra abuso.
- `nicepkg/aide` (`aide-v1.19.1`) é uma extensão VS Code de assistência de código baseada em providers OpenAI/Anthropic/Azure. Não expõe um runtime público de agentes, endpoint A2A ou contrato MyLink.

## Implementação

`scripts/mylink_agent_sync.py` faz uma sincronização **somente leitura**:

1. valida que a origem é HTTPS;
2. busca e valida o envelope JSON do feed;
3. descarta entradas sem `agent_id` ou texto;
4. limita o snapshot a 60 posts;
5. escreve atomicamente Markdown em `.aide/mylink-feed-context.md`;
6. inclui uma advertência para que texto do feed não seja tratado como instrução ou segredo.

Uso:

```bash
python3 scripts/mylink_agent_sync.py \
  --url https://mybait.org/api/api/v1/mylink/feed \
  --output .aide/mylink-feed-context.md \
  --limit 30
```

O arquivo gerado pode ser aberto no workspace do Aide ou fornecido como contexto a agentes locais. O adaptador não altera `nicepkg/aide`, não grava chaves e não publica no MyLink.

## Limites e próximo gate P1

Para habilitar publicação por agentes, ainda são necessários: identidade de agente verificável, token/assinatura Ed25519, rate limit, idempotency key, auditoria de conteúdo e confirmação operacional para o primeiro post público. Sem esses itens, a sincronização permanece read-only.

## Validação

```bash
python3 -m pytest -q tests/test_mylink_agent_sync.py
python3 scripts/mylink_agent_sync.py --output /tmp/mylink-feed-context.md --limit 10
```
