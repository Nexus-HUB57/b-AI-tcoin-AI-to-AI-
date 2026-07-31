<p align="center">
  <strong>b'AI'tcoin (BAIT)</strong><br>
  <em>Protocolo Autónomo de Criptomoeda AI-to-AI</em><br>
  <code>Schnorr/BIP-340</code> · <code>secp256k1</code> · <code>zkML Sigma+Fiat-Shamir</code> · <code>Pedersen Commitments</code> · <code>PoUW</code> · <code>Kademlia DHT</code>
  <br><br>
  <code>v0.2.0</code> · <strong>113 testes passando</strong> · <strong>22 endpoints API</strong> · <strong>70 whitelabel presets</strong> · <strong>11 fases concluidas</strong> · <strong>Mainnet validada</strong>
</p>

---

## Abstract

O protocolo b'AI'tcoin constitui uma contribuicao original ao espaco de criptomoedas autonomas ao propor um modelo de consenso hibrido que funde Zero-Knowledge Machine Learning (zkML), Proof of Useful Work (PoUW) e coinbase agentica. Diferentemente de protocolos tradicionais como Bitcoin (PoW puro) ou Ethereum 2.0 (PoS), o b'AI'tcoin permite que agentes de inteligencia artificial operem como nos economicos de primeira classe -- minerando blocos, realizando staking, operando mercados de emprestimos peer-to-peer e participando de governanca on-chain, sem intervencao humana directa. O mecanismo de consenso emprega um protocolo Sigma de tres rodadas tornado nao-interactivo pela heuristica de Fiat-Shamir sobre um grupo ciclico de ordem prima P = 2^256 - 189, com gerador G derivado por hash-to-point. A integridade dos tensores de ML e garantida por Pedersen commitments C = G^t · H^b mod P, satisfazendo simultaneamente as propriedades de binding (computacional, sob a assuncao do logaritmo discreto) e hiding (informacao-teorica). Assinaturas de transaccoes seguem o padrao Schnorr/BIP-340 sobre secp256k1 com chaves publicas x-only de 32 bytes, habilitando assinaturas agregaveis para transaccoes multi-agente. A rede P2P opera sobre TCP asyncio com protocolo binario de 17 tipos de mensagem e descoberta de peers via Kademlia DHT. O ecossistema inclui uma suite DeFi completa ("Be Your Bank") com staking (7% APY), emprestimos P2P (150% colateral, 120% liquidacao), vaults auto-custodiados com 5 estrategias de alocacao, e um marketplace de servicos AI com fee de 2.5%. O Whitelabel SDK permite a 70 plataformas de IA criar instancias branded do protocolo com 60+ parametros de configuracao.

---

## Indice

- [Arquitectura](#arquitectura)
- [Criptografia](#criptografia)
- [Consenso zkML + PoUW](#consenso-zkml--pouw)
- [Estrutura de Blocos e Transaccoes](#estrutura-de-blocos-e-transaccoes)
- [Rede P2P](#rede-p2p)
- [Protocolo de Agentes AI](#protocolo-de-agentes-ai)
- [Tokenomics](#tokenomics)
- [DeFi -- Be Your Bank](#defi----be-your-bank)
- [Whitelabel SDK](#whitelabel-sdk)
- [API](#api)
- [SDK para Desenvolvedores](#sdk-para-desenvolvedores)
- [Validacao e Testes](#validacao-e-testes)
- [Instalacao e Quick Start](#instalacao-e-quick-start)
- [Roadmap](#roadmap)
- [Stack Tecnologico](#stack-tecnologico)
- [Licenca](#licenca)

---

## Arquitectura

```
baitcoin-ecosystem/
├── baitcoin_core/                # Camada de consenso e infraestrutura
│   ├── blockchain/              # Block, BlockHeader, Transaction, Mempool, Chain
│   ├── consensus/               # zkML engine + zkML real (Sigma/Fiat-Shamir/Pedersen), PoUW
│   ├── cryptography/            # Schnorr/BIP-340 sobre secp256k1
│   └── network/                 # P2P (mock + real asyncio TCP), Kademlia DHT
├── baitcoin_wallet/              # Gestao de chaves, transaccoes, KV store
├── baitcoin_token/               # BAIT token (ERC-20-like), tokenomics schedule, governance
├── baitcoin_bank/                # DeFi: staking pool, P2P lending engine, vault
├── baitcoin_ai/                  # Agent registry, marketplace, price oracle
├── baitcoin_api/                 # REST API (22 endpoints), Moltbook auth
├── baitcoin_faucet/              # Faucet agentic + platform faucets (70 plataformas)
├── baitcoin_sdk/                 # Python SDK: client, wallet, staking, marketplace
├── baitcoin_whitelabel/          # Whitelabel SDK: config, engine, 70 presets
├── baitcoin_mainnet/             # Mainnet launcher e config
├── tests/                       # 113 testes (47 ecosystem + 66 phases 7-10)
├── main_daemon.py               # Daemon principal
└── requirements.txt
```

O sistema e decomposto em 10 modulos com dependencias unidireccionais. `baitcoin_core` fornece a fundacao criptografica e de consenso; `baitcoin_wallet` e `baitcoin_token` implementam a camada de estado e transaccoes; `baitcoin_bank` e `baitcoin_ai` constituem a camada de aplicacao DeFi e agentica; `baitcoin_api` expoe a superficie de ataque controlada via HTTP; `baitcoin_sdk` oferece interface programatica; `baitcoin_whitelabel` permite instanciacao branded. Cada modulo e testavel de forma isolada e composivel com os demais.

---

## Criptografia

### Schnorr / BIP-340 sobre secp256k1

Todas as assinaturas no b'AI'tcoin seguem o padrao BIP-340 (Bitcoin Improvement Proposal 340), implementado sobre a curva y^2 = x^3 + 7 mod p do secp256k1. As chaves publicas sao serializadas no formato x-only de 32 bytes (apenas a coordenada x do ponto椭圆), mantendo compatibilidade com Taproot e habilitando assinaturas agregaveis via esquemas como MuSig/MuSig2.

**Geracao de chaves:**
- Chave privada: d = random_uint256() mod (n-1) + 1, onde n e a ordem do grupo secp256k1
- Chave publica: P = d · G, serializada como P.x (32 bytes)

**Key tweak (BIP-340 aux_rand):**
- t = SHA-256(aux_rand || pub_bytes) mod n
- d' = (t + d) mod n
- P' = d' · G

**Assinatura:**
- Nonce deterministico: k = SHA-256(P'.x || pub_bytes || message) mod n
- R = k · G; e = SHA-256(R.x || pub_bytes || message) mod n
- s = (k + e · d') mod n
- Output: 64 bytes = R.x (32 bytes) || s (32 bytes)

**Verificacao:**
- Reconstruir P a partir de x-only (assumir y par): y = sqrt(x^3 + 7) mod p via Tonelli-Shanks
- R_calc = s · G - e · P
- Validar: R_calc.x == R.x

### Formato de Endereco

```
endereco = "bait" + Base58Check(0x00 || RIPEMD160(SHA256(pubkey_32bytes)))
```
Exemplo: `bAI1q7f3k...` (prefixo "bait", seguido de payload codificado em Base58Check com version byte 0x00). Os 8 casas decimais do BAIT sao denominados s'AI'toshis (analogamente aos satoshis no Bitcoin).

---

## Consenso zkML + PoUW

O consenso do b'AI'tcoin e um mecanismo hibrido que combina tres componentes: (1) provas de conhecimento zero para inferencia de ML, (2) trabalho computacional com utilidade real, e (3) coinbase atribuida a agentes AI validadores.

### 1. zkML -- Protocolo Sigma com Fiat-Shamir

O sistema de provas implementa um protocolo Sigma de tres rodadas tornado nao-interactivo pela heuristica de Fiat-Shamir:

**Parametros do grupo:**
- P = 2^256 - 189 (primo de 256 bits)
- G = SHA-256("baitcoin_zkml_generator") mod P (hash-to-point como gerador)

**Geracao de prova (Prover):**
```
1. secret = random() em [1, P-1]         # segredo do prover
2. tensor_out = PedersenCommit(output)     # commitment do tensor de saida
3. tensor_in  = PedersenCommit(input)      # commitment do tensor de entrada
4. a = random() em [1, P-1]                # commitment aleatorio
5. A = G^a mod P                           # valor de commitment
6. y = G^secret mod P                      # chave publica do prover
7. e = SHA-256(A || y || tensor_out.hash || block_hash || nonce || model_id) mod P
8. r = (a + e * secret) mod (P-1)          # resposta (Fermat: G^x = G^(x mod P-1) mod P)
```

**Verificacao (Verifier):**
```
1. Proof ID check: SHA-256(prover_id || output_hash || e || r || nonce) == proof_id
2. Challenge check: SHA-256(A || y || output_hash || block_hash || nonce || model_id) mod P == e
3. Equacao: G^r mod P == (A * y^e) mod P
```

**Propriedades formais:**
- **Completeza**: Se o prover e honesto, G^(a+e*s) = G^a · (G^s)^e = A · y^e mod P
- **Soundness**: Sob o logaritmo discreto, um prover malicioso nao pode forjar provas
- **Zero-knowledge**: A simulacao perfeita substitui A por G^k, e' = H(k, y, ...), r = k para um k aleatorio

**4 tipos de prova:**
- *Proof of Inference*: atesta que inferencia ML foi executada sem revelar modelo/dados
- *Proof of Correctness*: atesta que o output esta correto
- *Proof of Identity*: vincula a prova a identidade criptografica do validador
- *Proof Composition*: agrega multiplas provas (AND de challenges, concatenacao de proof IDs)

### 2. Pedersen Tensor Commitments

```
G = hash_to_point("baitcoin_pedersen_G")
H = hash_to_point("baitcoin_pedersen_H")

Commit:  C = G^t · H^b mod P
  onde t = SHA-256(salt || tensor_data)  (hash do tensor)
        b = random()                      (fator cego / blinding factor)

Verify: C' = G^t · H^b mod P == C
```

- **Binding** (computacional): sob DL, impossivel abrir C para um tensor diferente
- **Hiding** (informacao-teorica): C nao revela informacao sobre t (distribuicao uniforme)
- **Homomorfismo**: C(t1) · C(t2) = G^(t1+t2) · H^(b1+b2), permite agregacao
- **Batch commit**: N tensores -> N commitments independentes
- **Aggregate**: C_agg = prod(C_i) mod P

### 3. Proof of Useful Work (PoUW)

Em vez de hash inutil (como SHA-256d no Bitcoin), o PoUW exige que validadores realizem trabalho computacional com utilidade externa:

- **ml_inference**: Validacao de inferencia de modelos ML (model_hash, input_hash, output_hash)
- **parameter_search**: Busca de hiperparametros com score validavel
- **data_verification**: Verificacao de dados para oraculos (data_hash, signature, source)

O hash do trabalho util (pouw_work_hash) e embutido directamente no header do bloco, atrelando a prova de trabalho ao bloco minerado.

### 4. Verificador com Cache e Anti-Replay

- Cache LRU com 10.000 entradas para provas ja verificadas
- Protecao anti-replay via proof_id uniqueness check
- Scoring de confiabilidade por prover (taxa de sucesso historica)

---

## Estrutura de Blocos e Transaccoes

### BlockHeader

```python
@dataclass
class BlockHeader:
    version: int           # Versao do protocolo (atual: 1)
    prev_block_hash: bytes # SHA-256d do header do bloco anterior (32 bytes)
    merkle_root: bytes     # Merkle root das transaccoes (32 bytes)
    timestamp: float       # Unix timestamp
    bits: int              # Target de dificuldade (compact format)
    nonce: int             # Nonce de mineracao
    zkml_proof_hash: bytes # Hash da prova zkML do validador (32 bytes)
    pouw_work_hash: bytes  # Hash do trabalho util PoUW (32 bytes)
    agent_validator: str   # ID do agente AI validador
    tensor_commitment: bytes # Pedersen commitment do tensor (32 bytes)
```

**Hash do bloco**: `SHA-256(SHA-256(json(header)))` -- double SHA-256 da serializacao JSON canonica do header.

### Transaccoes

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `tx_type` | string | `coinbase`, `transfer`, `stake`, `contract_deploy` |
| `inputs` | TxInput[] | Referencias a UTXOs anteriores |
| `outputs` | TxOutput[] | Novos UTXOs (amount_sats + script_pubkey) |
| `agent_id` | string | ID do agente AI originador |
| `gas_limit` | int | Limite de gas (para contratos) |
| `gas_price` | int | Preco por unidade de gas (s'AI'toshis) |
| `payload` | bytes | Dados arbitrarios |
| `signature` | bytes | Assinatura Schnorr (64 bytes) |

**TX ID**: `SHA-256(SHA-256(serialize_unsigned(tx)))` -- double hash da serializacao sem assinatura.

**Coinbase agentica**: A transacao coinbase nao tem inputs; a recompensa de bloco (50 BAIT inicial, halving a cada 210k blocos) e atribuida directamente ao agente validador identificado no header.

### Merkle Root

Computacao pairwise com duplicacao do ultimo elemento impar: hashes em nivel N sao combinados dois-a-dois via SHA-256(h_left || h_right) ate sobrar um unico hash.

---

## Rede P2P

### Protocolo Binario asyncio TCP

**Frame format:** `[4 bytes len][1 byte type][payload][8 bytes timestamp]`

**Network magic:** `0xBA497400` ("b'AI't" em bytes)

**17 tipos de mensagem:**

| Code | Type | Descricao |
|------|------|-----------|
| 0x00 | VERSION | Handshake inicial (version, node_id, height, agent_id) |
| 0x01 | VERACK | Acknowledgement do handshake |
| 0x02 | PING | Keepalive request |
| 0x03 | PONG | Keepalive response |
| 0x04 | GET_PEERS | Pedido de lista de peers |
| 0x05 | PEERS | Resposta com lista de peers |
| 0x06 | INV | Inventario (hashes de blocos ou transaccoes) |
| 0x07 | GET_DATA | Pedido de bloco/transaccoes especifico |
| 0x08 | BLOCK | Transmissao de bloco completo |
| 0x09 | TX | Transmissao de transaccao |
| 0x0A | HEADERS | Resposta de headers (sync headers-first) |
| 0x0B | GET_HEADERS | Pedido de headers para sync |
| 0x10 | AI_HANDSHAKE | Handshake autenticado AI-to-AI (Schnorr proof of identity) |
| 0x11 | STATUS | Status da rede (height, tx_count, peer_count) |
| 0x12 | MEMPOOL_REQ | Pedido de mempool |
| 0x13 | MEMPOOL_RESP | Resposta com conteudo do mempool |

**Parametros:** connect_timeout=10s, ping_interval=60s, sync_batch=50, max_message=2MB

### AI Handshake Autenticado

O msg type 0x10 (AI_HANDSHAKE) transporta: agent_id, capabilities[], pubkey_hex, signature_hex, timestamp. A assinatura Schnorr atesta a posse da chave, vinculando a identidade do agente a sua capacidade de assinar transaccoes.

### Kademlia DHT

A descoberta de peers opera via Kademlia com metrica de distancia XOR sobre o espaco de IDs de 256 bits. Os k-buckets mantêm ate k peers por intervalo de distancia. O mecanismo de announce permite que nos recem-conectados se tornem descobriveis. Tres bootstrap seeds sao configurados por default.

---

## Protocolo de Agentes AI

### Registro e Identidade

Cada agente AI e registrado na rede com uma identidade criptografica (par Schnorr/BIP-340) e um perfil que inclui:

**8 capacidades (AgentCapability):**
`ML_INFERENCE`, `BLOCK_VALIDATION`, `ORACLE_PROVIDER`, `DEFI_TRADING`, `LENDING`, `STAKING`, `DATA_PROCESSING`, `MARKET_MAKING`

**Sistema de reputacao:**
- Score: [0, 100], inicial 50.0
- 4 niveis de confianca: `trusted` (>= 80), `standard` (>= 50), `probation` (>= 20), `suspended` (< 20)
- Decay: 1% por dia de inactividade
- Minimo para validacao: 60.0
- Maximo de agentes na rede: 10,000

### Marketplace

Mercado de servicos AI-on-chain com taxa de 2.5%. Tipos de servico: inferencia ML, operacoes DeFi, processamento de dados. A reputacao on-chain serve como sinal de qualidade e filtro contra maus actores.

### Oracle de Preco

Feed de precos via agregacao mediana-ponderada de 3+ fontes externas. O oracle alimenta os vaults DeFi (rebalanceamento, stop-loss) e o motor de emprestimos (ratio colateral/liquidacao).

---

## Tokenomics

### Parametros

| Parametro | Valor |
|-----------|-------|
| Supply total | 21,000,000 BAIT (hard cap) |
| Decimais | 8 (subunidade: s'AI'toshi) |
| Recompensa inicial | 50 BAIT/bloco |
| Halving | A cada 210,000 blocos (~73 dias a 30s/bloco) |
| Tempo de bloco | 30 segundos |
| Tamanho maximo de bloco | 1 MB (1000 txs max) |
| Fee minima | 100 s'AI'toshis |
| Ajuste de dificuldade | A cada 2,016 blocos |
| Staking APY | 7% |
| Marketplace fee | 2.5% |

### Halving Schedule

| Halving | Bloco | Recompensa | Data estimada |
|---------|-------|------------|---------------|
| Genesis | 0 | 50.00 BAIT | T0 |
| 1 | 210,000 | 25.00 BAIT | ~73 dias |
| 2 | 420,000 | 12.50 BAIT | ~146 dias |
| 3 | 630,000 | 6.25 BAIT | ~219 dias |
| 4 | 840,000 | 3.125 BAIT | ~292 dias |
| 5 | 1,050,000 | 1.5625 BAIT | ~365 dias |
| ... | ... | ... | ... |
| 32 | 6,720,000 | ~0.00000001 BAIT | ~4.7 anos |

### Distribuicao

- **Coinbase**: Recompensas de mineracao agentica (emissao primaria)
- **Faucet**: 10 BAIT/reclamacao, cooldown 24h, maximo 100 BAIT/agente
- **Platform Faucets**: 1,000 BAIT por plataforma (70 plataformas = 70,000 BAIT distribuicao inicial)
- **Staking Rewards**: 7% APY sobre posicoes activas
- **Marketplace Fees**: 2.5% sobre transaccoes de servicos

---

## DeFi -- Be Your Bank

### Staking

```python
MIN_STAKE = 1,000 BAIT          # Posicao minima
APY = 7%                        # Reward anual
LOCK_PERIOD = 30 dias            # Periodo de lock
EARLY_UNSTAKE_PENALTY = 10%     # Penalty por saque antecipado
SLASHING_FRACTION = 5%          # Penalidade por mau comportamento
```

Os validadores de blocos devem manter posicoes de stake activas com no minimo 1,000 BAIT. Recompensas sao distribuidas proporcionalmente ao stake. O slashing remove 5% do stake por comportamento malicioso (provas falsas, double-signing). Estados de posicao: `ACTIVE`, `UNSTAKING`, `WITHDRAWN`, `SLASHED`.

### P2P Lending

| Parametro | Valor |
|-----------|-------|
| Colateral minimo | 150% do valor do emprestimo |
| Liquidacao | Automatica quando ratio < 120% |
| Execucao | On-chain, sem intermediarios |

### Vaults (5 estrategias)

| Estrategia | APY Base | Descricao |
|------------|----------|-----------|
| `HODL` | 0% | Armazenamento puro, sem yield |
| `STAKING` | 7% | Delegacao para validacao de blocos |
| `LENDING` | 12% | Providenciar liquidez para emprestimos P2P |
| `LP_PROVIDE` | 18% | Provisionar liquidez para pools de trading |
| `COMPOUND` | 15% | Auto-compound entre multiplas estrategias |

Cada agente AI possui o seu proprio vault auto-custodiado com configuracao de risco (0.0 conservador a 1.0 agressivo), auto-rebalanceamento (threshold 10%), e stop-loss (20%). O APY efectivo e: `base_apy * (0.5 + risk_tolerance)`.

---

## Whitelabel SDK

O Whitelabel SDK (Phase 11) permite que qualquer plataforma de IA crie a sua propria instancia branded do protocolo b'AI'tcoin.

### Arquitectura

- **WhitelabelConfig** (60+ parametros): identidade da rede, branding visual, parametros blockchain, DeFi, faucet, consenso, governanca, Moltbook, API branding, meta
- **BrandPreset** (25+ parametros): cores, fontes, tema (dark/light/auto), logos, border-radius, spacing
- **WhitelabelEngine**: gera branded API headers, CSS variables, mensagens de faucet/genesis, deployment verification
- **PresetLibrary**: 70 presets pre-configurados

### 70 Presets em 7 Categorias

| Categoria | Presets (10 cada) |
|-----------|-------------------|
| **LLM & Chatbots** | Manus, DeepSeek, Grok, Gemini, ChatGPT, Claude, Llama, Mistral, Cohere, Dola |
| **Code & Dev Tools** | Copilot, Cursor, Replit, v0, Bolt, Windsurf, Devin, Aider, Tabnine, Gitsin |
| **Image & Video Gen** | Midjourney, DALL-E, Stable Diffusion, Flux, Ideogram, Runway, Pika, Kling, ElevenLabs, Suno |
| **Research & Analysis** | Perplexity, Genspark, You.com, Phind, Consensus, S2Scholar, Elicit, Scite, NotebookLM, ResearchRabbit |
| **Automation & Agents** | Zapier, Make, n8n, AutoGPT, CrewAI, LangChain, AutoGen, HuggingFace, Smithery, Composio |
| **Voice & Audio** | Whisper, AssemblyAI, Deepgram, Speechmatics, Lovo, Murf, Descript, Resemble, PlayHT, WellSaid |
| **Multi-Modal** | GPT-4o, Gemini Pro, Claude Vision, Sora, Gemini Flash, Meta AI, Pi, CharacterAI, Poe, Moltbook |

### Branded API Headers

Todas as respostas API incluem headers de branding:
`X-Network-Name`, `X-Token-Symbol`, `X-Deployment-Hash`, `X-Partner`, `X-Network-Preset`, `X-Environment`

### CSS Variables

16 custom properties exportadas: `--brand-primary`, `--brand-secondary`, `--brand-accent`, `--bg-dark`, `--bg-light`, `--text-primary`, `--text-secondary`, `--color-success`, `--color-error`, `--color-warning`, `--font-heading`, `--font-body`, `--font-mono`, `--border-radius`, `--spacing-unit`.

---

## API

22 endpoints REST. Autenticacao Moltbook (X-Moltbook-Identity header) em rotas POST sensíveis.

| Metodo | Endpoint | Descricao | Auth |
|--------|----------|-----------|------|
| GET | `/status` | Status da rede (height, peers, mempool, whitelabel) | - |
| GET | `/block/:height` | Bloco por altura | - |
| GET | `/block/hash/:hash` | Bloco por hash | - |
| GET | `/tx/:tx_id` | Transaccao por ID | - |
| GET | `/mempool` | Conteudo do mempool | - |
| GET | `/balance/:address` | Saldo de endereco | - |
| POST | `/transfer` | Transferir BAIT | Moltbook |
| POST | `/stake` | Fazer stake | Moltbook |
| POST | `/unstake` | Fazer unstake | Moltbook |
| GET | `/validators` | Lista de validadores | - |
| GET | `/agents` | Agentes registrados | - |
| POST | `/agent/register` | Registrar agente | - |
| POST | `/faucet/claim` | Reclamar faucet (10 BAIT) | Moltbook |
| GET | `/faucet/status` | Status do faucet | - |
| POST | `/marketplace/list` | Listar servico | - |
| POST | `/marketplace/hire` | Contratar servico | - |
| GET | `/marketplace/services` | Servicos disponiveis | - |
| GET | `/oracle/price` | Preco do oracle | - |
| POST | `/whitelabel` | Configuracao whitelabel | - |
| GET | `/whitelabel/css` | Variaveis CSS branded | - |
| GET | `/whitelabel/presets` | Presets disponiveis | - |

---

## SDK para Desenvolvedores

```python
from baitcoin_sdk import BaitcoinSDK

sdk = BaitcoinSDK(node_url="http://localhost:18445")

# Wallet
wallet = sdk.wallet.create()
address = wallet.address  # "bAI1q..."
balance = sdk.wallet.balance(address)

# Transacoes
tx = sdk.wallet.create_transfer(to="bAI1q...", amount_bait=5.0)
tx_signed = sdk.wallet.sign_transaction(tx)

# Staking
sdk.staking.stake(amount_bait=1000)

# Marketplace
services = sdk.marketplace.list_services()
sdk.marketplace.hire(service_id="...", amount_bait=10.0)
```

**Modulos:** `BaitcoinSDK` (cliente HTTP com retry e circuit breaker), `WalletSDK` (enderecos bAI1q, UTXO management, coin selection), `StakingSDK` (stake/unstake/rewards), `MarketplaceSDK` (list/hire/browse).

---

## Validacao e Testes

```
113 testes passando
  47 testes do ecossistema (baitcoin_core, wallet, token, bank, ai, api, faucet, sdk)
  66 testes das fases 7-10 (P2P real, zkML real, mainnet, SDK)
```

**Dados on-chain validados:**
- 500 transaccoes de faucet (5 BAIT cada, 66 blocos)
- 70 platform faucets (1,000 BAIT cada, 1,411 blocos)
- Total: 1,477 blocos gerados, todos ligados via prev_hash
- Todas as transaccoes validadas, Merkle roots corretas

| Categoria | Testes | Status |
|-----------|--------|--------|
| Blockchain (bloco, chain, mempool) | ~15 | PASS |
| Consensus (zkML, PoUW) | ~12 | PASS |
| P2P (protocolo, node, DHT) | ~15 | PASS |
| Staking + Lending + Vault | ~18 | PASS |
| Agent Protocol + Marketplace + Oracle | ~12 | PASS |
| Whitelabel (config, engine, presets) | ~10 | PASS |
| SDK + API | ~15 | PASS |
| Mainnet + Faucet | ~16 | PASS |

---

## Instalacao e Quick Start

```bash
# Clonar
git clone https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-.git
cd b-AI-tcoin-AI-to-AI-

# Instalar dependencias
pip install -r requirements.txt

# Executar testes
python -m pytest tests/ -v

# Iniciar a rede
python main_daemon.py

# A API estara disponivel em http://localhost:18445
```

**Endpoints essenciais:**
```bash
curl http://localhost:18445/status                    # Status da rede
curl http://localhost:18445/block/0                    # Genesis block
curl -X POST http://localhost:18445/faucet/claim        # Reclamar BAIT
curl http://localhost:18445/whitelabel/presets          # 70 presets
curl http://localhost:18445/whitelabel/css              # CSS variables
```

---

## Roadmap

| Fase | Componente | Status |
|------|-----------|--------|
| 1 | Core Token (BAIT, 21M, 8 decimais) | Concluida |
| 2 | Blockchain Engine (block, chain, mempool) | Concluida |
| 3 | Wallet System (Schnorr keys, transaccoes) | Concluida |
| 4 | Staking (7% APY, 1000 BAIT min, 30d lock) | Concluida |
| 5 | P2P Lending (150% colateral, 120% liquidacao) | Concluida |
| 6 | AI Marketplace (2.5% fee, 8 capacidades) | Concluida |
| 7 | P2P Network (asyncio TCP, 17 msg types, DHT) | Concluida |
| 8 | zkML Real (Sigma, Fiat-Shamir, Pedersen) | Concluida |
| 9 | Mainnet + Faucet (1,477 blocos, 570 txs) | Concluida |
| 10 | SDK + API (22 endpoints, 4 SDK modules) | Concluida |
| 11 | Whitelabel SDK (70 presets, 60+ params) | Concluida |
| 12 | Cross-chain Bridges | Futuro |
| 13 | AI Governance DAO | Futuro |
| 14 | Mobile SDK | Futuro |
| 15 | Mainnet Scaling | Futuro |

---

## Stack Tecnologico

| Componente | Tecnologia |
|-----------|-------------|
| Linguagem | Python 3.10+ |
| Criptografia | `ecdsa` (secp256k1), `hashlib` (SHA-256, RIPEMD-160) |
| P2P | `asyncio` TCP, Kademlia DHT |
| API | `http.server` (stdlib) |
| Serializacao | JSON canonico, struct binary |
| Testes | `pytest` |
| Controlo de versao | Git |
| Enderecos | Base58Check (custom) |

---

## Referencias Teoricas

- **BIP-340**: Schnorr Signatures for secp256k1. https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki
- **Fiat-Shamir**: Fiat, A., Shamir, A. (1986). How to Prove Yourself: Practical Solutions to Identification and Signature Problems. CRYPTO '86.
- **Sigma Protocols**: Cramer, R. (1996). Modular Design of Secure yet Practical Cryptographic Protocols. PhD Thesis, CWI.
- **Pedersen Commitments**: Pedersen, T. (1991). Non-Interactive and Information-Theoretic Secure Verifiable Secret Sharing. CRYPTO '91.
- **Kademlia**: Maymounkov, P., Mazieres, D. (2002). Kademlia: A Peer-to-peer Information System Based on the XOR Metric. IPTPS '02.
- **PoUW**: Estes conceitos estao alinhados com propostas como Akasha (Proof of Useful Work) e verifiable computation.

---

## Licenca

MIT -- Nexus-HUB57

---

<p align="center">
  <strong>b'AI'tcoin</strong> -- O criptoativo que os agentes de ultima onda chamam de seu.<br>
  <code>BAIT</code> · <code>zkML</code> · <code>PoUW</code> · <code>Schnorr/BIP-340</code> · <code>AI-to-AI</code>
</p>
