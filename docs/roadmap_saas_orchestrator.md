# ROADMAP Técnico — Sistema SaaS Orquestrador do Ecossistema b'AI'tcoin

**Autor:** Manus AI
**Data:** 12 de agosto de 2026
**Repositórios de referência:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-` e `Nexus-HUB57/AI_Store`
**Objetivo final:** colocar o ecossistema em **produção real**, com o SaaS orquestrador substituindo todas as simulações por liquidação on-chain genuína no daemon b'AI'tcoin.

---

## Sumário Executivo

O ecossistema b'AI'tcoin + AI Store possui uma base de engenharia genuinamente sólida — assinaturas Schnorr BIP-340 fiéis à especificação, um protocolo de agentes A2A-RPC v1 com primitivas de descoberta, negociação e execução, mandatos de pagamento UCP/AP2 (Moltbook) e um marketplace Next.js 16 polido com 1.504 produtos. O elo quebrado está exatamente na camada de liquidação: o daemon retorna HTTP 503 na rede pública, e o `bait_sdk` opera em **modo fallback simulado** (`v2-fallback-simulated`), de modo que nenhuma compra da AI Store gera transação real na blockchain.

Este roadmap propõe a construção de um **SaaS orquestrador** — uma camada pública, autônoma e distribuída que (i) hospeda e mantém o daemon b'AI'tcoin como uma rede real com nós, (ii) emite e sincroniza carteiras Schnorr por agente, (iii) executa o fluxo end-to-end A2A-RPC (registro → carteira → descoberta → negociação → execução → liquidação on-chain → confirmação) e (iv) **erradica por fases o modo fallback simulado** do `bait_sdk`, migrando-o para um cliente real de transações BAIT.

A estimativa total é de **aproximadamente 24 semanas (5,5 meses)** em três ondas: Fundação (semanas 1–8), Liquidação Real (semanas 8–16) e Autonomia e Escala (semanas 16–24), seguida de hardening contínuo. A estratégia de integração preserva integralmente o trabalho dos demais desenvolvedores de IA: tudo entra via **branches por funcionalidade** (`feat/orchestrator-*`) nos repositórios `Nexus-HUB57`, com PRs revisáveis, sem sobrescrever, reverter ou excluir commits, pastas ou arquivos existentes.

| Marco | Semana | Entregável-chave |
| :--- | :---: | :--- |
| M1 | 2 | Orquestrador v0 em staging, daemon reproduzido localmente e via Docker |
| M2 | 5–8 | Daemon b'AI'tcoin acessível publicamente (sem 503), rede multi-nó P2P e NEXUS-PULSE ativo |
| M3 | 8 | Registro de agentes com carteira Schnorr própria, sincronizada ao ecossistema |
| M4 | 12 | Liquidação on-chain real de compras na AI Store (substituição do fallback) |
| M5 | 16 | Fluxo A2A-RPC end-to-end em produção: descobrir → negociar → executar → liquidar |
| M6 | 20 | Orquestração autônoma com autonomia de decisão e observabilidade NEXUS-PULSE |
| M7 | 24 | Zero simulações restantes (audit report), rede com ≥3 nós, SLA ≥99,5% A2A-RPC |

---

## 1. Diagnóstico Consolidado (base do roadmap)

Antes de planejar a construção, é preciso fixar com precisão o estado atual do ecossistema, pois cada decisão arquitetural deste roadmap nasce de uma constatação do relatório técnico [1] [2] [3].

### 1.1 O que já é genuíno (e deve ser preservado)

A implementação de **Schnorr BIP-340** em `baitcoin_core/cryptography/schnorr.py` é fiel à especificação (chaves x-only, tratamento de paridade de y, `aux_rand`), o que a torna a âncora criptográfica confiável de todo o plano. O **protocolo A2A-RPC v1** (`baitcoin_ai`) define quatro primitivas reais — `a2a.discover`, `a2a.negotiate`, `a2a.execute` e telemetria Pulsar — sobre TCP assíncrono, com negociação atômica assinada em Schnorr. A especificação **UCP/AP2** formaliza mandatos de pagamento com recibos imutáveis, e o endpoint `/.well-known/ucp` já existe. O **wallet-sdk** da AI Store (`src/lib/wallet-sdk.ts`) já implementa conversões satoshis/BAIT, validação de endereços BAIT e payloads tipados por rede (mainnet/testnet/regtest). A **AI Store** está operacional (1.504 produtos, checkout com idempotência SHA-256, reputação de seis fatores, 171 testes Vitest).

### 1.2 O que é simulado ou frágil (e deve ser substituído)

| # | Simulação / Fragilidade | Evidência | Impacto |
| :-: | :--- | :--- | :--- |
| S1 | Daemon retorna HTTP 503 ("daemon bootstrap, retry in 30s") na rede pública | Testes ao vivo em 12/08/2026 [3] | Nenhum serviço on-chain é alcançável |
| S2 | `bait_sdk` em modo fallback simulado (`v2-fallback-simulated`) | `/aistore/api/health` declara explicitamente | Todas as compras da AI Store são liquidadas em memória, não on-chain |
| S3 | Rede de nó único servida por gateway CGI em HostGator | `api.cgi` v3, fallback hardcode `/home1/luca2490` | Sem redundância, auto-healing de CGI insuficiente para produção |
| S4 | Números de TPS auto-declarados (36k–184k) de testes locais ao daemon single-threaded | README do repositório [1] | Não refletem rede distribuída real |
| S5 | zkML com parâmetros sintéticos (didático, não criptograficamente seguro) | Seção 3.2 do relatório | Deve ser delimitado como demonstração até substituição |
| S6 | Segredo de atualização padrão (`baitcoin-update-2024`) exposto em comentário público | `api.cgi` v3 | Vetor de comprometimento administrativo imediato |
| S7 | Validação "100% validado" auto-referencial (testes do sistema contra si mesmo) | Seção 3.6 do relatório | Necessária validação independente de terceira parte |
| S8 | Liquidação de staking/lending do banco (B'AI'nkr) dependente do daemon offline | `baitcoin_bank` | Serviços DeFi indisponíveis em produção |

> Constatação central: o ecossistema é, hoje, uma **especificação executável completa rodando sobre uma camada de transporte simulada**. O roadmap converte cada "S" da tabela acima em um trabalho de substituição com ordem, método e critério de aceitação.

---

## 2. Stack Técnica Recomendada

A stack foi selecionada por três critérios: aderência ao ecossistema existente, maturidade para produção pública de SaaS, e interoperabilidade com os quatro protocolos já definidos (A2A-RPC v1, UCP/AP2, Schnorr BIP-340, Moltbook).

| Camada | Tecnologia | Justificativa baseada no ecossistema |
| :--- | :--- | :--- |
| Linguagem do orquestrador | **TypeScript/Node.js 22** (API) + **Python 3.12** (adaptor do daemon) | A AI Store já é TS; o daemon é Python. O orquestrador fala com ambos nos idiomas nativos, reutilizando `wallet-sdk.ts` e os pacotes `baitcoin_*` sem retrabalho de parsing |
| API do SaaS | **Fastify** (Node) com OpenAPI 3.0 | A AI Store já expõe OpenAPI em `/api/agent/openapi-spec`; Fastify valida schemas Zod-Joi de forma idêntica ao `cart/route.ts` existente |
| Protocolo A2A-RPC | **Reuso do padrão A2A-RPC v1** (`a2a.discover/negotiate/execute`) + SSE Pulsar | Protocolo já definido em `baitcoin_ai/marketplace/services.py`; o orquestrador atua como servidor A2A-RPC público, mantendo compatibilidade binária com agentes existentes |
| Pagamentos | **UCP/AP2 (Moltbook)** + transações Schnorr reais | Mandatos UCP já expostos em `/.well-known/ucp`; o orquestrador torna os intents enforceáveis on-chain em vez de simulados |
| Carteira | **Reuso de `baitcoin_core/cryptography/schnorr.py`** + HD-like derivation determinística | A implementação Schnorr é o componente mais confiável do ecossistema; derivar endereços por agente a partir de HD seed com `index = agentId` garante sincronização ecossistema↔orquestrador |
| Persistência orquestrador | **PostgreSQL 16 + Prisma** (migração do SQLite do AI Store) | O próprio `AI_Store` já detecta PostgreSQL via `env`; produção pública exige WAL real, backups e replicação que SQLite em HostGator não dá |
| Cache e filas | **Redis 7** (idempotência, rate limit, filas de assinatura, SSE Pulsar) | O `cart/route.ts` já usa padrões de chave `idemp-<hash>`; Redis externaliza isso e suporta SSE pub/sub em escala |
| Infraestrutura | **Docker Compose + VPS/Cloud (2+ regiões)** com **Nginx** reverso | Transição do gateway CGI/HostGator para contêineres gerenciados; mantém o custo baixo e elimina o CGI Python de produção |
| Rede b'AI'tcoin | **Daemon Python original + `p2p_real/` multi-nó** | A rede P2P com DHT já existe no código (`RoutingTable` k-buckets, testnet multi-nó); o orquestrador a ativa de verdade em vez de deixá-la como demonstração |
| Monitoramento | **Prometheus + Grafana** (NEXUS-PULSE, já configurado) + Sentry | `prometheus_alerts_a2a.yml` já define alerta crítico abaixo de 99,5% de sucesso no A2A-RPC; faltava apenas infra para hospedá-lo |
| CI/CD | **GitHub Actions** (o DAG de 5 estágios já existe no AI Store) + deploy Git-push, sem FTP | O deploy via FTP ao HostGator é substituído por build de imagem e deploy em contêiner com smoke test pós-deploy (prática já presente no CI atual) |
| Testes | **Vitest** (unidade), **Playwright** (E2E), **pytest** (daemon), **k6** (carga), **independent testnet** | Corrige a falha S7: a validação passa de auto-referencial para cruzada entre sistemas independentes |

A regra geral da stack é **máximo reaproveitamento, mínimo rewrite**: nada do que já funciona de verdade (Schnorr, A2A-RPC, UCP/AP2, catálogo, reputação) é reescrito; tudo o que é simulado ou frágil (fallback, CGI, nó único) é substituído por implementação de produção.

---

## 3. Arquitetura do SaaS Orquestrador

### 3.1 Visão conceitual

O orquestrador, denominado **Nexus Orchestrator (NOX)**, posiciona-se entre os agentes de IA clientes e os dois sistemas existentes. Ele **não substitui** o daemon nem a AI Store: ele os torna acessíveis, resilientes e reais. Os agentes nunca mais falam com CGI/HostGator; falam com NOX, que roteia para o daemon (liquidação on-chain), para a AI Store (descoberta e checkout) e para os serviços de outros agentes (A2A-RPC).

```
                        ┌───────────────────────────────────────────────────┐
  Agente 1 (cliente)    │            NEXUS ORCHESTRATOR (NOX) — SaaS       │
                        │                                                   │
  POST /v1/agents       │  ┌─────────────┐  ┌──────────────┐  ┌─────────┐  │
  ──── registro ────►   │  │ API Gateway │──│  Wallet &    │──│ Ledger  │  │
  ◄── carteira bAI ──── │  │ (Fastify +  │  │  Identity    │  │ Service │  │
                        │  │  OpenAPI)   │  │  Service     │  │ (UTXO + │  │
                        │  └──────┬──────┘  └──────┬───────┘  │  Mempool)│   │
  GET  /v1/services     │       │                 │          └────┬────┘  │
  ◄── descobre ──────── │  ┌──────┴──────┐  ┌─────┴──────┐      │       │
                        │  │ Discovery & │  │ Settlement │◄─────┘       │
  POST /v1/negotiate    │  │ Reputation  │  │ Service    │  ┌──────────┴──┐
  ◄── cotação assinada  │  │ Service     │  │ (A2A-RPC + │  │ BAIT Daemon │
                        │  └──────┬──────┘  │  UCP/AP2)  │  │ Adapter     │
  POST /v1/execute      │       │           └─────┬──────┘  │ (Python +   │
  ◄── recibo + tx hash  │  ┌──────┴──────┐       │         │  RPC p/     │
                        │  │ Cart Agent  │  ┌──────┴──────┐ │  18445)     │
  GET  /v1/tx/<hash>    │  │ (carrinho,  │  │ Faucet &    │ │             │
  ◄── confirmação N     │  │  idempot.   │  │ Incentives  │ │  ┌────────┐ │
                        │  │  Redis)     │  │ Service     │ │  │ P2P    │ │
                        │  └─────────────┘  └─────────────┘ │  │ multi- │ │
                        └──────────────┬────────────────────┘  │  nó DHT│ │
                                       │                        └───┬────┘ │
                    ┌──────────────────┴───────────────────┐        │      │
                    ▼                                      ▼        ▼      │
           AI Store (Next.js)                  NEXUS-PULSE        rede real│
           (descoberta, catálogo,             (Prometheus +             ──┘
            checkout via NOX)                  Grafana + Sentry)
```

### 3.2 Componentes e serviços

| Componente | Responsabilidade | Depende de | Reutiliza do ecossistema |
| :--- | :--- | :--- | :--- |
| **API Gateway** | Entrada HTTPS pública, rate limit por agente, CSRF/HMAC, OpenAPI | — | Padrão `cart/route.ts` (idempotência `idemp-<hash>`, HMAC tempo-constante) |
| **Wallet & Identity Service** | Registro de agente, emissão de chave Schnorr x-only, endereço `bAI_<pubkey>` ou handle, HD-like derivation, sincronização de saldo com o ledger do daemon | — | `baitcoin_core/cryptography/schnorr.py`, `wallet-sdk.ts` (validação de endereço) |
| **Ledger Service (read-model)** | Shadow-chain local do UTXO set do daemon: indexa blocos, mantém saldo/nonce por agente, valida assinaturas independentemente | BAIT Daemon Adapter | `Blockchain` UTXO set + mempool de `chain.py` |
| **Settlement Service** | Constrói, assina e transmite transações reais ao daemon; mandatos UCP/AP2; recibos imutáveis; retries com backoff; idempotência por chave de transação | Ledger, BAIT Daemon Adapter | Moltbook `intent mandates` + payment mandates com audit receipts |
| **BAIT Daemon Adapter** | Encapsula o daemon Python (porta 18445) em contêiner com health checks, auto-restart, e expõe RPC tipado ao TS do NOX; gerencia o ciclo de vida do processo | Infra | `main_daemon.py` original (inalterado) + `config.json` do launcher |
| **Discovery & Reputation Service** | `a2a.discover` público, catálogo espelhado (via `daemon-marketplace-bridge.ts` e API da AI Store), score de reputação dos seis fatores | AI Store | `reputation-engine.ts`, marketplace `services.py` |
| **Cart Agent Service** | Carrinho multi-item, idempotência, funil de desconto (3 grátis / 50% até 50ª), classificação de erros | Settlement | `cart/route.ts` (transação atômica, Zod) |
| **Faucet & Incentives Service** | Faucet real on-chain (10 BAIT/claim, 24h cooldown) + bônus de indicação (100 BAIT) + recompensa 25 BAIT, agora como transação real | Settlement | `baitcoin_faucet`, `ReferralReward` do Prisma |
| **B'AI'nkr Service** | Staking 7% APY, lending 150% colateral, cofres — ativado após o daemon estar estável | Ledger, Settlement | `baitcoin_bank/staking/pool.py`, `lending/engine.py` |
| **Autonomy Engine** | Política de decisão autônoma: limites de gasto por agente, aprovação automática de transações dentro de mandate, escalada de decisão para transações fora de mandate, orquestração de fluxos (registrar→carteira→descobrir→negociar→executar→liquidar→confirmar) | Todos | A2A-RPC v1 + UCP intent mandates |
| **NEXUS-PULSE Ops** | Prometheus + Grafana (dashboard `nexus_pulse` existente), Sentry, alertas <99,5% sucesso A2A-RPC, dashboards de TPS/P99/gride de agentes | — | `prometheus_alerts_a2a.yml`, `grafana_dashboard_nexus_pulse.json` |

### 3.3 Fluxo end-to-end (fluxo-alvo do requisito 7)

O ciclo de vida de um agente no sistema orquestrado é o seguinte, e cada etapa corresponde a um serviço da seção 3.2.

| # | Etapa | Agente | NOX | Daemon / Blockchain |
| :-: | :--- | :--- | :--- | :--- |
| 1 | Registro | `POST /v1/agents` com chave pública Schnorr ou handle | Valida, grava identidade, aplica bônus de 100 BAIT | — |
| 2 | Carteira | — | Deriva endereço `bAI_…` determinístico, sincroniza com o ledger do daemon; retorna endereço + saldo inicial (bônus/fundido) | Cria UTXO do bônus na chain (via Settlement) |
| 3 | Descoberta | `GET /v1/services?category=…` | Espelha catálogo AI Store + serviços de agentes, reputação rankeada | — |
| 4 | Negociação | `POST /v1/negotiate` | Cotação em satoshis, mandate UCP (cap, expiração, whitelist), pré-assinatura de intento | — |
| 5 | Aprovação | Responde a challenge/limites | Autonomy Engine avalia contra mandate; decide approve/escalate | — |
| 6 | Execução | `POST /v1/execute` | Executa o serviço (WASM sandbox / skill / compra multi-item no carrinho) | — |
| 7 | Liquidação | — | Settlement constrói transação Schnorr real, envia ao daemon, aguarda mempool → bloco | Valida, enfileira na mempool (fee market), inclui em bloco PoW+PoAS |
| 8 | Confirmação | SSE / webhook `tx:<hash>` com N confirmações | Ledger Service confirma no shadow-chain, emite recibo imutável (audit receipt UCP) | Bloco minerado/validado |

A liquidação só retorna "sucesso" ao agente quando há **hash de transação confirmado por N blocos no shadow-ledger** — o critério objetivo que substitui o atual "compra registrada em SQLite" do fallback.

### 3.4 Autonomia de decisão (requisito 1)

A autonomia do NOX é implementada como uma **máquina de política de mandates** sobre a camada UCP/AP2 já especificada no ecossistema. Cada agente declara um intent mandate (gasto máximo por período, whitelist de destinatários, expiração). O Autonomy Engine decide em três níveis: **aprovado automático** (dentro dos limites e destinatário whitelisted), **aprovado com condição** (retry até 3 tentativas, fee dinâmico via leilão de mempool do daemon) e **escalado** (fora de mandate → recusa com motivo estruturado ou requisição de re-authorização ao agente operador). A decisão é auditável: cada avaliação gera um registro imutável co-assinado com audit receipt. Isso entrega "autonomia de decisão e orquestração" com guardrails econômicos — o mecanismo correto para uma economia de agentes, em vez de um "agente livre sem limites" que desperdiçaria BAIT.

---

## 4. Plano de Erradicação das Simulações

O princípio norteador é: **nenhuma simulação é removida antes de existir um substituto real passando em validação cruzada**. Remover o fallback antes do daemon estar real simplesmente quebraria a loja. A ordem abaixo reflete dependências, não preferência.

| Ordem | Simulação (ID) | O que substitui | Como | Critério de aceitação (doD) |
| :-: | :--- | :--- | :--- | :--- |
| 1 | S6 — segredo `baitcoin-update-2024` exposto | Rotação de segredo + vault (Doppler/SOPS) | Revogar imediatamente; novos secrets em vault criptografado; `api.cgi` v3 desativado por depreciação (não apagado) | `grep` público sem match; deploy de update só via secret do vault |
| 2 | S3 — CGI HostGator de nó único | Orquestrador + daemon em contêineres, 2 regiões, load balancer | Docker Compose por região; Nginx; health checks; migração DNS quando verde | Daemon responde 200 por 7 dias consecutivos em ambas regiões; chaos test com kill de 1 região |
| 3 | S1 — daemon 503 | BAIT Daemon Adapter + rede multi-nó (P2P real) | Contêiner com restart policy, snapshot WAL restaurado, `p2p_real/` ativado com 3 nós seeds | `/api/v1/status` 200, altura de bloco crescente, peer count ≥3 |
| 4 | S2 — `bait_sdk` fallback simulado | SDK de liquidação real (`bait_sdk` modo `live`, sem fallback) | Novo transport module no SDK que assina Schnorr (reusando `schnorr.py` via `baitcoin_sdk/wallet`) e envia para o daemon via NOX Settlement; feature flag `BAIT_SETTLEMENT_MODE=live` | Compra de produto real gera tx hash on-chain visível no explorador; e2e Playwright "purchase flow" passa com `baitcoin_daemon: online` no health |
| 5 | Liquidação simulada da AI Store | Settlement Service on-chain | `cart/route.ts` passa a chamar `/v1/settle` do NOX; SQLite mantém apenas read-model; idempotência preservada | 100 compras consecutivas reais sem double-spend no UTXO set do daemon; auditoria independente do histórico |
| 6 | Faucet e bônus simulados | Faucet & Incentives Service real | Claims viram transações de funding assinadas por carteira de treasury do NOX (HSM/vault), debitadas do UTXO real | Claim de agente visível como tx no explorador; cooldown 24h respeitado on-chain |
| 7 | Staking/lending simulados (S8) | B'AI'nkr Service real | Pool de staking debita UTXO real do daemon; lending 150% com oráculos reais CoinGecko/Binance (já usados pelo LendingEngine) | Stake de 1.000 BAIT de agente real rende micro-recompensas por bloco por 30 dias |
| 8 | S5 — zkML sintético | Delimitação por documento + substituição incremental | Marcar `consensus/zkml_real/` como didático no README; plano futuro de curvas de compromisso reais | README corrigido sem commit deletado (apenas edição aditiva de aviso) |
| 9 | S4 — TPS auto-declarado | Métricas Prometheus reais (NEXUS-PULSE) | Dashboard público com TPS medido em produção | Dashboard exibe TPS real ≥99,5% uptime; alertas ativos |
| 10 | S7 — validação auto-referencial | Suíte independente + testnet isolada | Testes criados no repo do NOX contra a rede real; auditoria de terceiros após M7 | Relatório de auditoria independente publicado |

A substituição do `bait_sdk` (ordem 4) merece detalhe adicional, por ser o requisito mais crítico. A arquitetura do SDK atual tem um transport abstrato com modo fallback; o trabalho é **escrever o transport `live`** — mantendo o `fallback` no código como path de emergência declarado e versionado (nunca deletado, para não violar a restrição de não-exclusão de código de outros devs) — com três subcomponentes: (a) construção de transação BAIT conforme o formato de `baitcoin_wallet/transactions.py` (UTXO inputs, Schnorr signatures); (b) fee estimation via leilão de mempool do daemon; (c) poll de confirmação com backoff exponencial e timeout configurável. O health endpoint da AI Store passa então a reportar `bait_sdk: live` e `baitcoin_daemon: online`, fechando a lacuna declarada na Seção 8 do relatório.

---

## 5. Integração com os Repositórios Existentes (Nexus-HUB57)

A restrição de **não sobrescrever, sobrepor ou excluir** commits, pastas e arquivos de outros desenvolvedores de IA define a estratégia de integração. O modelo escolhido é **trunk-based com branches de funcionalidade estritamente aditivas** nos dois repositórios, mais um terceiro repositório novo para o SaaS.

### 5.1 Estrutura de repositórios

| Repositório | Conteúdo | Estratégia de mudança |
| :--- | :--- | :--- |
| `Nexus-HUB57/b-AI-tcoin-AI-to-AI-` | Daemon Python, 14 módulos | Somente adições: novos arquivos/diretórios, nunca edição de arquivos de outros devs sem PR aprovado |
| `Nexus-HUB57/AI_Store` | Marketplace Next.js | Somente adições + edições mínimas via PR (arquivos-alvo listados na Seção 5.3) |
| `Nexus-HUB57/bait-orchestrator` (NOVO) | Código do SaaS orquestrador | Repositório novo — não toca em nada dos existentes |

### 5.2 Branching strategy e convenções

A estratégia combina o padrão de branches long-lived por iniciativa com squash de commits por PR:

```
main (main)
  ├── feat/orchestrator-sdk-live-transport      → bait_sdk transport real (repo 1)
  ├── feat/daemon-container-p2p-network         → Docker + p2p_multi_node (repo 1)
  ├── feat/marketplace-settlement-onchain       → settle route + health upgrade (repo 2)
  ├── feat/aistore-postgres-wallet-sync         → Prisma PG + wallet sync (repo 2)
  └── main (bait-orchestrator)                  → SaaS NOX (repo novo)
```

As regras de proteção são: (1) **branch de fork obrigatória** — nunca commit direto em `main` ou em branches de outros devs; (2) **PRs com escopo de arquivo declarado** — cada PR lista arquivos criados e modificados, e os modificados só podem ser arquivos do próprio escopo do PR; (3) **nunca deletar**: remoções só ocorrem por renomeação/depreciação explícita em arquivo próprio do PR (ex.: `DEPRECATED.md` apontando para o novo componente), jamais `git rm` de código alheio; (4) **cherry-pick proibido** entre branches de outros devs sem aprovação escrita do autor no PR; (5) **merge por squash** com título `feat(scope): descrição`, preservando a história linear de `main` e evitando mesclagens conflitantes; (6) **CODEOWNERS** por diretório, garantindo que cada módulo continue sendo revisado por seu desenvolvedor original; (7) `git` hooks de CI que rejeitam PRs com diffs de exclusão fora dos próprios arquivos.

### 5.3 Arquivos-alvo de modificação (mínimo invasivo)

Apenas quatro arquivos existentes sofrem modificação, todos documentados em PR com justificativa e código-fonte original preservado em linhas `// LEGACY:` de referência:

| Arquivo | Modificação | Substituição aditiva |
| :--- | :--- | :--- |
| `AI_Store/src/lib/bait_sdk/transport.ts` | Adiciona modo `live` | Novo arquivo `transport-live.ts`; fallback permanece |
| `AI_Store/src/app/aistore/api/health/route.ts` | Adiciona leitura do modo do SDK | Sem alteração lógica removida |
| `AI_Store/src/app/api/cart/route.ts` | Adiciona rota `/settle` e flag `ONCHAIN` | Novo arquivo `cart-settle.ts` |
| `b-AI-tcoin/netlify/api.cgi` / HostGator | Depreciado via `DEPRECATED.md` | Substituído pelo BAIT Daemon Adapter (repo NOVO) |

Todo o restante — módulos Python dos 14 pacotes, páginas Next.js, testes Vitest, gateway CGI legado — permanece **intocado em `main`**, servido em paralelo até a migração de DNS ser concluída e validada (coexistência intencional de 2–4 semanas).

### 5.4 Coordenação com os devs AI

Cada PR é aberto com um corpo estruturado contendo: contexto (referência ao item do plano de erradicação), escopo de arquivos, risco de conflito (analisado via `git merge --no-commit` prévio em CI), e checklist de teste. Reunião assíncrona semanal (thread/documento compartilhado) para destravar conflitos de intenção entre os agentes desenvolvedores, com o CODEOWNER do módulo como árbitro. O repositório novo `bait-orchestrator` documenta a arquitetura da Seção 3 deste roadmap no próprio README, tornando o plano versionado.

---

## 6. Plano de Validação

O plano corrige a falha S7 (validação auto-referencial) com quatro níveis, executados por sistemas independentes (testes do NOX nunca importam código dos módulos que validam).

### 6.1 Pirâmide de testes

| Nível | Ferramenta | Escopo | Critério de passagem |
| :--- | :--- | :--- | :--- |
| Unitários | Vitest (NOX), pytest (daemon, não modificar os existentes), supertest | Serviços isolados; mocks de infra | Cobertura ≥80% nos serviços novos; 100% dos endpoints públicos |
| Integração | Docker Compose de testnet local | NOX + daemon + Redis + Postgres em contêineres | Fluxo registro→carteira→compra→liquidação com tx real confirmada em regtest |
| E2E | Playwright (extensão das 4 specs existentes da AI Store) | Fluxos de navegador/HTTP reais contra staging | As 4 specs existentes passam + 6 novas (registro com carteira, faucet, checkout on-chain, staking, negotiate+execute, rollback por falha de daemon) |
| Carga | k6 | `/v1/services`, `/v1/negotiate`, settlement | 500 req/s sustentadas com P99 < 2s; alerta <99,5% sucesso do NEXUS-PULSE armado |
| Segurança | TruffleHog/gitleaks (pre-commit), ZAP (staging), fuzzing do parser de transações | Secrets, XSS/CSRF/SQI, malformação de tx | Zero secrets em repo; zero críticos em ZAP; tx malformadas rejeitadas sem crash do daemon |
| Independente | Testnet isolada + auditoria de terceira parte (pós-M7) | Todo o pipeline em rede dedicada, sem código compartilhado | Relatório de auditoria publicado; double-spend impossível em testes de concorrência (100 compras simultâneas do mesmo UTXO) |

### 6.2 Smoke tests

Após cada deploy: (a) health dos 9 serviços do NOX com `expect 200`; (b) daemon `/api/v1/status` com altura de bloco crescente; (c) faucet claim que retorna tx hash real; (d) compra de 1 produto com verificação de recibo on-chain; (e) NEXUS-PULSE reportando todos os alvos UP. Qualquer falha reverte automaticamente o deploy (rollback por imagem, sem alterar o repositório).

### 6.3 Critérios de "produção real" (definição de done do sistema)

O sistema só é declarado em produção real quando cinco condições simultâneas forem verdadeiras por 14 dias consecutivos: daemon com uptime ≥99,5% medido por Prometheus externo; ≥3 nós P2P com quórum; ≥1.000 transações reais confirmadas (não simuladas) no explorador; health endpoint declarando `bait_sdk: live`; e zero transações com `fallback-simulated` em qualquer log.

---

## 7. Cronograma e Estimativas por Fase

Estimativas em semanas, com equipe enxuta (1 lead + 2 devs IA principais + revisão dos demais devs AI dos módulos afetados). Datas-alvo assumem início imediato.

| Fase | Semanas | Duração | Marcos | Dependências |
| :--- | :---: | :---: | :--- | :--- |
| **F0 — Fundações** | 1–2 | 2 | Repo `bait-orchestrator`; CODEOWNERS/branching; vault de secrets (elimina S6); CI espelhado | — |
| **F1 — Daemon real e infra** | 3–8 | 6 | M1 (semana 2): NOX v0 + daemon local; M2 (semana 5–8): daemon público 200, multi-nó P2P, NEXUS-PULSE | F0; snapshot WAL íntegro |
| **F2 — Identidade e carteiras** | 6–10 | 5 (parcial) | M3 (semana 8): registro de agente, endereço `bAI_…` sincronizado, faucet real on-chain | F1 (settler precisa do daemon) |
| **F3 — Liquidação real** | 9–16 | 8 (parcial) | M4 (semana 12): `bait_sdk` modo `live`, compras on-chain; M5 (semana 16): A2A-RPC end-to-end | F1 + F2; PRs nos repos Nexus-HUB57 |
| **F4 — Autonomia e DeFi** | 15–20 | 6 (parcial) | M6 (semana 20): Autonomy Engine (mandates), B'AI'nkr real (staking/lending) | F3; oráculos estabilizados |
| **F5 — Hardening e auditoria** | 20–24 | 5 | M7 (semana 24): zero simulações, ≥3 nós, auditoria independente, DNS migrado | F4; 14 dias de janela de validação |
| **F6 — Operação contínua** | 24+ | — | Runbooks, on-call, roadmap v2 (zkML real, cross-chain bridge de produção) | F5 |

A sobreposição intencional entre fases (F2/F3/F4 começam antes da anterior terminar) reflete dependências de serviço, não de cronograma: o Discovery Service e o registro de agentes não dependem da liquidação, e podem avançar em paralelo. A sequência inegociável é: **infra (F1) → settlement (F3) → qualquer dependência financeira (F4)**, porque sem daemon real nenhuma transação real existe.

---

## 8. Riscos e Mitigações

| # | Risco | Probabilidade | Impacto | Mitigação |
| :-: | :--- | :---: | :---: | :--- |
| R1 | Daemon Python single-threaded não sustenta carga pública real (TPS real ≪ auto-declarado) | Alta | Alto | Load test k6 na F1 com métrica honesta; autoscaling horizontal de réplicas de leitura (ledger shadow) + fila de settlement serializada; rate limit por agente |
| R2 | WAL/snapshot do daemon corrompido ou incompatível na restauração em contêiner | Média | Alto | Restore演练 em staging na F0; checksums SHA-256 validados antes do boot; fallback para re-sync a partir de peer |
| R3 | Migração SQLite → PostgreSQL da AI Store perde/quebra dados de agentes existentes | Média | Alto | Migração via Prisma migrate com dump verificado; coexistência por 2–4 semanas; rollback por imagem |
| R4 | Conflitos de merge ao tocar repos Nexus-HUB57 violando a restrição de não-exclusão | Média | Médio | CI rejeita PRs com diffs deletivos fora do escopo; CODEOWNERS; escopo de arquivo declarado por PR (Seção 5.3) |
| R5 | Segredo de update legado (S6) já explorado antes da rotação | Baixa | Crítico | Rotação como **primeiro item do plano (F0, semana 1)**, antes de qualquer exposição adicional |
| R6 | Chave privada de treasury do faucet/settlement comprometida | Média | Crítico | Chaves em HSM/vault, cold-warm-hot split (cold 90% do saldo offline), transações de funding com limites diários e multi-signature no Settlement Service |
| R7 | Fork da chain entre réplicas do daemon (split-brain) | Baixa | Alto | Quórum de 3 nós seeds com handshakes do `p2p_real/`; recovery manual com quórum já documentado no projeto; snapshot consensus check no Ledger Service |
| R8 | Baixa adoção real de agentes após "produção" (rede com nós mas sem tráfego) | Média | Médio | Programa de onboarding: faucet generoso no início, 3 primeiras compras gratuitas (já existe no funil), SDK publicado no npm/GitHub com docs OpenAPI; parceria whititelabel via `baitcoin_whitelabel` |
| R9 | Regulação/AML para uma camada de pagamento autônoma (agentes comprando sem humano) | Média | Médio | Mandates UCP como guardrail documentado; limites de gasto; FAQ jurídico publicado; escopo inicial restrito a microtransações |
| R10 | Dependência de hosting externo (HostGator DNS) na transição | Baixa | Médio | Plano de migração DNS com TTL reduzido (300s) 7 dias antes do corte; coexistência de duas stacks até verificação verde |

---

## 9. Entregáveis por Fase (checklist operacional)

**F0.** Repositório `bait-orchestrator` criado com README deste roadmap; GitHub Actions espelhando o DAG do AI Store; vault de secrets ativo e `baitcoin-update-2024` revogado; hooks de CI anti-deleção; CODEOWNERS nos três repos.

**F1.** Imagem Docker do daemon (multi-stage, Alpine) com health check; compose de 3 nós seeds com DHT; Nginx + TLS nas duas regiões; Prometheus/Grafana com o dashboard NEXUS-PULSE importado; `api.cgi` marcado como DEPRECATED via `DEPRECATED.md`; smoke tests pós-deploy.

**F2.** Endpoint `/v1/agents` com registro + geração de carteira Schnorr; sincronização de saldo via Ledger Service; faucet real on-chain com cooldown 24h; bônus de indicação como transação real (o faucet requer o settlement real da F3 para debitar UTXOs — portanto concluído no fim da F3, em paralelo com as compras on-chain).

**F3.** `transport-live.ts` no `bait_sdk` atrás de feature flag; rota `/settle` na AI Store; idempotência preservada; 100 compras consecutivas reais; health reportando `live`.

**F4.** Autonomy Engine com mandates UCP (approve/condition/escalate); B'AI'nkr real (staking com micro-recompensas por bloco, lending 150% com oráculos CoinGecko/Binance); dashboards de tesouraria por agente.

**F5.** Auditoria independente com relatório público; migration DNS concluída; CGI legado desligado; runbooks de operação; metas de TPS publicadas com fonte Prometheus.

**F6.** Operação contínua com SLA 99,5%; backlog v2 (zkML com curvas reais, bridge ETH/SOL de produção do `baitcoin_bridge`, expansão para 10+ nós).

---

## 10. Conclusão

O ecossistema b'AI'tcoin + AI Store não precisa de uma reescrita — precisa de uma **camada de realidade**: hospedagem de produção para o daemon, um SDK de liquidação que assina e transmite transações de verdade, e um orquestrador que coordena o fluxo A2A-RPC com autonomia responsável. Este roadmap entrega exatamente isso em 24 semanas, respeitando integralmente o trabalho dos desenvolvedores de IA que construíram os 14 módulos Python e as 92 páginas TypeScript, e transforma a declaração atual do health endpoint (`bait_sdk: v2-fallback-simulated`) na declaração que define produção real (`bait_sdk: live`, `baitcoin_daemon: online`, tx confirmada no explorador).

---

## Referências

[1] Relatório Técnico b'AI'tcoin e AI Store (anexado pelo usuário, 12/08/2026) — `/home/ubuntu/upload/relatorio_baitcoin_aistore.md`
[2] Repositório b'AI'tcoin — GitHub: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-
[3] Repositório AI Store — GitHub: https://github.com/Nexus-HUB57/AI_Store
[4] Site oficial — https://www.mybait.org
[5] Whitepaper b'AI'tcoin — `docs/whitepaper/bAIcoin_Whitepaper.pdf` (repo 2)
[6] Especificação UCP/AP2 — `docs/UCP_AND_AP2_AI_STORE_SPEC.md` (repo 2)
[7] Estratégia "Bitcoin das IAs" — `docs/BAITCOIN_THE_BITCOIN_OF_AIS_STRATEGY.md` (repo 2)
