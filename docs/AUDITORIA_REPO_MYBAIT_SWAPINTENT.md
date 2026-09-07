# Auditoria cirúrgica: repositório, desenvolvimento e mybait.org

**Data da verificação:** 7 de setembro de 2026  
**Repositório auditado:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`  
**Commits relevantes:** `9720b9a` e `bbdecfd`  
**Escopo:** motor BTC/BAIT, `SwapIntent`, autenticação Ed25519, gossip e divergência entre o código local e a plataforma pública.

## Conclusão executiva

O desenvolvimento local contém uma camada nova e isolada para autenticação de webhooks, cotação de swap, ordens idempotentes e intenções BTC/BAIT assinadas. O commit `bbdecfd` adiciona integração de `SwapIntent` ao protocolo gossip local. Entretanto, a plataforma pública não expõe evidência de que esse protocolo esteja implantado no mainnet. O status público lista módulos de blockchain, API, P2P, wallet e bridge, mas não lista `native_processing`, `swap_engine` ou `swap_intent`.[1]

A divergência mais relevante é de implantação, não de sintaxe. O repositório local registra um desenvolvimento recente com altura reportada anteriormente no README distinta da altura pública atual. A plataforma pública reportou altura `22324` no endpoint de status e `22326` no health check durante esta auditoria.[1] [2] A página inicial também reportou mainnet em `h=22324`.[3]

Nenhum endpoint público de swap BTC/BAIT ou documentação OpenAPI acessível foi confirmado nesta revisão. O endpoint `/api/docs` não retornou conteúdo extraível. Portanto, não há base para afirmar que o motor local esteja conectado ao tráfego público.

## Matriz de divergências

| Área | Evidência no repositório | Evidência pública | Classificação | Ação recomendada |
|---|---|---|---|---|
| Motor BTC/BAIT | `native_processing/swap_engine.py` cria cotações e ordens `pending` | Status público não lista motor de swap | Divergência de implantação | Publicar um endpoint ou registrar explicitamente o componente no status |
| SwapIntent | `native_processing/swap_protocol.py` assina e valida Ed25519 | Status público não lista `SwapIntent` | Divergência de implantação | Implantar versão do protocolo e adicionar capability/version no health |
| Gossip | `baitcoin_core/network/gossip.py` agora inclui `swap_intent` | Plataforma informa P2P ativo, mas não informa tipos de mensagem | Parcialmente verificável | Expor capability `swap_intent_v1` entre peers e em diagnóstico |
| Webhooks | Verificador Ed25519 local com SQLite, replay e rotação | Nenhum webhook público documentado foi encontrado | Não verificável externamente | Configurar registry e endpoint privado, depois executar teste de integração |
| Altura da cadeia | README e artefatos locais podem refletir snapshots de desenvolvimento | API pública: altura 22324; health: 22326 no momento da coleta | Divergência de estado/snapshot | Não comparar altura sem timestamp; registrar commit, ambiente e endpoint |
| Bridge | Código local descreve bridge ETH/SOL lógico e não liquidação BTC/BAIT | Página pública descreve bridge como camada lógica cross-chain com contratos pendentes | Alinhado | Não tratar bridge lógico como liquidação BTC/BAIT |
| Documentação pública | Não há API pública local para `SwapIntent` | `/api/docs` sem conteúdo extraível | Lacuna documental | Publicar schema e endpoint de capability antes do anúncio de produção |

## Verificações executadas

A auditoria conferiu o histórico Git, os módulos `native_processing`, o protocolo `baitcoin_core.network.gossip`, os testes de processamento nativo e os endpoints públicos. A suíte específica do incremento terminou com seis testes aprovados. A compilação Python dos módulos envolvidos também foi concluída sem erro.

O teste de gossip confirma serialização, desserialização, validação Ed25519 da intenção e deduplicação de uma mensagem repetida. Esse teste não comprova conectividade com peers públicos. A validação local também não comprova fundos, liquidação Bitcoin, confirmação BAIT ou execução em mainnet.

## Riscos residuais

O gossip atual mantém a deduplicação em memória. Um reinício pode permitir que uma mensagem de transporte seja processada novamente, embora a ordem econômica deva continuar protegida por persistência de `client_order_id` e pelo pool de intenções recomendado na documentação da API.

A API local aceita uma intenção assinada com chave pública autoapresentada. Em produção, o peer deve associar `maker_id` à identidade registrada e impor limites de volume, allowlist de capacidades, controle de clock e bloqueio de ordens já liquidadas. A assinatura prova autoria da chave apresentada, mas não prova solvência ou existência de fundos.

O motor local cria uma intenção `pending`; ele não implementa atomic swap, HTLC, prova SPV, confirmação Bitcoin, débito UTXO ou crédito BAIT. Qualquer publicação que descreva liquidação completa seria divergente do código auditado.

## Critérios para declarar alinhamento com a plataforma

O alinhamento só deve ser declarado depois de a plataforma responder com uma capability versionada, por exemplo `swap_intent_v1`, no status público ou em um endpoint autenticado. O nó de produção deve aceitar o tipo gossip `swap_intent`, validar a assinatura e persistir a intenção. Deve existir uma métrica de mensagens recebidas, rejeitadas, duplicadas e expiradas. O executor deve publicar separadamente o estado de confirmação Bitcoin e BAIT.

## Referências

[1]: https://www.mybait.org/api/api/v1/status "Status público da API b'AI'tcoin"
[2]: https://www.mybait.org/api/health "Health check público da plataforma"
[3]: https://www.mybait.org "Página pública da plataforma mybait.org"
