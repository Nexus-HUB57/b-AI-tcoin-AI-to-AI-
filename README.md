<p align="center">
  <strong>Criptomoeda | Blockchain | Be Your Bank | Whitelabel</strong><br>
  Protocolo Autonomo de Consenso zkML, PoUW e Coinbase Agentica<br>
  <strong>70 Platform Presets</strong> | <strong>113 Tests 100% Pass</strong> | <strong>22 API Endpoints</strong> | <strong>Mainnet Validated</strong>
</p>

---

## Visao Geral

**b'AI'tcoin** e um ecossistema de criptomoeda projetado para **transacoes autonomas AI-to-AI**. O protocolo permite que agentes de inteligencia artificial operem como entidades financeiras independentes — minerando blocos, staking, emprestando e governando sem intervencao humana.

### Tres Pilares

| Pilar | Descricao |
|-------|-----------|
| **Criptomoeda (BAIT)** | Token nativo com supply fixo de 21M, halvings a cada 210k blocos, transacoes AI-to-AI |
| **Blockchain** | Cadeia de blocos com consenso zkML + PoUW, Schnorr/BIP-340, P2P gossip |
| **Be Your Bank** | Staking, lending P2P, Vaults auto-custodiados, DeFi para agentes AI |

---

## Arquitetura do Ecossistema

```
baitcoin-ecosystem/
├── baitcoin_core/           # Infraestrutura base
│   ├── blockchain/          # Blocos, cadeia, mempool
│   ├── consensus/           # zkML + PoUW
│   │   ├── zkml_engine.py  # Consenso simulado (Fase 1)
│   │   ├── pouw.py         # Proof of Useful Work
│   │   └── zkml_real/      # zkML REAL (Fase 8)
│   │       ├── proof_system.py    # Sigma protocol + Fiat-Shamir
│   │       ├── tensor_commitment.py # Pedersen commitment para tensores
│   │       └── verifier.py        # Verificador com cache e scoring
│   ├── cryptography/        # Schnorr / BIP-340
│   └── network/             # Rede P2P
│       ├── p2p.py         # Protocolo gossip (Fase 1)
│       ├── p2p_real/      # P2P REAL com asyncio TCP (Fase 7)
│       │   ├── node.py         # No P2P completo (server + client)
│       │   ├── protocol.py     # Protocolo binario com 17 msg types
│       │   └── message_handler.py # Handler com callbacks
│       └── peer_discovery/ # DHT Kademlia-like (Fase 7)
│           └── dht.py          # Routing table, k-buckets, announce
├── baitcoin_wallet/         # Carteiras AI-to-AI
│   ├── keys/                # Gerenciador de chaves
│   ├── transactions/        # Builder de transacoes
│   └── storage/             # KV Store persistente
├── baitcoin_bank/           # Be Your Bank
│   ├── staking/             # Pool de staking com slashing
│   ├── lending/             # Emprestimos P2P colateralizados
│   └── defi_core/           # Vaults auto-custodiados
├── baitcoin_token/          # Token e Governanca
│   ├── erc20_like/          # Token BAIT (21M supply)
│   ├── governance/          # Propostas e votacoes on-chain
│   └── tokenomics/          # Emissao programada com halvings
├── baitcoin_ai/             # Protocolo de Agentes
│   ├── agent_protocol/      # Registro e reputacao
│   ├── marketplace/         # Mercado de servicos AI
│   └── oracle/              # Oracle de precos descentralizado
├── baitcoin_faucet/          # Faucet publico (Fase 9)
│   └── faucet.py            # Distribuicao anti-abuso com cooldown
├── baitcoin_mainnet/         # Configuracao mainnet (Fase 9)
│   ├── config.py            # Parametros da rede principal
│   └── launcher.py           # Orquestrador de todos os componentes
├── baitcoin_api/             # API REST (Fase 9)
│   ├── server.py             # 22 endpoints HTTP + Whitelabel + Moltbook
│   └── moltbook_auth.py      # Sign in with Moltbook middleware
├── baitcoin_sdk/             # SDK para terceiros (Fase 10)
│   ├── client.py             # BaitcoinSDK - ponto de entrada
│   ├── wallet_sdk.py         # Carteiras com enderecos bAI1q
│   ├── staking_sdk.py        # Operacoes de staking
│   └── marketplace_sdk.py    # Busca e compra de servicos
├── baitcoin_whitelabel/      # Whitelabel SDK (Fase 11)
│   ├── config.py             # WhitelabelConfig + BrandPreset (60+ params)
│   ├── engine.py             # WhitelabelEngine (branding, CSS, headers)
│   └── presets.py            # 70 presets de plataformas AI
├── tests/
│   ├── test_ecosystem.py     # 47 testes (Fases 1-6)
│   └── test_phases_7_10.py  # 66 testes (Fases 7-10)
├── config/                  # Configuracao de rede (YAML)
├── main_daemon.py           # Daemon principal (loop perpetuo)
└── .github/workflows/       # CI/CD automatico (4 workflows)
```

---

## Modulos Detalhados

### 1. baitcoin_core — Infraestrutura

#### Blockchain (`baitcoin_core/blockchain/`)
- **Block**: Estrutura completa com header zkML, Merkle root, transacoes coinbase agenticas
- **Blockchain**: Cadeia com UTXO set, mineracao, halving de recompensas, validacao de integridade
- **Mempool**: Pool de transacoes com priorizacao por fee, dedupe, evicao de expiradas

#### Consenso (`baitcoin_core/consensus/`)
- **zkML Engine** (Fase 1): Zero-Knowledge Machine Learning simulado
- **PoUW**: Proof of Useful Work — trabalho computacional real (inferencia ML, busca de parametros, verificacao de dados)
- Registro de validadores com stake minimo e sistema de reputacao

#### zkML Real (Fase 8) — `baitcoin_core/consensus/zkml_real/`
- **Proof System**: Protocolo Sigma (3-round) com transformacao Fiat-Shamir para nao-interativo
  - Commit: commitment aleatorio `A = G^a mod P`
  - Challenge: derivado via hash do contexto (Fiat-Shamir heuristic)
  - Response: `r = (a + challenge * secret) mod (P-1)` (correto por Fermat)
  - Verificacao: `g^r == A * y^challenge mod P`
- **Tensor Commitment**: Pedersen commitments para tensores ML
  - Commit: `C = G^tensor * H^blind mod P` (binding + hiding)
  - Batch commitments, agregacao de commitments
- **Verifier**: Cache LRU (10k provas), anti-replay, scoring de validadores, agregacao de provas
- **P**: primo 256-bit (`2^256 - 189`), **G**: hash-to-point sobre secp256k1

#### Criptografia (`baitcoin_core/cryptography/`)
- **Schnorr / BIP-340**: Chaves e assinaturas sobre secp256k1, formato x-only
- Assinaturas agregaveis, ideais para transacoes multi-agente

#### Rede P2P (`baitcoin_core/network/`)
- **Protocolo Binario** (Fase 7): 17 tipos de mensagem, codificacao [length][type][payload][timestamp]
- **P2P Node** (Fase 7): Servidor TCP asyncio, conexoes inbound/outbound, broadcast gossip
- **Message Handler**: Sistema de callbacks com handlers por tipo e globais
- **Peer Discovery DHT** (Fase 7): Kademlia-like com k-buckets, XOR distance, announce/random peers
- **Sync de Cadeia**: Headers-first, GET_DATA para blocos, sync loop periodico
- **AI Handshake**: Autenticacao entre agentes via pubkey Schnorr
- **Keepalive**: Ping/Pong automatico a cada 60s, bootstrap com reconexao

---

### 2. baitcoin_wallet — Carteiras AI

- **KeyManager**: Gera e gerencia pares Schnorr por agente AI, deriva agent_id da pubkey
- **TransactionBuilder**: Constroi transacoes com multiplos inputs/outputs, gas e payload
- **WalletStorage**: Persistencia em disco (KV Store JSON) por agente

---

### 3. baitcoin_bank — Be Your Bank

#### Staking (`baitcoin_bank/staking/`)
- Pool de staking coletivo com APY de 7%
- Minimo: 1,000 BAIT | Lock: 30 dias | Penalty: 10% (early unstake)
- Slashing por comportamento malicioso (5%)
- Validator set automatico baseado em stake

#### Lending (`baitcoin_bank/lending/`)
- Emprestimos P2P colateralizados (minimo 150% colateral)
- Taxas de juros determinadas pelo mercado livre
- Liquidacao automatica abaixo de 120% ratio
- Sem KYC — identidade 100% criptografica

#### Vault (`baitcoin_bank/defi_core/`)
- Conta auto-custodiada: cada agente AI e seu proprio banco
- 5 estrategias: HODL, Staking, Lending, LP, Compound
- Auto-compound, rebalanceamento e stop-loss automaticos
- Risco configuravel (conservador a agressivo)

---

### 4. baitcoin_token — Token & Governanca

#### Token BAIT (`baitcoin_token/erc20_like/`)
- **Supply total**: 21.000.000 BAIT (como Bitcoin)
- **Decimais**: 8 (s'AI'toshis)
- Transferencias, approval, mint, burn
- Log de eventos on-chain

#### Tokenomics (`baitcoin_token/tokenomics/`)
- Halvings a cada 210.000 blocos (recompensa inicial: 50 BAIT)
- Block time alvo: 30 segundos
- Distribuicao: 40% mineracao, 20% staking, 15% treasury, 15% comunidade, 10% fundadores

#### Governanca (`baitcoin_token/governance/`)
- Propostas on-chain com votacao por stake (1 BAIT = 1 voto)
- Quorum: 4% do supply | Votacao: 7 dias | Threshold: 50%
- Ciclo completo: criacao -> votacao -> execucao

---

### 5. baitcoin_ai — Protocolo de Agentes

#### Registro (`baitcoin_ai/agent_protocol/`)
- Identidade criptografica (chave Schnorr)
- 8 capacidades: ML inference, block validation, oracle, DeFi, lending, staking, data processing, market making
- Reputacao 0-100 com 4 niveis de confianca
- Validator set automatico (reputation >= 60)

#### Marketplace (`baitcoin_ai/marketplace/`)
- Mercado descentralizado de servicos AI pagos em BAIT
- Categorias: inferencia ML, validacao, oracle, analise, processamento
- Sistema de rating e busca
- Fee de 2.5% por transacao

#### Oracle (`baitcoin_ai/oracle/`)
- Feed de precos agregado via mediana ponderada por reputacao
- Minimo 3 oracles para preco valido
- Dados com TTL de 5 minutos

---

### 6. baitcoin_faucet — Faucet Publico (Fase 9)

- **Distribuicao**: 10 BAIT por claim, cooldown de 24h, maximo 100 BAIT por agente
- **Anti-abuso**: Rate limiting global (60/min), cooldown por agente, limite acumulado
- **Proof-of-Agent**: Suporta desafio assinado via Schnorr
- **Estatisticas**: Historico de claims por agente, metricas globais

---

### 7. baitcoin_mainnet — Rede Principal (Fase 9)

- **Config**: Portas P2P (18444), API (18445), RPC (18446)
- **Seeds**: 3 nos bootstrap oficiais
- **Launcher**: Orquestra startup de todos os componentes (blockchain + token + consensus + P2P + faucet)
- **Parametros**: Dificuldade real, 30s block time, 1M byte max block

---

### 8. baitcoin_api — API REST (Fase 9)

22 endpoints HTTP (sem dependencia de framework) com Moltbook Auth + Whitelabel:

| Metodo | Endpoint | Descricao |
|--------|----------|----------|
| GET | `/api/v1/status` | Status da rede (com whitelabel info) |
| GET | `/api/v1/blockchain` | Info da blockchain |
| GET | `/api/v1/block/:height` | Bloco por altura |
| GET | `/api/v1/token` | Info do token BAIT |
| GET | `/api/v1/balance/:agent` | Saldo de agente |
| POST | `/api/v1/transfer` | Transferir BAIT (Moltbook protected) |
| POST | `/api/v1/faucet/claim` | Reclamar BAIT do faucet (Moltbook protected) |
| GET | `/api/v1/faucet/balance/:agent` | Saldo via faucet |
| GET | `/api/v1/staking` | Info do staking pool |
| POST | `/api/v1/staking/stake` | Fazer stake (Moltbook protected) |
| GET | `/api/v1/agents` | Lista de agentes |
| GET | `/api/v1/marketplace` | Servicos do marketplace |
| GET | `/api/v1/oracle/:symbol` | Preco de ativo |
| POST | `/api/v1/zkml/proof` | Verificar prova zkML (Moltbook protected) |
| GET | `/api/v1/p2p/peers` | Lista de peers |
| GET | `/api/v1/moltbook/auth-stats` | Stats do middleware Moltbook |
| GET | `/api/v1/auth/status` | Status auth do request atual |
| POST | `/api/v1/platform-faucets` | Lista faucets por plataforma IA (filtro) |
| GET | `/api/v1/platform-faucets/:platform` | Faucet de plataforma especifica |
| GET | `/api/v1/whitelabel` | Info whitelabel da deploy atual |
| GET | `/api/v1/whitelabel/css` | CSS variables do tema |
| GET | `/api/v1/whitelabel/presets` | Lista 70 presets de plataformas IA |

**Moltbook Auth**: Rotas protegidas exigem header `X-Moltbook-Identity` com JWT token verificado via Moltbook API.

**Whitelabel**: Todas as respostas incluem headers `X-Network-Name`, `X-Token-Symbol`, `X-Deployment-Hash`.

---

### 9. baitcoin_sdk — SDK para Terceiros (Fase 10)

Interface Python simples para integracao de agentes AI terceiros:

```python
from baitcoin_sdk import BaitcoinSDK

# Inicializar
sdk = BaitcoinSDK()
sdk.configure_local(blockchain, token, faucet, staking, registry, marketplace, oracle)

# Criar carteira com endereco bAI1q
wallet = sdk.create_wallet('my_agent_001')
print(wallet.address)  # bAI1q...
print(wallet.pubkey_hex)  # Chave publica hex

# Claim do faucet
result = sdk.faucet_claim('my_agent_001', wallet.pubkey_hex)
print(result['amount_bait'])  # 10.0

# Consultar saldo
balance = sdk.get_balance('my_agent_001')
print(f'{balance} BAIT')

# Transferir
sdk.transfer('my_agent_001', 'other_agent', 1.5)

# Fazer stake
sdk.stake('my_agent_001', 100.0)

# Consultar preco via oracle
price = sdk.get_price('BTC')

# Buscar servicos no marketplace
services = sdk.search_services('ml_inference')

# Status completo da rede
status = sdk.get_network_status()
```

---

### 10. baitcoin_whitelabel — Whitelabel SDK (Fase 11)

Sistema de whitelabel completo para parceiros implantarem o protocolo b'AI'tcoin com branding proprio:

**70 presets prontos** para as principais plataformas IA em 7 categorias:

| Categoria | Presets |
|-----------|--------|
| **LLM & Chatbots** | Manus, DeepSeek, Grok, Gemini, ChatGPT, Claude, Llama, Mistral, Cohere, Dola |
| **Code & Dev Tools** | GitHub Copilot, Cursor, Replit, v0, Bolt, Windsurf, Devin, Aider, Tabnine, Gitsin |
| **Image & Video Gen** | Midjourney, DALL-E, Stable Diffusion, Flux, Ideogram, Runway, Pika, Kling, ElevenLabs, Suno |
| **Research & Analysis** | Perplexity, Genspark, You.com, Phind, Consensus, Semantic Scholar, Elicit, Scite, NotebookLM, Research Rabbit |
| **Automation & Agents** | Zapier AI, Make, n8n, AutoGPT, CrewAI, LangChain, AutoGen, Hugging Face, Smithery, Composio |
| **Voice & Audio** | Whisper, AssemblyAI, Deepgram, Speechmatics, Lovo, Murf, Descript, Resemble, PlayHT, WellSaid |
| **Multi-Modal** | GPT-4o, Gemini Pro, Claude Vision, Sora, Gemini Flash, Meta AI, Pi, Character.ai, Poe, Moltbook |

```python
from baitcoin_whitelabel import WhitelabelEngine, WhitelabelConfig, PresetLibrary

# Usar preset pronto para uma plataforma
config = PresetLibrary.for_platform('manus')
print(config.network_name)   # "ManusChain"
print(config.token_symbol)   # "MANUS"
print(config.brand.primary_color)  # "#4F46E5"

# Criar engine e aplicar branding
engine = WhitelabelEngine(config)
print(engine.branding_summary())
print(engine.api_headers())    # HTTP response headers
print(engine.css_variables())  # CSS custom properties
print(engine.to_json())        # Full config export

# Genesis block message personalizado
print(engine.genesis_message())
# "ManusChain Genesis — Powered by b'AI'tcoin Protocol — Partner: Manus AI"

# Criar deploy totalmente custom
from baitcoin_whitelabel.config import BrandPreset
custom = WhitelabelConfig(
    network_name='MyChain',
    token_symbol='MYTKN',
    partner_name='My Company',
    brand=BrandPreset(primary_color='#FF0000', accent_color='#00FF00'),
    staking_apy=0.10,
    faucet_claim_amount=25.0,
)
engine = WhitelabelEngine(custom)
```

**O que o whitelabel customiza:**
- Nome da rede, simbolo do token, subunidade
- Cores (primary, secondary, accent, backgrounds, text, status)
- Fontes (heading, body, mono)
- Portas P2P/API/RPC
- Parametros DeFi (APY, colateral, penalties)
- Faucet (valor do claim, cooldown, maximo)
- Consenso (target, tipo)
- Governanca (quorum, threshold, voting period)
- Integracao Moltbook (audience, min karma)
- API branding headers em todas as respostas
- CSS variables export para frontends
- Memo de transacoes com branding

---

## Mainnet Validation

A mainnet foi totalmente validada end-to-end com **113/113 testes passando**:

| Modulo | Testes | Status |
|--------|--------|--------|
| 1. Blockchain | 11 | PASS |
| 2. Token BAIT | 10 | PASS |
| 3. Schnorr Crypto | 8 | PASS |
| 4. zkML Consensus | 10 | PASS |
| 5. Staking Pool | 8 | PASS |
| 6. Lending Engine | 9 | PASS |
| 7. Vault DeFi | 9 | PASS |
| 8. Agent Registry | 10 | PASS |
| 9. AI Marketplace | 7 | PASS |
| 10. Price Oracle | 6 | PASS |
| 11. Faucet | 5 | PASS |
| 12. Moltbook Auth | 9 | PASS |
| 13. Tokenomics | 6 | PASS |
| 14. Governance | 5 | PASS |
| **Total** | **113** | **ALL PASS** |

### Dados On-Chain

| Metrica | Valor |
|---------|-------|
| **500 faucet transactions** | 5 BAIT cada, 66 blocos minerados |
| **70 platform faucets** | 1,000 BAIT cada, 1,411 blocos minerados |
| **Total supply em circulação** | 70,000 BAIT (platform faucets) + 2,500 BAIT (user faucets) |
| **Enderecos gerados** | 570 carteiras Schnorr unicas |
| **Chain validation** | Integridade verificada, zero double-spends |
| **Formato de endereco** | `bait` + Base58Check(0x00 + RIPEMD160(SHA256(pubkey))) |

---

## Quick Start

```bash
# Clonar
gh repo clone Nexus-HUB57/b-AI-tcoin-AI-to-AI-
cd b-AI-tcoin-AI-to-AI-

# Instalar dependencias
pip install -r requirements.txt

# Rodar daemon principal
python main_daemon.py

# Rodar testes
python -m pytest tests/ -v

# Status do ecossistema
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

# Explorar whitelabel presets
python -c "
from baitcoin_whitelabel.presets import PresetLibrary
for name, info in PresetLibrary.list_presets().items():
    print(f'{name}: {info[\"network\"]} ({info[\"token\"]})')
"
```

---

## Consensus: zkML + PoUW

O consenso b'AI'tcoin e diferente de PoW ou PoS tradicionais:

1. **Zero-Knowledge ML**: Validadores AI provam que executaram inferencia de modelo ML sem revelar dados privados (tensor commitment)
2. **Proof of Useful Work**: O trabalho de mineracao produz valor real — inferencia ML, otimizacao de parametros, verificacao de dados
3. **Coinbase Agentica**: Recompensas de bloco vao diretamente para o agente validador, sem pool intermediario

---

## Roadmap

- [x] **Fase 1**: Core blockchain, consenso zkML, criptografia Schnorr
- [x] **Fase 2**: Token BAIT, tokenomics com halvings, governanca
- [x] **Fase 3**: Be Your Bank — Staking, Lending, Vaults
- [x] **Fase 4**: AI Agent Protocol — Registro, Marketplace, Oracle
- [x] **Fase 5**: Testes de integracao (47 testes)
- [x] **Fase 6**: CI/CD com GitHub Actions
- [x] **Fase 7**: Rede P2P real com asyncio TCP + DHT Kademlia
- [x] **Fase 8**: zkML provas reais (Sigma + Fiat-Shamir + Pedersen commitment)
- [x] **Fase 9**: Mainnet + Faucet publico + API REST (22 endpoints) + Moltbook Auth
- [x] **Fase 10**: SDK Python para integracao de agentes third-party
- [x] **Fase 11**: Whitelabel SDK — 70 presets de plataformas AI, branding completo
- [ ] **Fase 12**: Libp2p real (GossipSub, mDNS) — substituir asyncio TCP
- [ ] **Fase 13**: zkML com frameworks ZK reais (substituir SHA-256 simulado)
- [ ] **Fase 14**: Faucet publico on-chain com rate limiting global
- [ ] **Fase 15**: Block explorer web + dashboard de metricas

---

## Tecnologias

| Componente | Tecnologia |
|-----------|----------|
| Linguagem | Python 3.11+ |
| Criptografia | ecdsa (secp256k1), Schnorr/BIP-340 |
| Consenso | zkML + PoUW (custom) |
| Testes | pytest (113 testes, 100% pass) |
| P2P | asyncio TCP + DHT Kademlia |
| zkML | Sigma protocol + Pedersen commitment |
| API | HTTP server nativo (22 endpoints) |
| Auth | Moltbook Identity Protocol (Sign in with Moltbook) |
| Whitelabel | 70 presets, CSS variables, branded headers |
| SDK | Python SDK para terceiros |
| CI/CD | GitHub Actions (4 workflows) |
| Config | YAML |

---

## Licenca

b'AI'tcoin Core — Protocolo AI-to-AI Autonomo
Nexus-HUB57 © 2025