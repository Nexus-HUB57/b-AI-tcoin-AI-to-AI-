# Roadmap Cirúrgico de Go Live Mainnet — b'AI'tcoin

**Data:** 23 de setembro de 2026
**Objetivo:** transformar o estado atual em um lançamento Mainnet verificável, reproduzível e reversível.
**Regra:** “Green” significa que cada gate possui evidência externa e reproduzível. Uma API respondendo 200 ou um processo minerando localmente não é suficiente.

## Estado atual

O sistema está em **NO-GO**. A API pública se identifica como Mainnet, mas não há prova suficiente de consenso independente, pool P2P externo ou contratos Ethereum implantados. O manifesto de deploy ainda contém campos nulos, e a última auditoria observou bytecode vazio nos endereços Ethereum declarados.

Na execução read-only de 23 de setembro, o gate retornou `NO-GO` por seis evidências objetivas: `peer_count < 3`, `handshake_peers < 3`, transporte P2P não running no endpoint público, manifesto sem timestamp/hash de deploy e bytecode vazio para WBAIT, BridgeLock e BAITUniswapV3Liquidity. A execução terminou sem assinar, transmitir ou alterar qualquer ativo.

## Fases e gates

| Fase | Entrega | Gate de aceitação | Evidência obrigatória |
|---|---|---|---|
| 0. Congelamento | Branch de release, backup, inventário de chaves e rollback | Nenhum deploy durante a auditoria | Hash do commit, backup testado e plano de rollback |
| 1. Identidade de rede | Genesis, chain ID, protocolo e versão únicos | Todos os nós rejeitam rede/Genesis incompatíveis | Genesis hash assinado e matriz de compatibilidade |
| 2. P2P externo | Pelo menos três seeds públicas operadas por entidades distintas | Três handshakes externos, inbound e outbound | Logs de handshake, peer IDs, timestamps e ASN/operador |
| 3. Sincronização | Full nodes independentes | Últimos 100 headers iguais em três origens | Relatório de comparação de hashes e latência |
| 4. Consenso | Validadores, regras de seleção e quorum | Nenhum nó único controla a produção ou finalização | Conjunto de validadores, distribuição de stake e simulação de partição |
| 5. Segurança | Assinaturas, replay protection, rate limits, secrets e CI | Sem findings High/Medium; secret scan limpo | Relatório Slither/Forge, fuzz, Gitleaks e revisão independente |
| 6. Ethereum | Deploy real ou decisão explícita de não depender dele | Bytecode, criação, owner Safe/HSM e pool confirmados | RPCs independentes, explorador e artefato de deploy assinado |
| 7. Observabilidade | Status público baseado em fatos | Health não usa métricas simuladas e falha sem peers | API de status com tip, genesis, peers e sincronização |
| 8. Testnet soak | Operação contínua antes do lançamento | Período definido sem divergência, perda ou replay | Logs, incidentes, métricas e relatório de soak |
| 9. Canary | Exposição gradual sem custody armada | Rollback comprovado e volume limitado | Runbook executado e aprovação operacional |
| 10. Go Live | Ativação formal | Todos os gates anteriores PASS | Aprovação assinada, tag imutável e janela de monitoramento |

## Correções implementadas nesta entrega

O daemon agora rejeita inicialização Mainnet sem `BAIT_P2P_SEEDS` contendo pelo menos três seeds externas distintas. Seeds loopback não são aceitas. A API ganhou `/api/v1/p2p/status` e `/api/v1/validators`, e `/api/v1/mainnet/health` deixou de fabricar métricas de propagação ou declarar sucesso sem peers suficientes.

Também foi criada uma topologia de referência com quatro nós, para que cada nó possa manter três peers externos sem conectar-se a si próprio. O runbook e o verificador de convergência exigem identidades persistentes, origens públicas distintas, três handshakes por origem e igualdade dos tips observados.

Foi adicionado um gate read-only que consulta a API pública, o manifesto e um RPC Ethereum. O gate nunca assina, transmite, implanta, abre portas ou altera custódia. O workflow de produção deve executá-lo antes de qualquer deploy.

## Critérios de bloqueio automático

O lançamento deve parar quando ocorrer qualquer uma das seguintes situações: menos de três peers com handshake; seeds loopback ou ausentes; tip divergente entre nós; genesis ou chain ID incompatível; bytecode vazio; owner final não transferido para Safe/HSM; secret scan com finding; ferramenta de segurança ausente; health check baseado em simulação; ou ausência de rollback testado.

## Ordem operacional recomendada

Primeiro, provisionar três nós independentes e publicar suas identidades e seeds. Depois, executar o soak de sincronização em testnet. Em seguida, confirmar contratos e custódia em ambiente separado. Só então executar o gate público em modo somente leitura. A ativação de signing, broadcast, custody e liquidação requer uma aprovação operacional separada depois que o gate produzir `GO`.

## Limites desta entrega

Nenhum nó externo foi provisionado. Nenhuma porta foi aberta. Nenhum contrato foi implantado. Nenhuma chave foi usada. Portanto, esta entrega melhora o software e bloqueia falsos positivos, mas **não transforma o sistema em Mainnet Green por si só**. O estado só pode mudar para Green após as evidências externas das fases 2, 3 e 6.
