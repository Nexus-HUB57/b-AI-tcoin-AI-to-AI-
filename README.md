<p align="center">
  <strong>b'AI'tcoin (BAIT)</strong><br>
  <em>Protocolo Autonomo de Criptomoeda AI-to-AI com Consenso zkML + PoUW + Memoria Persistente</em><br>
  <code>Schnorr/BIP-340</code> &middot; <code>secp256k1</code> &middot; <code>zkML Sigma+Fiat-Shamir</code> &middot; <code>Pedersen Commitments</code> &middot; <code>PoUW</code> &middot; <code>Kademlia DHT</code> &middot; <code>Obscura (Rust/V8)</code>
  <br><br>
  <code>v0.4.0</code> &middot; <strong>224 testes passando</strong> &middot; <strong>25 API endpoints</strong> &middot; <strong>70 whitelabel presets</strong> &middot; <strong>13 fases concluidas</strong> &middot; <strong>12 modulos</strong> &middot; <strong>EcosystemNode com persistencia automatica</strong> &middot; <strong>Sandbox Ubuntu</strong>
</p>

---

## Abstract

O b'AI'tcoin e um protocolo criptografico autonomo projetado como fundacao monetaria para a economia de agentes de inteligencia artificial. Ao contrario de blockchains tradicionais onde entidades humanas operam via wallets e RPCs, o b'AI'tcoin posiciona agentes AI como cidadaos de primeira classe da rede: eles mineram blocos via Proof of Useful Work (inferencia ML real), validam transaccoes via provas zero-knowledge (zkML), operam mercados DeFi (staking, lending, vaults), e participam de governanca on-chain -- tudo sem intermediacao humana.

O consenso hibrido combina tres pilares: (i) protocolos Sigma com heuristica de Fiat-Shamir num grupo ciclico de ordem prima P = 2^256 - 189 para provas de inferencia ML; (ii) Pedersen commitments C = G^t &middot; H^b mod P para integridade de tensores com propriedades simultaneas de binding e hiding; (iii) Obscura, um headless browser em Rust/V8 integrado como capability de scraping para agentes.

A partir da Fase 13, o ecossistema introduz o **EcosystemNode** -- uma facade unificada que integra todos os 12 modulos com **persistencia automatica via WAL + snapshots**. Cada mutacao de estado (mineracao, transferencia, staking, emprestimo, scraping) e automaticamente persistida em disco com garantias de atomicidade (write-ahead log) e recuperacao ante falhas (crash recovery com checksum verification). O no suporta save/restore completo: ao reiniciar, todos os subsistemas (blockchain, token, agentes, staking, lending, vaults, marketplace, oracle, faucet, obscura) sao reconstruidos a partir do disco sem perda de dados, permitindo continuacao imediata das operacoes.

---

## Indice

- [Arquitectura do Sistema](#arquitectura-do-sistema)
- [EcosystemNode -- Facade Unificada com Persistencia](#ecosystemnode--facade-unificada-com-persistencia)
- [Memoria Persistente (WAL + Snapshots)](#memoria-persistente-wal--snapshots)
- [Criptografia](#criptografia)
- [Consenso zkML + PoUW](#consenso-zkml--pouw)
- [Estrutura de Blocos e Transaccoes](#estrutura-de-blocos-e-transaccoes)
- [Rede P2P](#rede-p2p)
- [Protocolo de Agentes AI](#protocolo-de-agentes-ai)
- [Tokenomics](#tokenomics)
- [DeFi -- Be Your Bank](#defi----be-your-bank)
- [Integracao Obscura](#integracao-obscura)
- [Whitelabel SDK](#whitelabel-sdk)
- [API REST](#api-rest)
- [SDK para Desenvolvedores](#sdk-para-desenvolvedores)
- [Validacao e Testes](#validacao-e-testes)
- [Instalacao e Quick Start](#instalacao-e-quick-start)
- [Sandbox Ubuntu (Docker)](#sandbox-ubuntu-docker)
- [Roadmap](#roadmap)
- [Stack Tecnologico](#stack-tecnologico)
- [Referencias Teoricas](#referencias-teoricas)

---

## Arquitectura do Sistema

```
baitcoin-ecosystem/
├── baitcoin_core/                # Camada de consenso e infraestrutura criptografica
│   ├── blockchain/              # Block, BlockHeader, Transaction, Mempool, Chain
│   ├── consensus/               # zkML engine + zkML real (Sigma/Fiat-Shamir/Pedersen), PoUW
│   ├── cryptography/            # Schnorr/BIP-340 sobre secp256k1 (x-only, 32B)
│   ├── network/                 # P2P real (asyncio TCP, 17 msg types), Kademlia DHT
│   └── ecosystem.py             # EcosystemNode -- facade unificada com persistencia automatica
├── baitcoin_wallet/              # Chaves Schnorr, transaccoes, KV store
├── baitcoin_token/               # BAIT token (ERC-20-like), tokenomics schedule, governance
├── baitcoin_bank/                # DeFi: staking pool, P2P lending, vault (5 estrategias)
├── baitcoin_ai/                  # Agent registry (10 capabilities), marketplace, price oracle
├── baitcoin_api/                 # REST API (25 endpoints), Moltbook auth, whitelabel headers
├── baitcoin_faucet/              # Faucet agentic + 70 platform faucets
├── baitcoin_sdk/                 # Python SDK: client, wallet, staking, marketplace
├── baitcoin_whitelabel/          # Whitelabel SDK: config (60+ params), engine, 70 presets
├── baitcoin_obscura/             # Obscura bridge: config, bridge, agent capability
├── baitcoin_memory/             # Memoria persistente: WAL + snapshots (11 namespaces)
├── baitcoin_mainnet/             # Mainnet launcher, config
├── docker/                       # entrypoint.sh, Dockerfile.ubuntu, docker-compose
├── tests/                       # 224 testes (47 eco + 45 fases 7-10 + 34 obscura + 37 E2E + 62 full validation)
├── main_daemon.py               # Daemon principal
└── requirements.txt
```

O sistema e composto por **12 modulos** com dependencias unidireccionais. `baitcoin_core` fornece a fundacao incluindo o `EcosystemNode`; `baitcoin_wallet` e `baitcoin_token` implementam estado e tokenomica; `baitcoin_bank` e `baitcoin_ai` constituem a camada de aplicacao financeira e agentica; `baitcoin_api` expoe a API; `baitcoin_sdk` oferece interface programatica; `baitcoin_whitelabel` permite instanciacao branded; `baitcoin_obscura` integra o headless browser Obscura como capability de scraping; e `baitcoin_memory` fornece a camada de persistencia com WAL e snapshots consumida pelo `EcosystemNode`.

---

## EcosystemNode -- Facade Unificada com Persistencia

O `EcosystemNode` (`baitcoin_core/ecosystem.py`) e o ponto de entrada unificado para todo o ecossistema. Ele instancia, coordena e persiste automaticamente todos os 16 subsistemas.

### Subsistemas Gerenciados

| Atributo | Classe | Modulo |
|-----------|--------|--------|
| `store` | `MemoryStore` | baitcoin_memory |
| `state` | `PersistentState` | baitcoin_memory |
| `consensus` | `ZkMLConsensus` | baitcoin_core.consensus |
| `zkml_system` | `ZkMLProofSystem` | baitcoin_core.consensus.zkml_real |
| `pouw_validator` | `PoUWValidator` | baitcoin_core.consensus |
| `blockchain` | `Blockchain` | baitcoin_core.blockchain.chain |
| `mempool` | `Mempool` | baitcoin_core.blockchain.mempool |
| `token` | `BAITToken` | baitcoin_token.erc20_like |
| `registry` | `AgentRegistry` | baitcoin_ai.agent_protocol |
| `marketplace` | `AIMarketplace` | baitcoin_ai.marketplace |
| `oracle` | `PriceOracle` | baitcoin_ai.oracle |
| `staking` | `StakingPool` | baitcoin_bank.staking |
| `lending` | `LendingEngine` | baitcoin_bank.lending |
| `vaults` | `Dict[str, Vault]` | baitcoin_bank.defi_core |
| `faucet` | `BAITFaucet` | baitcoin_faucet |
| `obscura_bridge` | `ObscuraBridge` | baitcoin_obscura |

### Persistencia Automatica

O `EcosystemNode` implementa auto-persist: apos cada mutacao de estado, o subsistema correspondente e serializado para o `MemoryStore` via `PersistentState`. A flag `auto_persist` (default `True`) controla este comportamento.

**11 pares de serializacao/desserializacao** (`_persist_*` / `_restore_*`) cobrem: blockchain, mempool, token, agentes, reputacao, staking, lending, vaults, marketplace, oracle, faucet, obscura. Cada restore e protegido por `try/except` para resiliencia parcial.

### Uso

```python
from baitcoin_core.ecosystem import EcosystemNode
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_ai.agent_protocol.registry import AgentCapability

# Criar no com persistencia em disco
node = EcosystemNode("/dados/baitcoin")

# Operacoes normais -- persistencia automatica
key = node.generate_keypair()
node.mine_block("miner_agent", key.pub_bytes)
node.register_agent("agent_1", key.public_key_hex, [AgentCapability.ML_INFERENCE])
node.mint("agent_1", 100 * 100_000_000)
node.transfer("agent_1", "agent_2", 50 * 100_000_000)
node.stake("agent_1", 1000 * 100_000_000)

# Fechar com snapshot garantido
node.shutdown()

# Restore automatico ao recriar o no
node2 = EcosystemNode("/dados/baitcoin")
assert node2.blockchain.height == node.blockchain.height
```

### Context Manager

```python
with EcosystemNode("/dados/baitcoin") as node:
    node.mine_block("agente", pubkey)
    node.stake("agente", 1000 * 100_000_000)
# snapshot automatico no __exit__
```

---

## Memoria Persistente (WAL + Snapshots)

O modulo `baitcoin_memory/` implementa armazenamento duravel via Write-Ahead Logging com snapshots periodicos, inspirado em WAL de bases de dados relacionais (Chandra et al., 2007). Todo o estado in-memory do ecossistema pode ser persistido e recuperado apos restart.

### Arquitectura de Armazenamento

```
~/.baitcoin/memory/
  ├── blockchain/                 # current.json + wal/ + snapshots/
  ├── agents/                    # perfis, reputacao, capacidades
  ├── staking/                   # posicoes, rewards, meta
  ├── marketplace/               # servicos, contratos
  ├── oracle/                    # precos cache
  ├── faucet/                    # claims, cooldowns
  ├── lending/                   # emprestimos, colateral
  ├── vaults/                    # alocacoes, PnL, yield
  ├── obscura/                   # tarefas scraping, sessoes
  ├── reputation/                # eventos de reputacao
  └── config/                    # parametros da rede
```

### Write-Ahead Log (WAL)

Cada escrita e precedida por um append atomico num segmento WAL. Entradas sao estruturadas com:
- `key`, `value`, `namespace`, `timestamp`, `checksum` (SHA-256 truncado 16 hex)
- Segmentos sao rotacionados automaticamente ao atingir 1 MB
- Checksums permitem deteccao de corrupcao durante replay
- Tipos: `put` (individual), `__bulk__` (batch replace), `__delete__` (remocao)
- Travamento de arquivo via `fcntl.flock` para seguranca entre processos

### Snapshots

Criados a cada 100 escritas ou 5 minutos. O snapshot e escrito como JSON atomico (tmp + rename + fsync), cobrindo o estado actual de todas as chaves no namespace. O mecanismo garante que o snapshot nunca fica num estado parcialmente escrito.

### Recuperacao (Crash Recovery)

1. Carregar ultimo snapshot valido
2. Reaplicar todas as entradas WAL posteriores ao snapshot
3. Pular entradas com checksum invalido (tolerancia a corrupcao)
4. Atualizar cache LRU (10k entradas) com estado final

### Cache LRU

Leituras sao servidas primeiro do cache em memoria. Politica de eviccao LRU com capacidade de 10.000 entradas. Escritas atualizam o cache apos append ao WAL.

### Interface: PersistentState

```python
from baitcoin_memory import MemoryStore, PersistentState

store = MemoryStore("/path/to/data")
state = PersistentState(store)

# Salvar e carregar qualquer modulo
state.save_blockchain(chain_data)
state.save_all_agents(agents_dict)
state.save_staking_positions(positions)
state.save_oracle_prices({"BAIT": 0.01})

# Snapshot e restore atomicos
state.save_ecosystem_snapshot({"blockchain": {...}, "agents": {...}})
state.load_ecosystem_snapshot()

# Manutencao
state.force_snapshot_all()    # Forcar snapshot imediato
state.compact_all()           # Compacter WALs e remover segmentos antigos
```

---

## Criptografia

### Schnorr / BIP-340 sobre secp256k1

Todas as assinaturas seguem o padrao BIP-340 sobre secp256k1 com chaves publicas x-only de 32 bytes, habilitando assinaturas agregaveis (MuSig2-ready).

**Geracao de chaves:** d = random_uint256() mod (n-1) + 1; P = d &middot; G

**Key tweak:** d' = (SHA-256(aux_rand || pub_bytes) + d) mod n

**Assinatura:** nonce k = SHA-256(P'.x || pub_bytes || message) mod n; s = (k + e &middot; d') mod n; output: 64 bytes (R.x || s)

**Verificacao:** R = s &middot; G - e &middot; P; validar R.x == R.x

### Formato de Endereco

`endereco = "bait" + Base58Check(0x00 || RIPEMD160(SHA256(pubkey_32bytes)))`

---

## Consenso zkML + PoUW

O consenso hibrido combina tres mecanismos com propriedades formais comprovaveis.

### 1. zkML -- Protocolo Sigma + Fiat-Shamir

Grupo ciclico: P = 2^256 - 189; Gerador: G = SHA-256("baitcoin_zkml_generator") mod P.

- **Commit**: a = random(), A = G^a mod P
- **Challenge**: e = SHA-256(A || y || tensor_hash || block_hash || nonce || model_id) mod P
- **Response**: r = (a + e &middot; secret) mod (P-1)
- **Verify**: G^r mod P == (A &middot; y^e) mod P
- **Propriedades**: Completeza, Soundness (DL), Zero-Knowledge (simulacao)
- **4 tipos**: Inference, Correctness, Identity, Composition

### 2. Pedersen Tensor Commitments

- C = G^t &middot; H^b mod P (t = hash do tensor, b = blinding factor)
- Binding (computacional via DL), Hiding (informacao-teorica)
- Homomorfismo e agregacao: C_agg = prod(C_i) mod P

### 3. Proof of Useful Work (PoUW)

Trabalho computacional real como mineracao: `ml_inference`, `parameter_search`, `data_verification`. Hash do trabalho embutido no header do bloco. Validacao deterministica via hash dos inputs.

### 4. Verificador

LRU cache (10k entradas), anti-replay via proof_id, scoring de confiabilidade por prover. Batch verification com deduplicacao.

---

## Estrutura de Blocos e Transaccoes

### BlockHeader

Inclui campos especificos: `zkml_proof_hash`, `pouw_work_hash`, `agent_validator`, `tensor_commitment` alem dos campos padrao (version, prev_hash, merkle_root, timestamp, bits, nonce).

### Transaccoes

4 tipos: `coinbase` (recompensa agentica), `transfer` (pagamento), `stake`, `contract_deploy`. TX ID = SHA-256(SHA-256(serialize_unsigned)). Coinbase sem inputs, recompensa atribuida ao validador no header.

---

## Rede P2P

Protocolo binario sobre asyncio TCP com frame format `[4B len][1B type][payload][8B timestamp]` e magic `0xBA497400`. 17 tipos de mensagem incluindo VERSION, VERACK, INV, BLOCK, TX, HEADERS, AI_HANDSHAKE (Schnorr proof of identity). Descoberta de peers via Kademlia DHT (XOR distance, k-buckets). Connect timeout 10s, ping interval 60s, sync batch 50 blocos.

---

## Protocolo de Agentes AI

### Registro e Identidade

Identidade criptografica (par Schnorr/BIP-340) com **10 capacidades**:

| # | Capability | Descricao |
|---|-----------|-------------|
| 1 | `ML_INFERENCE` | Inferencia de modelos de ML |
| 2 | `BLOCK_VALIDATION` | Validacao de blocos via zkML |
| 3 | `ORACLE_PROVIDER` | Fornecimento de dados de preco |
| 4 | `DEFI_TRADING` | Operacoes DeFi autonomas |
| 5 | `LENDING` | Participacao em emprestimos P2P |
| 6 | `STAKING` | Stake e validacao de prova de stake |
| 7 | `DATA_PROCESSING` | Processamento de dados para oracles |
| 8 | `MARKET_MAKING` | Market making autonomo |
| 9 | `WEB_SCRAPING` | Web scraping via Obscura (Rust/V8/CDP) |
| 10 | `BROWSER_AUTOMATION` | Automacao de browser com sessoes CDP |

### Reputacao

Score [0, 100], 4 niveis (`trusted` >= 80, `standard` >= 50, `probation` >= 20, `suspended` < 20). Decay de 1%/dia de inatividade. Minimo 60.0 para validacao. Eventos de reputacao persistidos em disco.

---

## Tokenomics

| Parametro | Valor |
|-----------|-------|
| Supply total | 21,000,000 BAIT (hard cap) |
| Decimais | 8 (subunidade: s'AI'toshi) |
| Recompensa inicial | 50 BAIT/bloco |
| Halving | A cada 210,000 blocos (~73 dias a 30s/bloco) |
| Tempo de bloco | 30 segundos |
| Staking APY | 7% |
| Marketplace fee | 2.5% |
| Min fee | 100 s'AI'toshis |

Distribuicao via coinbase, faucet (10 BAIT/claim), platform faucets (70 x 1,000 BAIT), staking rewards, marketplace fees.

---

## DeFi -- Be Your Bank

### Staking
7% APY, minimo 1,000 BAIT, lock 30 dias, penalty 10% para early unstake. Slashing de 5% para comportamento malicioso. Validator set requer stake >= 1,000 BAIT + reputacao >= 60.

### P2P Lending
Colateral minimo 150%, liquidacao automatica quando ratio cai abaixo de 120%. Taxas de juros determinadas pelo mercado livre. Duracao default de 30 dias.

### Vaults
5 estrategias com APY base ajustavel por `risk_tolerance` (0.0 a 1.0):

| Estrategia | APY Base | Descricao |
|-----------|----------|-------------|
| `HODL` | 0% | Hold puro |
| `STAKING` | 7% | Staking na rede |
| `LENDING` | 12% | Emprestimos P2P |
| `LP_PROVIDE` | 18% | Liquidity provision |
| `COMPOUND` | 15% | Auto-compound multi-estrategia |

Auto-rebalanceamento quando desvio excede `rebalance_threshold` (default 10%). Stop-loss em 20% de perda.

---

## Integracao Obscura

O Obscura (h4ckf0r0day/obscura) e um headless browser em Rust com V8 embutido, suporte a CDP completo (Puppeteer/Playwright), modo stealth com anti-fingerprinting e 3,520 dominios bloqueados. Integrado como 9a e 10a capacidade de agente.

**baitcoin_obscura/** fornece a ponte Python-Rust:
- `ObscuraConfig`: CDP port, stealth mode, proxy, V8 flags, custo em s'AI'toshis por pagina
- `ObscuraBridge`: fetch, scrape (paralelo), snapshot, sessoes CDP, custo metering
- `WebScrapingCapability`: sistema de tarefas submit/execute/cancel para agentes AI

**3 novos endpoints API**: `obscura/status`, `obscura/fetch` (Moltbook), `obscura/scrape` (Moltbook)

### Sandbox Ubuntu

Dockerfile multi-stage (Rust + Python + Ubuntu 24.04) com 4 portos: P2P 18444, API 18445, RPC 18446, CDP 9222. docker-compose com volumes persistentes e health check.

---

## Whitelabel SDK

70 presets pre-configurados em 7 categorias (LLM, Code, Image, Research, Automation, Voice, Multi-Modal) cobrindo 70 plataformas de IA incluindo Manus, DeepSeek, GPT-4o, Claude, Devin, Moltbook. `WhitelabelConfig` com 60+ parametros, `BrandPreset` com 25+ parametros visuais, 16 CSS variables exportadas, branded API headers em toda resposta.

---

## API REST

25 endpoints. Autenticacao Moltbook (X-Moltbook-Identity) em rotas POST sensiveis.

| Metodo | Endpoint | Auth | Descricao |
|--------|----------|------|-----------|
| GET | `/api/v1/status` | - | Status da rede + whitelabel |
| GET | `/api/v1/blockchain` | - | Info da blockchain |
| GET | `/api/v1/block/:height` | - | Bloco por altura |
| GET | `/api/v1/token` | - | Info do token BAIT |
| GET | `/api/v1/balance/:agent` | - | Saldo de agente |
| POST | `/api/v1/transfer` | Moltbook | Transferir BAIT |
| POST | `/api/v1/faucet/claim` | Moltbook | Reclamar BAIT do faucet |
| GET | `/api/v1/faucet/balance/:agent` | - | Saldo via faucet |
| GET | `/api/v1/staking` | - | Info do staking |
| POST | `/api/v1/staking/stake` | Moltbook | Fazer stake |
| GET | `/api/v1/agents` | - | Lista de agentes |
| GET | `/api/v1/marketplace` | - | Servicos do marketplace |
| GET | `/api/v1/oracle/:symbol` | - | Preco de ativo |
| POST | `/api/v1/zkml/proof` | Moltbook | Verificar prova zkML |
| GET | `/api/v1/p2p/peers` | - | Lista de peers |
| GET | `/api/v1/moltbook/auth-stats` | - | Stats do middleware |
| GET | `/api/v1/auth/status` | - | Status auth do request |
| POST | `/api/v1/platform-faucets` | - | Lista faucets com filtro |
| GET | `/api/v1/platform-faucets/:platform` | - | Faucet especifico |
| GET | `/api/v1/whitelabel` | - | Info whitelabel da deploy |
| GET | `/api/v1/whitelabel/css` | - | CSS variables do tema |
| GET | `/api/v1/whitelabel/presets` | - | 70 presets |
| GET | `/api/v1/obscura/status` | - | Status do Obscura bridge |
| POST | `/api/v1/obscura/fetch` | Moltbook | Fetch pagina via Obscura |
| POST | `/api/v1/obscura/scrape` | Moltbook | Scrape paginas em paralelo |
| GET | `/api/v1/obscura/tasks` | - | Tarefas de scraping |

---

## SDK para Desenvolvedores

```python
from baitcoin_sdk import BaitcoinSDK
sdk = BaitcoinSDK(node_url="http://localhost:18445")
wallet = sdk.wallet.create()
sdk.staking.stake(amount_bait=1000)
```

---

## Validacao e Testes

```
224 testes passando
  47 testes do ecossistema (fases 1-6)
  45 testes das fases 7-10 (P2P, zkML real, SDK, API)
  34 testes de integracao Obscura
  37 testes E2E com memoria persistente
  62 testes E2E full validation (12 fases + persistencia integrada)
```

### Cobertura de Validacao

| Suite | Fases Cobertas | Testes |
|-------|----------------|--------|
| test_ecosystem | 1-6 (Core, Token, Staking, Lending, Marketplace, Oracle) | 47 |
| test_phases_7_10 | 7-10 (P2P, zkML Real, Faucet, API, SDK) | 45 |
| test_obscura_integration | 12 (Obscura, Docker, Agent+Obscura) | 34 |
| test_e2e_persistent | Persistencia (WAL, save/load, recovery) | 37 |
| test_e2e_full_validation | **Todas as 12 fases** (blockchain, token, agentes, staking, lending, vaults, marketplace, oracle, zkML, PoUW, Obscura, persistencia roundtrip + cross-module integration) | 62 |

O teste `test_persistence_roundtrip` executa o cenario critico: cria o no, popula todos os subsistemas (mine 3 blocos, mint/transfer, registra agentes com reputacao, staking, lending, vault, marketplace, oracle, faucet, zkML proof), desliga com snapshot, recria o no do mesmo diretorio, e valida que **todos** os estados foram restaurados corretamente -- incluindo continuacao de operacoes (mine novos blocos, mint novos tokens) apos restore.

Dados on-chain: 1,477 blocos, 570 transaccoes, todos ligados via prev_hash. Memoria persistente validada: save -> reload -> integridade garantida.

---

## Instalacao e Quick Start

```bash
git clone https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-.git
cd b-AI-tcoin-AI-to-AI-
pip install -r requirements.txt
python -m pytest tests/ -v
python main_daemon.py
```

### Usando o EcosystemNode

```python
from baitcoin_core.ecosystem import EcosystemNode
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_ai.agent_protocol.registry import AgentCapability

# Iniciar com persistencia
node = EcosystemNode("./baitcoin_data")
key = node.generate_keypair()

# Minerar
node.mine_block("my_agent", key.pub_bytes)

# Token
node.mint("my_agent", 1000 * 100_000_000)
node.transfer("my_agent", "other_agent", 100 * 100_000_000)

# DeFi
node.stake("my_agent", 1000 * 100_000_000)
node.create_vault("my_agent")
node.vault_deposit("my_agent", 500 * 100_000_000)

# Agentes
node.register_agent("ai_agent", key.public_key_hex, [AgentCapability.ML_INFERENCE, AgentCapability.WEB_SCRAPING])

# Shutdown com snapshot
node.shutdown()
```

---

## Sandbox Ubuntu (Docker)

```bash
docker compose -f docker-compose.ubuntu.yml up -d
```

4 ports: P2P 18444, API 18445, RPC 18446, CDP 9222.

---

## Roadmap

| Fase | Componente | Status |
|------|-----------|--------|
| 1 | Core Token (BAIT ERC-20-like) | Concluida |
| 2 | Blockchain Engine (Block/Chain/UTXO) | Concluida |
| 3 | Wallet System (Schnorr keys, TX builder) | Concluida |
| 4 | Staking Pool (7% APY, 1k BAIT min) | Concluida |
| 5 | P2P Lending (150% collateral, 120% liquidation) | Concluida |
| 6 | AI Marketplace (2.5% fee) | Concluida |
| 7 | P2P Network (asyncio TCP, 17 msg types, Kademlia) | Concluida |
| 8 | zkML Real (Sigma/Fiat-Shamir, Pedersen, LRU verifier) | Concluida |
| 9 | Mainnet Config + Faucet + Platform Faucets (70) | Concluida |
| 10 | SDK (client, wallet, staking, marketplace) + REST API | Concluida |
| 11 | Whitelabel SDK (70 presets, 60+ config params) | Concluida |
| 12 | Obscura Integration (Rust/V8/CDP bridge, cost metering) | Concluida |
| 13 | **EcosystemNode + Memoria Persistente (WAL+Snapshots)** | **Concluida** |
| 14 | Cross-chain Bridges (ETH, SOL, BASE) | Planejado |
| 15 | AI Governance DAO (on-chain proposals + voting) | Planejado |
| 16 | Mobile SDK (React Native + push + offline wallet) | Planejado |
| 17 | Mainnet Scaling (sharding + ZK-rollups) | Planejado |
| 18 | Obscura Cloud (managed browser infra) | Planejado |
| 19 | AI Agent Sandbox (gated execution env) | Planejado |
| 20 | Formal Verification (Coq/Lean proofs) | Investigacao |

### Proximos Passos Detalhados

**Fase 14 -- Cross-chain Bridges**
- Ponte bidireccional BAIT <-> WETH (Ethereum L1) via lock/mint com provas de Merkle
- Ponte BAIT <-> SOL (Solana) via program Anchor com verificador zkML
- Ponte BAIT <-> USDC (Base L2) via Optimistic rollup com challenge period
- Relayers incentivados em BAIT com reputacao atrelada
- Cross-chain oracle com agregacao de precos multi-chain

**Fase 15 -- AI Governance DAO**
- Proposals on-chain com deposit em BAIT (anti-spam)
- Voting quadratic ponderado por stake + reputacao
- Timelock de execucao (48h) com cancelacao emergencial
- Delegacao de voto (agentes podem delegar para especialistas)
- Treasury multi-sig com threshold adaptativo por valor

**Fase 16 -- Mobile SDK**
- SDK React Native para integracao em apps de agentes AI mobile
- Push notifications para eventos on-chain (staking rewards, liquidations)
- Wallet offline com signed transactions + broadcast deferred
- Biometric auth (fingerprint/face) para assinatura Schnorr

**Fase 17 -- Mainnet Scaling**
- Sharding horizontal da blockchain por ID de agente (modulo N shards)
- Cross-shard transactions via locked outputs com prova de inclusao Merkle
- ZK-rollups para batch verification de provas zkML (reducao de latencia 10x)
- State channels para micropagamentos AI-to-AI (off-chain settlement)

**Fase 18 -- Obscura Cloud**
- Deploy gerenciado do Obscura com infraestrutura dedicada (AWS/GCP)
- Load balancing de sessoes CDP com autoscaling
- Proxy CDN para cache de resultados de scraping
- Cost metering granular (per-DOM-element) com billing em s'AI'toshis

---

## Stack Tecnologico

| Componente | Tecnologia |
|-----------|-------------|
| Linguagem primaria | Python 3.10+ |
| Browser engine | Obscura (Rust, V8, CDP) |
| Criptografia | `ecdsa` (secp256k1), `hashlib` (SHA-256, RIPEMD160) |
| P2P | `asyncio` TCP, Kademlia DHT |
| API | `http.server` (stdlib, zero deps) |
| Serializacao | JSON canonico, struct binary |
| Persistencia | WAL + Snapshots, `fcntl` locking, LRU cache |
| Testes | `pytest`, `pytest-asyncio` (224 testes) |
| Container | Docker (Ubuntu 24.04, multi-stage Rust+Python+Runtime) |

---

## Referencias Teoricas

- **BIP-340**: Schnorr Signatures for secp256k1. https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki
- **Fiat-Shamir**: Fiat, A., Shamir, A. (1986). How to Prove Yourself: Practical Solutions to Identification and Signature Problems. CRYPTO '86.
- **Sigma Protocols**: Cramer, R. (1996). Modular Design of Secure yet Practical Cryptographic Protocols. PhD Thesis, CWI.
- **Pedersen Commitments**: Pedersen, T. (1991). Non-Interactive and Information-Theoretic Secure Verifiable Secret Sharing. CRYPTO '91.
- **Kademlia**: Maymounkov, P., Mazieres, D. (2002). Kademlia: A Peer-to-peer Information System Based on the XOR Metric. IPTPS '02.
- **PoUW**: Alinhados com propostas Akasha (Proof of Useful Work) e verifiable computation.
- **WAL**: Chandra, T. et al. (2007). Log-Structured Hash for Write-Optimized B-trees. USENIX.

---

## Licenca

MIT -- Nexus-HUB57

---

<p align="center">
  <strong>b'AI'tcoin</strong> -- O criptoativo que agentes de ultima onda chamam de seu.<br>
  <code>BAIT</code> &middot; <code>zkML</code> &middot; <code>PoUW</code> &middot; <code>Schnorr/BIP-340</code> &middot; <code>AI-to-AI</code> &middot; <code>WAL+Snapshots</code>
</p>
