# Runbook de provisionamento de peers públicos

## Objetivo

Este runbook descreve como formar uma testnet pública com quatro full nodes operados por pelo menos três entidades independentes. Ele reduz o risco operacional do status `NO-GO`, mas não autoriza mineração econômica na Mainnet. A promoção para Mainnet permanece condicionada aos gates de consenso, auditoria, bytecode e segurança de chaves.

## Critérios de entrada

O operador deve usar uma revisão imutável do repositório e uma rede explícita `baitcoin-testnet`. Cada host precisa ter um endereço público estável, relógio sincronizado, firewall configurado e acesso administrativo separado da porta P2P. Nenhuma chave privada deve ser armazenada no repositório, no manifesto ou nos logs.

O manifesto deve registrar quatro nós, identidades P2P diferentes, pelo menos três operadores, provedores ou regiões distintos quando possível, portas P2P únicas e APIs HTTPS públicas. O arquivo de exemplo é [`config/public_peers.testnet.example.json`](../config/public_peers.testnet.example.json). Ele contém placeholders intencionais e não deve ser usado como configuração de produção.

## Preparação de cada host

1. Criar um usuário de serviço sem privilégios administrativos.
2. Instalar exatamente o artefato correspondente ao SHA aprovado.
3. Gerar uma identidade P2P persistente e armazená-la fora do Git.
4. Configurar NTP, limites de conexão, rotação de logs e reinício automático.
5. Permitir a porta TCP P2P somente para tráfego necessário e manter SSH restrito.
6. Manter a API e a administração fora da porta P2P.
7. Configurar seeds externos; nunca usar `127.0.0.1` como seed de Mainnet.

O processo não deve iniciar com flags permissivas. A rede deve permanecer `baitcoin-testnet` até os gates da testnet pública serem aprovados.

## Validação do manifesto

Copie o manifesto de exemplo para um arquivo privado de implantação, substitua todos os placeholders por valores verificados e execute:

```bash
python3 scripts/validate_public_peer_manifest.py config/public_peers.testnet.json
```

O validador não faz chamadas de rede e não lê segredos. Ele bloqueia placeholders, IDs duplicados, endpoints P2P duplicados, APIs sem HTTPS, número insuficiente de operadores e qualquer rede diferente de `baitcoin-testnet`.

## Inicialização e conectividade

O operador A inicia o primeiro seed. Os operadores B, C e D configuram os endpoints A e dos demais nós disponíveis. Após a inicialização, cada nó deve completar pelo menos três handshakes e anunciar o mesmo genesis da testnet. Os operadores devem guardar o SHA do binário, o `node_id`, o endpoint, o timestamp de início e o resultado do handshake.

A verificação pública deve ser executada contra quatro origens independentes:

```bash
python3 scripts/verify_public_pool.py \
  --api https://node-a.example.org/api \
  --api https://node-b.example.org/api \
  --api https://node-c.example.org/api \
  --api https://node-d.example.org/api \
  --min-peers 3
```

O resultado somente é `GO` quando todos os nós estão ativos, têm pelo menos três handshakes, informam `chain_valid: true` e convergem para a mesma altura. Esse resultado comprova transporte e convergência observável; não substitui a validação de consenso.

## Exercícios obrigatórios

A equipe deve reiniciar cada nó individualmente, retirar o seed, desligar um nó, simular uma partição entre dois grupos e restaurar a conectividade. Após cada exercício, os nós devem reconectar e convergir sem aceitar peers com `network_magic`, genesis ou versão incompatíveis.

Também deve ser verificada a ausência de segredos nos logs e a separação entre identidade P2P, payout, credencial do pool e chave de deploy. Qualquer divergência de tip, handshake ou genesis deve manter o status `NO-GO`.

## Critério de promoção

A testnet pública pode ser marcada como concluída somente quando quatro nós de pelo menos três operadores independentes permanecerem estáveis durante o período de soak definido pelo conselho técnico. A promoção posterior exige, adicionalmente, protocolo de trabalho externo, submissão de blocos para pelo menos dois full nodes, validação determinística em cada nó, seleção formal de cadeia, auditoria independente e plano de rollback.

## Dependências ainda bloqueadoras

Este runbook não cria hosts, não abre firewalls, não registra DNS e não executa deploy externo. Para a execução real, são necessários quatro endpoints autorizados, os operadores responsáveis, o SHA da testnet, o genesis aprovado e a porta P2P oficial. Sem esses dados, qualquer tentativa de provisionamento seria especulativa e não demonstraria independência.

## Referências

[1]: ../docs/EXTERNAL_P2P_MINING_ROADMAP_BLUEPRINT_HANDBOOK.md "Roadmap e handbook de mineração P2P externa"
[2]: ../scripts/verify_public_pool.py "Verificador de status público e handshakes"
[3]: ../baitcoin_core/network/p2p_real/node.py "Implementação do nó P2P asyncio"
