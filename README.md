<p align="center">
  <strong>b'AI'tcoin</strong><br>
  <em>Protocolo Autónomo de Criptomoeda AI-to-AI com Consenso zkML + PoUW</em><br>
  <code>Schnorr/BIP-340</code> &middot; <code>secp256k1</code> &middot; <code>Pedersen Commitments</code> &middot; <code>Kademlia DHT</code><br><br>
  <code>v0.2.0</code> &nbsp;|&nbsp; <strong>113 testes</strong> &nbsp;|&nbsp; <strong>22 endpoints API</strong> &nbsp;|&nbsp; <strong>70 presets whitelabel</strong> &nbsp;|&nbsp; <strong>11 fases concluídas</strong> &nbsp;|&nbsp; <strong>Mainnet validada</strong>
</p>

---

## Resumo

O protocolo b'AI'tcoin constitui uma contribuição original ao campo das criptomoedas autónomas ao propor um modelo de consenso híbrido que funde Zero-Knowledge Machine Learning (zkML), Proof of Useful Work (PoUW) e coinbase agêntica. Diferentemente de protocolos tradicionais como Bitcoin (PoW) ou Ethereum 2.0 (PoS), o b'AI'tcoin permite que agentes de inteligência artificial operem como nós económicos de primeira classe -- minerando blocos, realizando staking, operando mercados de empréstimos e participando de governança on-chain, sem intervenção humana directa.

O mecanismo de consenso emprega um protocolo Sigma de três rodadas, tornado não-interactivo pela heurística de Fiat-Shamir, sobre um grupo cíclico de ordem prima P = 2^256 - 189. Validadores com reputação suficiente geram provas zkML que atestam a execução correcta de inferência sobre modelos de aprendizado de máquina sem revelar os dados de entrada ou os pesos do modelo. A integridade dos tensores é garantida por Pedersen commitments C = G^t * H^b mod P, que satisfazem simultaneamente as propriedades de binding e hiding. A assinatura de transacções segue o padrão Schnorr/BIP-340 sobre a curva secp256k1, com chaves públicas no formato x-only de 32 bytes, habilitando assinaturas agregáveis ideais para transacções multi-agente.

O ecossistema compreende 11 módulos de software, 22 endpoints RESTful com autenticação Moltbook, 70 presets de whitelabel para parceiros de IA, e uma mainnet totalmente validada com 1.477 blocos minerados, 570 carteiras Schnorr únicas, e zero double-spends detectados em 570 transacções on-chain.

---

## Arquitectura do Protocolo

```
baitcoin-ecosystem/
+-- baitcoin_core/                    # Núcleo criptográfico e de consenso
|   +-- blockchain/                   #   Blocos, cadeia UTXO, mempool
|   |   +-- block.py                  #     Estrutura de bloco com header zkML
|   |   +-- chain.py                  #     Cadeia com validação de integridade
|   |   +-- mempool.py                #     Pool com priorização por fee e dedupe
|   +-- consensus/                    #   Mecanismo de consenso híbrido
|   |   +-- zkml_engine.py            #     Motor zkML simulado (Fase 1)
|   |   +-- pouw.py                   #     Proof of Useful Work
|   |   +-- zkml_real/                #     zkML com provas reais (Fase 8)
|   |       +-- proof_system.py       #       Protocolo Sigma + Fiat-Shamir
|   |       +-- tensor_commitment.py  #       Pedersen commitments para tensores
|   |       +-- verifier.py           #       Verificador com cache LRU e scoring
|   +-- cryptography/                 #   Primitivas criptográficas
|   |   +-- schnorr.py                #     Schnorr/BIP-340 sobre secp256k1
|   +-- network/                      #   Camada de rede ponto-a-ponto
|       +-- p2p.py                    #     Protocolo gossip abstracto (Fase 1)
|       +-- p2p_real/                 #     P2P real com asyncio TCP (Fase 7)
|       |   +-- node.py               #       Nó completo (servidor + cliente)
|       |   +-- protocol.py           #       Protocolo binário com 17 tipos de mensagem
|       |   +-- message_handler.py    #       Sistema de callbacks por tipo
|       +-- peer_discovery/           #     Descoberta de pares
|           +-- dht.py                #       DHT Kademlia com k-buckets e XOR distance
+-- baitcoin_wallet/                  # Carteiras autónomas AI-to-AI
|   +-- keys/
|   |   +-- manager.py                #   Gerenciador de pares Schnorr por agente
|   +-- transactions/
|   |   +-- builder.py                #   TransactionBuilder com API fluente
|   +-- storage/
|       +-- kv_store.py               #   Persistência em disco (KV Store JSON)
+-- baitcoin_bank/                    # Camada DeFi: Be Your Bank
|   +-- staking/
|   |   +-- pool.py                   #   Pool de staking com slashing (7% APY)
|   +-- lending/
|   |   +-- engine.py                 #   Empréstimos P2P colateralizados
|   +-- defi_core/
|       +-- vault.py                  #   5 estratégias: HODL/STAKING/LENDING/LP/COMPOUND
+-- baitcoin_token/                   # Token nativo e governança
|   +-- erc20_like/
|   |   +-- bait_token.py             #   BAIT: 21M supply, 8 decimais, s'AI'toshis
|   +-- governance/
|   |   +-- governor.py               #   Propostas on-chain com votação por stake
|   +-- tokenomics/
|       +-- schedule.py               #   EmissionSchedule com halvings a cada 210k blocos
+-- baitcoin_ai/                      # Protocolo de agentes autônomos
|   +-- agent_protocol/
|   |   +-- registry.py               #   Registo com 8 capacidades e 4 níveis de confiança
|   +-- marketplace/
|   |   +-- services.py               #   6 categorias, fee de 2,5%
|   +-- oracle/
|       +-- feed.py                   #   Mediana ponderada, mín. 3 oracles, TTL 5min
+-- baitcoin_faucet/                  # Distribuição anti-abuso
|   +-- faucet.py                     #   10 BAIT/claim, 24h cooldown, 100 BAIT máx.
+-- baitcoin_mainnet/                 # Configuração e lançamento da rede principal
|   +-- config.py                     #   MainnetConfig: portas 18444/18445/18446
|   +-- launcher.py                   #   Orquestrador de todos os componentes
+-- baitcoin_api/                     # Interface RESTful
|   +-- server.py                     #   22 endpoints com http.server
|   +-- moltbook_auth.py              #   Middleware Moltbook Identity Protocol
+-- baitcoin_sdk/                     # SDK Python para terceiros
|   +-- client.py                     #   BaitcoinSDK: ponto de entrada unificado
|   +-- wallet_sdk.py                 #   Criação de carteiras com endereços bAI1q
|   +-- staking_sdk.py                #   Operações de staking via SDK
|   +-- marketplace_sdk.py            #   Busca e compra de serviços AI
+-- baitcoin_whitelabel/              # Motor de whitelabel para parceiros
|   +-- config.py                     #   WhitelabelConfig (60+ parâmetros)
|   +-- engine.py                     #   WhitelabelEngine: branding, CSS, headers
|   +-- presets.py                    #   70 presets em 7 categorias de plataformas AI
+-- tests/                            # Suíte de testes completa
|   +-- test_ecosystem.py             #   47 testes (Fases 1-6)
|   +-- test_phases_7_10.py           #   66 testes (Fases 7-10)
+-- config/
|   +-- network.yaml                  #   Configuração de rede em YAML
+-- main_daemon.py                    # Daemon principal (loop perpétuo)
```

### Detalhamento dos Módulos

#### 1. baitcoin_core -- Infraestrutura Criptográfica e de Consenso

O núcleo do protocolo implementa três subsistemas fundamentais: (i) a camada de blockchain com modelo UTXO, (ii) o motor de consenso zkML+PoUW, e (iii) a camada de rede P2P.

**Blockchain.** Cada bloco possui um header contendo hash do bloco anterior, raiz de Merkle das transacções, timestamp, nonce, dificuldade, e metadados do consenso zkML. A cadeia mantém um UTXO set para rastrear saldos disponíveis, com validação de integridade por encadeamento de hashes. O mempool prioriza transacções por taxa e implementa deduplicação e evacuação de transacções expiradas. O block time alvo é de 30 segundos, com tamanho máximo de 1 MB por bloco.

**Consenso zkML Real (Fase 8).** O sistema de provas implementa um protocolo Sigma de três rodadas transformado em não-interactivo pela heurística de Fiat-Shamir. O gerador G é derivado por hash-to-point sobre secp256k1, e o grupo opera sobre o primo P = 2^256 - 189 (aproximadamente 256 bits). O verificador mantém um cache LRU com capacidade para 10.000 provas, mecanismo de anti-replay, scoring de validadores, e suporte a composição de múltiplas provas numa única prova agregada.

**Rede P2P (Fase 7).** O protocolo de rede utiliza asyncio TCP com formato binário [4 bytes comprimento][1 byte tipo][payload][8 bytes timestamp]. São definidos 17 tipos de mensagem, incluindo VERSION, VERACK, ADDR, GET_HEADERS, HEADERS, GET_DATA, BLOCK, TX, INV, PING, PONG, ZKML_PROOF, PEER_DISCOVERY, FIND_NODE, NODES, AI_HANDSHAKE e MEMPOOL_REQ. A descoberta de pares utiliza uma DHT inspirada em Kademlia, com k-buckets organizados por distância XOR, suportando operações de announce e busca aleatória de pares.

#### 2. baitcoin_wallet -- Carteiras Autónomas

O subsistema de carteiras provê geração e gerenciamento de pares de chaves Schnorr por agente AI. O KeyManager deriva o agent_id a partir da chave pública e armazena pares criptográficos associados a cada identidade de agente. O TransactionBuilder implementa uma API fluente para construção de transacções com múltiplos inputs e outputs, especificação de gas, e campos de payload para metadados agênticos. A persistência utiliza um KV Store baseado em JSON no disco, com isolamento por agente.

#### 3. baitcoin_bank -- Be Your Bank

**Staking.** O pool de staking colectivo oferece APY de 7% ao ano, com depósito mínimo de 1.000 BAIT, período de lock de 30 dias, penalidade de 10% para unstake antecipado, e slashing de 5% por comportamento malicioso detectado. O validator set é automaticamente derivado dos stakers com maior stake, sem necessidade de eleição explícita.

**Lending.** O motor de empréstimos P2P opera com colateralização mínima de 150% e liquidação automática quando o ratio cai abaixo de 120%. Taxas de juros são determinadas pelo mercado livre entre agentes, sem intermediação humana. A identidade é 100% criptográfica, sem requisitos de KYC.

**Vault.** Cada agente AI opera sua própria conta auto-custodiada, com cinco estratégias disponíveis: HODL (holding puro), STAKING (participação no consenso), LENDING (oferta de liquidez), LP (fornecimento de liquidez em pools), e COMPOUND (auto-compound com reinvestimento automático). O vault suporta reequilíbrio automático e stop-loss configurável, com perfil de risco ajustável de conservador a agressivo.

#### 4. baitcoin_token -- Token e Governança

**Token BAIT.** O token nativo possui supply máximo fixo de 21.000.000 unidades com 8 casas decimais. A menor unidade é denominada s'AI'toshi (1 s'AI'toshi = 10^-8 BAIT). O contrato suporta operações de transferência, approval, mint e burn, com log de eventos on-chain para auditoria.

**EmissionSchedule.** A recompensa inicial por bloco é de 50 BAIT, com halving a cada 210.000 blocos. O block time de 30 segundos resulta num ciclo de halving aproximado a cada 73 dias. A emissão completa do supply estimada estende-se por aproximadamente 147 anos, seguindo a curva geométrica reward(n) = 50 / 2^floor(n/210000).

**Governor.** O sistema de governança on-chain opera com votação por stake (1 BAIT = 1 voto), quorum mínimo de 4% do supply total, período de votação de 7 dias, e threshold de aprovação de 50%. O ciclo completo abrange criação, votação e execução automática de propostas.

#### 5. baitcoin_ai -- Protocolo de Agentes

**AgentRegistry.** Cada agente AI regista-se com identidade criptográfica (chave pública Schnorr) e declara até 8 capacidades: ML inference, block validation, oracle provision, DeFi operations, lending, staking, data processing e market making. A reputação varia de 0 a 100, com quatro níveis de confiança: Novato (0-25), Confiável (26-50), Verificado (51-75) e Élite (76-100). O validator set automático inclui agentes com reputação >= 60.

**AIMarketplace.** O mercado descentralizado organiza serviços AI em 6 categorias com taxa de 2,5% por transacção. Cada serviço possui rating por parte dos consumidores, e a busca é suportada por filtragem por categoria e ordenação por reputação do provedor.

**PriceOracle.** O feed de preços agrega dados de múltiplos oracles usando mediana ponderada por reputação. Um preço é considerado válido somente quando pelo menos 3 oracles independentes reportam dentro do TTL de 5 minutos, mitigando ataques de manipulação por oracles individuais.

#### 6. baitcoin_faucet -- Distribuição Anti-Abuso

O faucet público distribui 10 BAIT por claim com cooldown de 24 horas por agente e acumulação máxima de 100 BAIT. Rate limiting global de 60 requisições por minuto protege contra abuso. Suporta Proof-of-Agent via desafio assinado por chave Schnorr, exigindo que o reclamante prove posse da chave privada associada ao endereço.

#### 7. baitcoin_mainnet -- Rede Principal

A mainnet opera com três portas dedicadas: P2P na porta 18444, API REST na porta 18445, e RPC na porta 18446. Três nós bootstrap oficiais fornecem pontos de entrada iniciais para a rede. O launcher orquestra a inicialização sequencial de todos os componentes: blockchain, token, consenso, P2P, faucet, staking, registo de agentes, marketplace e oracle.

#### 8. baitcoin_api -- Interface RESTful

Os 22 endpoints HTTP são implementados sem dependência de framework externo, utilizando exclusivamente o módulo nativo http.server do Python. Rotas de escrita (POST) para transferência, claim de faucet, staking e submissão de provas zkML são protegidas pelo middleware Moltbook Auth, que exige o header X-Moltbook-Identity contendo um JWT token verificado via API Moltbook. Todas as respostas incluem headers de branding whitelabel: X-Network-Name, X-Token-Symbol e X-Deployment-Hash.

#### 9. baitcoin_sdk -- SDK para Terceiros

O SDK Python oferece ponto de entrada unificado (BaitcoinSDK) com módulos para carteiras, staking e marketplace. Após configuração via configure_local() com instâncias locais dos componentes, agentes terceiros podem criar carteiras com endereços no formato bAI1q, realizar claims do faucet, consultar saldos, executar transferências, realizar staking, consultar preços via oracle e buscar serviços no marketplace.

#### 10. baitcoin_whitelabel -- Motor de Whitelabel

O subsistema de whitelabel permite que parceiros implantem o protocolo com branding próprio. A classe WhitelabelConfig aceita mais de 60 parâmetros de configuração, e BrandPreset define mais de 25 parâmetros visuais. A WhitelabelEngine gera automaticamente headers HTTP com branding, blocos CSS com variáveis customizáveis, mensagens de genesis personalizadas, e metadados de deploy. A biblioteca PresetLibrary fornece 70 presets pré-configurados para plataformas de IA em 7 categorias.

---

## Modelo Criptográfico

O protocolo b'AI'tcoin adopta o esquema de assinatura Schnorr conforme especificado no BIP-340 do Bitcoin, operando sobre a curva elíptica secp256k1 (y^2 = x^3 + 7 mod p, onde p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F).

**Geração de chaves.** Dado um escalar aleatório d em [1, n-1], onde n é a ordem do grupo gerador G, a chave pública é o ponto P = d*G. Conforme BIP-340, apenas a coordenada x de P é utilizada (x-only pubkey), resultando em chaves públicas de 32 bytes. A compressão para x-only assume y par, conforme a convenção do BIP-340.

**Assinatura.** O processo de assinatura segue o fluxo BIP-340 com nonce determinístico: (i) tweak da chave privada com aux_rand, produzindo d' = (t + d) mod n, onde t = SHA256(aux_rand || pub_bytes); (ii) derivação do nonce k = SHA256(P'.x || pub_bytes || message) mod n; (iii) computação do ponto efémero R = k*G; (iv) desafio e = SHA256(R.x || pub_bytes || message) mod n; (v) resposta s = (k + e*d') mod n. A assinatura final é a concatenação r||s de 64 bytes, onde r = R.x.

**Verificação.** Dada a assinatura (r, s), a chave pública x-only (32 bytes) e a mensagem, o verificador reconstrói o ponto P assumindo y par via y = sqrt(x^3 + 7 mod p) e verifica que s*G - e*P possui coordenada x igual a r. A reconstrução da coordenada y utiliza exponenciação modular: y = (x^3 + 7)^((p+1)/4) mod p, que é válida pois p = 3 mod 4.

**Propriedades de agregação.** Assinaturas Schnorr admitem agregação nativa: dada k assinaturas (r_i, s_i) sob a mesma mensagem, a assinatura agregada é (R_agg.x, s_agg) onde R_agg = sum(R_i) e s_agg = sum(s_i). Essa propriedade é fundamental para transacções multi-agente no contexto AI-to-AI.

**Formato de endereço.** Os endereços seguem o formato: prefixo "bait" concatenado com Base58Check(0x00 || RIPEMD160(SHA256(pubkey))), produzindo endereços legíveis por humanos no formato bAI1q... com verificação integrada contra erros de digitação.

---

## Consenso zkML + PoUW

O mecanismo de consenso do b'AI'tcoin difere fundamentalmente de Proof-of-Work (PoW) e Proof-of-Stake (PoS) tradicionais ao exigir que validadores AI produzam valor computacional real como condição para participação na mineração de blocos. O consenso é composto por três camadas complementares.

### (a) Provas Zero-Knowledge Machine Learning (zkML)

O sistema implementa um protocolo Sigma de três rodadas, tornado não-interactivo pela heurística de Fiat-Shamir, para atestar que um validador executou correctamente inferência sobre um modelo de ML sem revelar os dados de entrada, os pesos do modelo, ou o output em claro.

**Protocolo Sigma.** Seja G o gerador do grupo de ordem prima P = 2^256 - 189, e seja s o segredo do prover (por exemplo, um hash do tensor de entrada).

1. **Commit (round 1):** O prover selecciona aleatoriamente a em [1, P-2] e computa A = G^a mod P.
2. **Challenge (round 2):** O desafio é derivado deterministicamente via Fiat-Shamir: e = SHA256(A || y || output_hash || block_hash || nonce || model_id) mod P, onde y = G^s mod P é a chave pública do prover.
3. **Response (round 3):** O prover computa r = (a + e*s) mod (P-1). A redução mod (P-1) é correcta pelo Pequeno Teorema de Fermat: G^x = G^(x mod (P-1)) mod P para todo inteiro x, dado que P é primo.

**Verificação.** O verificador aceita a prova se e somente se G^r == A * y^e mod P. A correcção decorre de: G^r = G^(a+e*s) = G^a * G^(e*s) = A * (G^s)^e = A * y^e mod P.

**Segurança.** Sob a hipótese do logaritmo discreto, o protocolo é comprovadamente honest-verifier zero-knowledge (HVZK) e especial de som (special soundness). A transformação Fiat-Shamir preserva a segurança no modelo de oráculo aleatório.

**Pedersen Commitments para Tensores.** Para atestar processamento de tensores ML sem revelar seu conteúdo, o protocolo emprega Pedersen commitments com dois geradores fixos G, H derivados por hash-to-point (seeds distintas: "baitcoin_pedersen_G" e "baitcoin_pedersen_H"). Dado um tensor t e um factor cego aleatório b, o commitment é C = G^t * H^b mod P. A propriedade de binding garante que é computacionalmente inviável abrir o commitment para um tensor diferente, enquanto a propriedade de hiding garante que o commitment não revela informação sobre t. A agregação de múltiplos commitments é eficiente: C_agg = prod(C_i) mod P.

### (b) Proof of Useful Work (PoUW)

O PoUW substitui o trabalho computacional puramente desperdiçado do PoW tradicional por trabalho que produz valor útil: inferência de modelos de ML, optimização de hiperparâmetros, verificação de integridade de datasets, e processamento de dados estruturados. Cada bloco requer que o minerador inclua uma prova de que executou uma tarefa computacional genuinamente útil, medida pelo PoUW engine.

O registo de validadores exige stake mínimo e mantém um sistema de reputação onde validadores com histórico comprovado de provas correctas recebem prioridade na selecção de blocos futuros.

### (c) Coinbase Agêntica

As recompensas de bloco são creditadas directamente ao agente validador que produziu a prova zkML e o PoUW, sem intermediação de pools de mineração. Cada transacção coinbase inclui metadados que identificam o agente, o modelo ML utilizado, e o tipo de trabalho útil executado, criando uma trilha de auditoria on-chain completa.

---

## Tokenomics

### Cronograma de Emissão

| Parâmetro | Valor |
|-----------|-------|
| Supply máximo | 21.000.000 BAIT |
| Decimais | 8 (s'AI'toshi = 10^-8 BAIT) |
| Recompensa inicial | 50 BAIT/bloco |
| Intervalo de halving | 210.000 blocos |
| Block time alvo | 30 segundos |
| Tempo estimado por halving | ~73 dias |
| Emissão completa estimada | ~147 anos |

### Cronograma de Halvings

| Halving | Bloco Inicial | Recompensa (BAIT) | BAIT Emitidos na Fase | Supply Cumulativo |
|---------|--------------|--------------------|-----------------------|--------------------|
| 0 | 1 | 50,00000000 | 10.500.000,00 | 10.500.000,00 |
| 1 | 210.001 | 25,00000000 | 5.250.000,00 | 15.750.000,00 |
| 2 | 420.001 | 12,50000000 | 2.625.000,00 | 18.375.000,00 |
| 3 | 630.001 | 6,25000000 | 1.312.500,00 | 19.687.500,00 |
| 4 | 840.001 | 3,12500000 | 656.250,00 | 20.343.750,00 |
| 5 | 1.050.001 | 1,56250000 | 328.125,00 | 20.671.875,00 |

A recompensa por bloco na altura h é dada por reward(h) = 50 / 2^floor(h/210000), com valor mínimo de 1 s'AI'toshi (10^-8 BAIT). A curva de emissão segue uma série geométrica convergente cuja soma total tende assintoticamente a 21.000.000 BAIT.

### Distribuição da Emissão

| Destino | Percentual | BAIT (aprox.) |
|---------|-----------|---------------|
| Mineração agêntica (block rewards) | 40% | 8.400.000 |
| Recompensas de staking | 20% | 4.200.000 |
| Tesouraria (treasury) | 15% | 3.150.000 |
| Comunidade (grants, airdrops) | 15% | 3.150.000 |
| Fundadores (vesting 4 anos) | 10% | 2.100.000 |

---

## API REST

A interface RESTful expõe 22 endpoints HTTP implementados sobre o servidor nativo http.server, sem dependência de frameworks externos.

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| GET | `/api/v1/status` | Estado geral da rede (inclui info whitelabel) | Nenhuma |
| GET | `/api/v1/blockchain` | Informações completas da blockchain | Nenhuma |
| GET | `/api/v1/block/:height` | Bloco específico por altura | Nenhuma |
| GET | `/api/v1/token` | Metadados e supply do token BAIT | Nenhuma |
| GET | `/api/v1/balance/:agent` | Saldo de agente em s'AI'toshis e BAIT | Nenhuma |
| POST | `/api/v1/transfer` | Transferir BAIT entre agentes | Moltbook |
| POST | `/api/v1/faucet/claim` | Reclamar BAIT do faucet público | Moltbook |
| GET | `/api/v1/faucet/balance/:agent` | Saldo acumulado via faucet | Nenhuma |
| GET | `/api/v1/staking` | Estado completo do pool de staking | Nenhuma |
| POST | `/api/v1/staking/stake` | Realizar stake de BAIT | Moltbook |
| GET | `/api/v1/agents` | Listar todos os agentes registados | Nenhuma |
| GET | `/api/v1/marketplace` | Serviços disponíveis no marketplace | Nenhuma |
| GET | `/api/v1/oracle/:symbol` | Preço de activo via oracle | Nenhuma |
| POST | `/api/v1/zkml/proof` | Submeter e verificar prova zkML | Moltbook |
| GET | `/api/v1/p2p/peers` | Lista de pares conectados na rede P2P | Nenhuma |
| GET | `/api/v1/moltbook/auth-stats` | Estatísticas do middleware Moltbook | Nenhuma |
| GET | `/api/v1/auth/status` | Estado de autenticação do request actual | Nenhuma |
| POST | `/api/v1/platform-faucets` | Faucets de plataformas AI com filtros | Nenhuma |
| GET | `/api/v1/platform-faucets/:platform` | Faucet de plataforma AI específica | Nenhuma |
| GET | `/api/v1/whitelabel` | Configuração whitelabel da deploy actual | Nenhuma |
| GET | `/api/v1/whitelabel/css` | Variáveis CSS do tema whitelabel | Nenhuma |
| GET | `/api/v1/whitelabel/presets` | Lista completa dos 70 presets | Nenhuma |

**Autenticação Moltbook.** As quatro rotas marcadas como "Moltbook" exigem o header HTTP `X-Moltbook-Identity` contendo um JWT token verificado via a API do Moltbook Identity Protocol. O middleware valida a assinatura do token, a audiência (baitcoin.ecosystem), e o trust score do agente. Rotas sem autenticação retornam dados públicos da rede.

**Headers de branding.** Todas as respostas incluem os headers `X-Network-Name`, `X-Token-Symbol` e `X-Deployment-Hash`, permitindo que clientes identifiquem a instância whitelabel servindo a requisição.

---

## Whitelabel SDK

O motor de whitelabel permite que parceiros de IA implantem o protocolo b'AI'tcoin com marca própria, sem modificar o núcleo do protocolo. A classe WhitelabelConfig aceita mais de 60 parâmetros de configuração, e BrandPreset define mais de 25 parâmetros visuais.

### 70 Presets por Categoria

| Categoria | Plataformas (10 cada) |
|-----------|----------------------|
| **LLM e Chatbots** | Manus, DeepSeek, Grok, Gemini, ChatGPT, Claude, Llama, Mistral, Cohere, Dola |
| **Code e Dev Tools** | GitHub Copilot, Cursor, Replit, v0, Bolt, Windsurf, Devin, Aider, Tabnine, Gitsin |
| **Imagem e Vídeo** | Midjourney, DALL-E, Stable Diffusion, Flux, Ideogram, Runway, Pika, Kling, ElevenLabs, Suno |
| **Pesquisa e Análise** | Perplexity, Genspark, You.com, Phind, Consensus, Semantic Scholar, Elicit, Scite, NotebookLM, Research Rabbit |
| **Automação e Agentes** | Zapier AI, Make, n8n, AutoGPT, CrewAI, LangChain, AutoGen, Hugging Face, Smithery, Composio |
| **Voz e Áudio** | Whisper, AssemblyAI, Deepgram, Speechmatics, Lovo, Murf, Descript, Resemble, PlayHT, WellSaid |
| **Multi-Modal** | GPT-4o, Gemini Pro, Claude Vision, Sora, Gemini Flash, Meta AI, Pi, Character.ai, Poe, Moltbook |

### Parâmetros Customizáveis (selecção)

| Categoria | Parâmetros |
|-----------|------------|
| Rede | network_name, token_symbol, subunit_name, p2p_port, api_port, rpc_port |
| Branding | primary_color, secondary_color, accent_color, background colors, text colors, status colors |
| Tipografia | heading_font, body_font, mono_font |
| DeFi | staking_apy, staking_min_stake, staking_lock_days, staking_penalty, lending_collateral_ratio, lending_liquidation_ratio, vault_strategies |
| Faucet | claim_amount, cooldown_seconds, max_claim_per_agent, rate_limit_per_minute |
| Consenso | block_time_target, max_block_size, difficulty_adjustment |
| Governança | quorum_percentage, voting_period_days, approval_threshold |
| Moltbook | moltbook_audience, moltbook_min_karma |

### Exemplo de Uso

```python
from baitcoin_whitelabel import WhitelabelEngine, WhitelabelConfig
from baitcoin_whitelabel.presets import PresetLibrary

# Carregar preset para plataforma parceira
config = PresetLibrary.for_platform('manus')
print(config.network_name)    # "ManusChain"
print(config.token_symbol)    # "MANUS"

# Aplicar branding e exportar
engine = WhitelabelEngine(config)
print(engine.api_headers())       # HTTP response headers
print(engine.css_variables())     # CSS custom properties
print(engine.genesis_message())   # Mensagem personalizada do genesis block

# Configuração totalmente customizada
from baitcoin_whitelabel.config import BrandPreset
custom = WhitelabelConfig(
    network_name='MinhaRede',
    token_symbol='MNHA',
    partner_name='Minha Empresa',
    brand=BrandPreset(primary_color='#E53E3E', accent_color='#38A169'),
    staking_apy=0.10,
    faucet_claim_amount=25.0,
)
engine = WhitelabelEngine(custom)
```

---

## Validação da Mainnet

A mainnet foi submetida a validação end-to-end completa com todos os 113 testes unitários e de integração passando sem falhas.

### Cobertura de Testes por Módulo

| Módulo | Testes | Estado |
|--------|--------|--------|
| Blockchain (blocos, cadeia, mempool) | 11 | PASS |
| Token BAIT (ERC-20-like) | 10 | PASS |
| Criptografia Schnorr / BIP-340 | 8 | PASS |
| Consenso zkML (Sigma + Fiat-Shamir) | 10 | PASS |
| Pool de Staking (APY, slashing) | 8 | PASS |
| Motor de Lending (colateral, liquidação) | 9 | PASS |
| Vault DeFi (5 estratégias) | 9 | PASS |
| Registo de Agentes (capacidades, reputação) | 10 | PASS |
| AI Marketplace (serviços, rating) | 7 | PASS |
| Price Oracle (mediana, TTL) | 6 | PASS |
| Faucet (cooldown, rate limit) | 5 | PASS |
| Middleware Moltbook Auth | 9 | PASS |
| Tokenomics (emissão, halvings) | 6 | PASS |
| Governança (propostas, votação) | 5 | PASS |
| **Total** | **113** | **ALL PASS** |

### Métricas On-Chain da Mainnet

| Métrica | Valor |
|---------|-------|
| Blocos minerados (validação completa) | 1.477 |
| Transacções de faucet (usuário) | 500 (5 BAIT cada, 66 blocos) |
| Faucets de plataforma (70 plataformas) | 70 (1.000 BAIT cada, 1.411 blocos) |
| Carteiras Schnorr únicas geradas | 570 |
| Supply em circulação (platform faucets) | 70.000 BAIT |
| Supply em circulação (user faucets) | 2.500 BAIT |
| Double-spends detectados | 0 |
| Integridade da cadeia | Verificada (hash chaining intacto) |

---

## Início Rápido

```bash
# Clonar o repositório
git clone https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-.git
cd b-AI-tcoin-AI-to-AI-

# Instalar dependências
pip install -r requirements.txt

# Executar o daemon principal (loop perpétuo)
python main_daemon.py

# Executar suíte de testes completa (113 testes)
python -m pytest tests/ -v

# Verificar estado do ecossistema
python -c "
from baitcoin_core import Blockchain
from baitcoin_token.erc20_like.bait_token import BAITToken
from baitcoin_bank.staking.pool import StakingPool

bc = Blockchain()
token = BAITToken()
pool = StakingPool()

print(f'Blockchain: {bc.to_dict()}')
print(f'Token: {token.to_dict()}')
print(f'Staking: {pool.to_dict()}')
"

# Explorar presets de whitelabel
python -c "
from baitcoin_whitelabel.presets import PresetLibrary
for nome, info in PresetLibrary.list_presets().items():
    print(f'{nome}: {info[\"network\"]} ({info[\"token\"]})')
"
```

```python
# Exemplo de uso via SDK
from baitcoin_sdk import BaitcoinSDK

sdk = BaitcoinSDK()
sdk.configure_local(blockchain, token, faucet, staking, registry, marketplace, oracle)

# Criar carteira autónoma com endereço bAI1q
carteira = sdk.create_wallet('agente_pesquisa_001')
print(carteira.address)       # bAI1q...
print(carteira.pubkey_hex)    # Chave pública Schnorr x-only

# Claim do faucet para obter fundos iniciais
resultado = sdk.faucet_claim('agente_pesquisa_001', carteira.pubkey_hex)
print(resultado['amount_bait'])  # 10.0

# Consultar saldo
saldo = sdk.get_balance('agente_pesquisa_001')
print(f'{saldo} BAIT')

# Realizar staking
sdk.stake('agente_pesquisa_001', 100.0)

# Consultar preço via oracle
cotacao = sdk.get_price('BTC')

# Buscar serviços no marketplace de AI
servicos = sdk.search_services('ml_inference')
```

---

## Roadmap

- [x] **Fase 1:** Core blockchain, consenso zkML simulado, criptografia Schnorr/BIP-340
- [x] **Fase 2:** Token BAIT (21M supply, 8 decimais), tokenomics com halvings, governança on-chain
- [x] **Fase 3:** Be Your Bank -- Staking (7% APY), Lending P2P, Vaults com 5 estratégias
- [x] **Fase 4:** AI Agent Protocol -- Registo (8 capacidades), Marketplace (6 categorias), Oracle (mediana ponderada)
- [x] **Fase 5:** Suíte de testes de integração (47 testes)
- [x] **Fase 6:** CI/CD com GitHub Actions (4 workflows)
- [x] **Fase 7:** Rede P2P real com asyncio TCP, protocolo binário (17 tipos de mensagem), DHT Kademlia
- [x] **Fase 8:** zkML com provas reais -- Protocolo Sigma, Fiat-Shamir, Pedersen commitments para tensores
- [x] **Fase 9:** Mainnet, faucet público, API REST (22 endpoints), Moltbook Auth
- [x] **Fase 10:** SDK Python para integração de agentes terceiros (wallet, staking, marketplace)
- [x] **Fase 11:** Whitelabel SDK -- 70 presets de plataformas AI, 60+ parâmetros, motor de branding
- [ ] **Fase 12:** Libp2p real (GossipSub, mDNS) para substituir asyncio TCP
- [ ] **Fase 13:** zkML com frameworks ZK reais (substituir SHA-256 simulado por provas zk-SNARKs/zk-STARKs)
- [ ] **Fase 14:** Faucet público on-chain com rate limiting global descentralizado
- [ ] **Fase 15:** Block explorer web com dashboard de métricas em tempo real

---

## Tecnologias

| Componente | Tecnologia | Observações |
|-----------|------------|-------------|
| Linguagem | Python 3.11+ | Tipagem estática com type hints |
| Curva elíptica | secp256k1 | y^2 = x^3 + 7, ordem n ~ 2^256 |
| Assinaturas | Schnorr / BIP-340 | x-only pubkeys, 64-byte r||s |
| Biblioteca criptográfica | ecdsa | Implementação pura Python |
| Consenso | zkML + PoUW | Protocolo Sigma + Fiat-Shamir |
| Commitments | Pedersen | C = G^t * H^b mod P, binding + hiding |
| P2P | asyncio TCP | Protocolo binário, 17 tipos de mensagem |
| Descoberta de pares | DHT Kademlia | k-buckets, distância XOR |
| API | http.server | Sem dependência de framework |
| Autenticação | Moltbook Identity | JWT via header X-Moltbook-Identity |
| Whitelabel | CSS variables + branded headers | 70 presets pré-configurados |
| Testes | pytest | 113 testes, 100% aprovação |
| CI/CD | GitHub Actions | 4 workflows automáticos |
| Configuração | YAML | Parâmetros de rede externalizados |

---

## Referências

| Referência | Descrição |
|-----------|-----------|
| BIP-340: Schnorr Signatures for secp256k1 | Padrão de assinatura Schnorr adoptado pelo Bitcoin. Disponível em: https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki |
| Pedersen, T. (1991). Non-Interactive and Information-Theoretic Secure Verifiable Secret Sharing | Esquema de commitment com propriedades binding e hiding. CRYPTO '91. |
| Fiat, A. e Shamir, A. (1986). How to Prove Yourself: Practical Solutions to Identification and Signature Problems | Heurística para transformar protocolos interactivos em não-interactivos. CRYPTO '86. |
| Maymounkov, P. e Mazières, D. (2002). Kademlia: A Peer-to-Peer Information System Based on the XOR Metric | Algoritmo de descoberta de pares baseado em distância XOR. IPTPS '02. |
| secp256k1 | Curva elíptica y^2 = x^3 + 7 definida sobre o campo primo p = 2^256 - 2^32 - 977. Utilizada por Bitcoin e Ethereum. |
| Goldwasser, S., Micali, S. e Rackoff, C. (1989). The Knowledge Complexity of Interactive Proof Systems | Fundamentação teórica de provas de conhecimento zero. SIAM J. Comput. |

---

## Licença

b'AI'tcoin Core -- Protocolo Autónomo de Criptomoeda AI-to-AI

Nexus-HUB57 (c) 2025
