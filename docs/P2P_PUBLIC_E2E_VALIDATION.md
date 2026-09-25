# Validação E2E do Pool P2P Público

**Data da validação:** 24 de setembro de 2026

## Resultado local

O harness `scripts/run_public_pool_e2e.py --nodes 4` retornou `GO` em modo `local-transport-only`. Os quatro nós foram iniciados em portas efêmeras, cada nó manteve três peers, cada nó concluiu três handshakes e um bloco sintético foi propagado para três destinatários.

A suíte direcionada passou com **65 testes** incluindo o contrato HTTP da API, o harness de quatro nós, o transporte TCP de swap e a validação E2E completa.

## Resultado público

As origens `https://www.mybait.org` e `https://mybait.org` responderam HTTP 200 para `/api/api/v1/status`, `/api/api/v1/p2p/status` e `/api/api/v1/mainnet/health`. Porém, `/api/api/v1/p2p/status` retornou somente as chaves do status geral da cadeia. Não foram retornados `running`, `peer_count`, `handshake_peers`, `listen_port`, `configured_seeds` ou `peers`.

O readiness gate público permanece `NO-GO` por falta de evidência de transporte P2P. Isso não é considerado uma falha do handler local: a implementação atual de `baitcoin_api/server.py` chama `get_public_status()` e o novo teste HTTP confirma que a rota retorna o payload transport-only correto quando executada com o daemon atualizado.

## Causa operacional

O workflow `deploy-mybait.yml` publica somente arquivos frontend. O backend é atualizado pelo CGI `netlify/api.cgi`, que baixa o código da branch `main` por meio de uma ação administrativa protegida e reinicia o daemon. Portanto, alterações em uma branch de PR não atualizam o daemon público automaticamente.

## Próximo passo de produção

Depois da revisão e merge do código, o operador autorizado deve executar o procedimento administrativo de atualização do backend, reiniciar o daemon e repetir:

1. `curl https://www.mybait.org/api/api/v1/p2p/status`;
2. conferir `running=true`, `peer_count >= 3` e `handshake_peers >= 3`;
3. executar `scripts/verify_public_pool.py` com três origens independentes;
4. executar o readiness gate completo.

Nenhum segredo, chave, assinatura, broadcast, custody, DNS, firewall ou servidor foi alterado durante esta validação.
