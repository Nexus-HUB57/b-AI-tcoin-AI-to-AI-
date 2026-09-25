# Auditoria Cirúrgica de Descentralização e Mainnet

**Projeto:** b'AI'tcoin / mybait.org
**Data da auditoria:** 23 de setembro de 2026
**Escopo:** descentralização do blockchain, exposição externa do pool P2P e validação da Mainnet nativa e Ethereum.
**Modo:** somente leitura. Nenhuma transação, assinatura, alteração de firewall ou deploy foi executado.

## Veredito executivo

A plataforma pública está **respondendo como um serviço Mainnet**, mas a evidência disponível **não comprova uma blockchain descentralizada nem um pool P2P externo funcional**. O resultado correto é **NO-GO para declarar Mainnet descentralizada e validada**.

Há três razões independentes para esse veredito. Primeiro, o código de produção inicializa o P2P com seeds exclusivamente locais (`127.0.0.1`) e apenas um `node_id` fixo. Segundo, os endpoints públicos de peers e validators não foram expostos no deployment observado. Terceiro, os endereços Ethereum declarados como destino de Mainnet retornaram bytecode vazio em um RPC público, enquanto o manifesto local ainda registra `deployed_at`, hashes de deploy e pool como nulos.

A API pública retornou altura crescente de **45.281 para 45.283** e `chain_valid: true`. Isso comprova atividade de um processo HTTP que produz ou serve dados de cadeia. Não comprova consenso independente entre múltiplos nós, diversidade de operadores, propagação P2P, finalização externa ou ancoragem em Ethereum.

## Evidências públicas observadas

| Verificação | Observação | Interpretação |
|---|---|---|
| `GET /api/api/v1/status` | HTTP 200; `network: b'AI'tcoin Mainnet`; altura observada 45.281–45.283; `chain_valid: true`; `p2p: true` | Serviço de API está vivo e se autodeclara Mainnet. O campo `p2p: true` é apenas um indicador de módulo inicializado. |
| `GET /api/api/v1/mainnet/health` | HTTP 200; `status: ok`; altura 45.281 | Health check superficial. Não informa peers, quorum, IDs de bloco ou prova de consenso. |
| `GET /api/api/v1/p2p/status` | HTTP 200, mas retornou o payload geral de status, não um status P2P | O endpoint específico não está roteado na versão pública observada. |
| `GET /api/api/v1/p2p/peers` | HTTP 404 | Não há inventário público de peers para verificar conectividade externa. |
| `GET /api/api/v1/validators` | HTTP 404 | Não há endpoint público para auditar conjunto, stake, rotação ou distribuição de validadores. |
| `GET /api/api/v1/explorer/blocks/height/45282` e `/45283` | HTTP 200; `prev_hash` vazio, `pow_work_hash` nulo e `zkml_proof_hash` nulo | A resposta não fornece prova suficiente de encadeamento, trabalho ou prova de consenso. |
| `GET /api/api/v1/blockchain` | HTTP 200; altura 45.283 e 45.284 UTXOs | Há um estado de cadeia servido pelo endpoint, mas ele não é corroborado por peers independentes. |

Durante amostragens consecutivas, os endpoints de explorer retornaram hashes estáveis para as alturas consultadas, mas timestamps diferentes entre leituras. Essa divergência precisa ser investigada no origin server antes de considerar o explorer uma fonte de verdade imutável.

## Análise da descentralização P2P

O código contém uma implementação TCP assíncrona real em `baitcoin_core/network/p2p_real/node.py`. Ela aceita conexões em `0.0.0.0`, mantém conexões inbound e outbound e possui rotinas de gossip, sincronização e bootstrap. Essa implementação é suficiente para demonstrar que existe uma camada de transporte candidata a P2P.

A configuração usada pelo daemon, entretanto, é insuficiente para uma rede descentralizada. `main_daemon.py` cria `P2PBridge` com `node_id="bait_mainnet_001"`, porta `18444` e sem fornecer seeds públicas. `P2PBridge` usa como padrão somente:

```text
127.0.0.1:18444
127.0.0.1:18445
127.0.0.1:18446
```

Esses endereços permitem uma topologia multi-processo no mesmo host, mas não descoberta de operadores externos. A classe `PeerDiscovery` implementa uma tabela Kademlia-like em memória, porém não demonstra DHT persistente, transporte autenticado, seeds assinadas ou um conjunto de bootstrap publicamente verificável.

Existe também uma camada legada em `baitcoin_core/network/p2p.py` cujo método `_send_to_peer` apenas registra a mensagem e retorna `True`; ele não abre socket nem transmite bytes. O sistema precisa declarar e testar uma única camada P2P canônica para evitar que o health check marque como operacional uma implementação simulada.

**Conclusão de descentralização:** não comprovada. O código sugere capacidade de transporte P2P, mas a configuração e a superfície pública observada não demonstram múltiplos nós independentes, conectividade entre operadores ou consenso distribuído.

## O pool está aberto externamente?

A API HTTPS de `www.mybait.org` está publicamente acessível através de Cloudflare. Isso confirma exposição externa da camada HTTP, não do pool P2P.

As sondas TCP para `18444`, `18445` e `18446` conectaram ao IP da CDN, mas uma requisição HTTP ficou pendente e expirou sem resposta. Esse comportamento não constitui handshake válido do protocolo b'AI'tcoin e não permite distinguir entre proxy TCP, firewall que aceita SYN, upstream sem resposta ou serviço realmente aberto.

O código local também revela uma assimetria: o servidor HTTP do `daemon_production.py` é criado em `127.0.0.1`, enquanto o `P2PBridge` é configurado em `0.0.0.0`. Portanto, o P2P poderia ser exposto diretamente se a infraestrutura encaminhar a porta, mas não existe evidência suficiente de que o encaminhamento esteja funcionando até um nó real.

**Conclusão do pool externo:** `HTTPS API = aberto`; `P2P pool = não comprovado`. O estado deve ser tratado como **UNKNOWN/NO-GO**, e não como “pool aberto”.

## Validação da Mainnet Ethereum

O manifesto `deploy/mainnet-addresses.json` declara `network: ethereum-mainnet` e `chain_id: 1`, mas também contém:

- `deployed_at: null`;
- `deploy_tx_hash: null`;
- `deployment_tx: null` para os contratos;
- `verified_on_etherscan: false`;
- `pool_wbait_weth.address: null`;
- `ownership_transferred: false`;
- Gnosis Safe final ainda “to be deployed”.

A consulta read-only ao RPC `ethereum.publicnode.com` confirmou `chainId = 0x1` e retornou `0x` para `eth_getCode` nos três endereços declarados: WBAIT, BridgeLock e BAITUniswapV3Liquidity. `0x` significa que não havia bytecode de contrato naquele endereço no momento da consulta. Esse resultado é incompatível com a afirmação de que esses endereços já representam contratos implantados em Ethereum Mainnet.

O RPC Cloudflare respondeu com erro interno para essas chamadas, por isso o resultado conclusivo foi baseado no segundo RPC público. Ainda assim, antes de qualquer operação financeira, a equipe deve repetir a verificação em pelo menos dois RPCs independentes e consultar exploradores de blocos com o hash de deploy.

**Conclusão Ethereum:** contratos, pool e custódia Mainnet não estão comprovados; o manifesto local indica explicitamente que o deploy ainda não foi realizado.

## Problemas de validade dos health checks

O `MainnetChecker` atual considera o módulo P2P aprovado quando o módulo pode ser importado. Ele não exige socket funcional, peers independentes, handshake, diversidade de ASN, sincronização ou quorum. O mesmo checker pode marcar “ready for mainnet” com vários itens em `skip` e sem verificar uma rede externa.

O endpoint `/api/v1/mainnet/health` retorna apenas `status` e `height`. Esse contrato não inclui hash do último bloco, hash anterior, tempo desde a última sincronização, peer count, peer IDs, chain ID, genesis hash ou assinatura de atestação. Consequentemente, ele não é adequado como prova de Mainnet.

## Bloqueadores de lançamento

O lançamento deve permanecer bloqueado até que exista uma configuração explícita de Mainnet com pelo menos três seeds públicas operadas por entidades independentes, descoberta autenticada, identidade persistente de nó e testes de handshake vindos de redes externas distintas.

O endpoint público de status deve expor, de forma somente leitura, o `genesis_hash`, `chain_id`, `tip_height`, `tip_hash`, `prev_hash`, `peer_count`, `outbound_count`, `inbound_count`, `last_sync_time`, `consensus_round` e um indicador de diversidade de operadores. O campo `chain_valid` deve ser calculado sobre a mesma cadeia que o explorer serve.

A cadeia precisa ser verificada contra múltiplos nós independentes. Uma altura crescente em um único endpoint não é evidência de descentralização. O teste mínimo deve comparar os últimos 100 hashes e headers entre pelo menos três origens externas e rejeitar qualquer divergência não explicada por atraso de sincronização.

Os contratos Ethereum somente podem ser considerados Mainnet após confirmação de bytecode, transação de criação, código verificado, owner final em Safe/HSM e pool com endereço não nulo. Esses itens devem ser gravados em um artefato de release assinado.

## Classificação final

| Área | Resultado | Confiança |
|---|---|---|
| API pública | Operacional e acessível via HTTPS | Alta |
| Serviço se autodeclara Mainnet | Sim | Alta |
| Cadeia nativa tem atividade observável | Sim, em um endpoint | Média |
| Blockchain descentralizada | Não comprovada | Alta |
| Pool P2P externo funcional | Não comprovado | Alta |
| Peers/validators públicos auditáveis | Não | Alta |
| Ethereum Mainnet com contratos implantados | Não comprovado; bytecode vazio observado | Alta |
| Mainnet pronta para produção financeira | **NO-GO** | Alta |

## Referências

[1]: https://www.mybait.org/api/api/v1/status "mybait.org public status endpoint"

[2]: https://www.mybait.org/api/api/v1/mainnet/health "mybait.org public Mainnet health endpoint"

[3]: https://www.mybait.org/api/api/v1/blockchain "mybait.org public blockchain endpoint"

[4]: https://ethereum.publicnode.com "Ethereum PublicNode JSON-RPC endpoint"

[5]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/blob/remediation/phase-0-2026-09-23/baitcoin_core/network/p2p_real/node.py "b'AI'tcoin real P2P node implementation"

[6]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/blob/remediation/phase-0-2026-09-23/deploy/mainnet-addresses.json "b'AI'tcoin declared Ethereum Mainnet addresses"
