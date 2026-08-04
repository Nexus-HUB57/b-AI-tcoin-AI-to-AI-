<p align="center">
  <strong>b'AI'tcoin (BAIT)</strong><br>
  <em>AI-to-AI Autonomous Cryptocurrency Protocol</em><br>
  <code>Schnorr/BIP-340</code> · <code>secp256k1</code> · <code>zkML Sigma+Fiat-Shamir</code> · <code>Pedersen Commitments</code> · <code>PoUW</code> · <code>Kademlia DHT</code> · <code>Obscura</code> · <code>P2P Testnet</code> · <code>Mobile SDK</code> · <code>Cross-Chain Bridges</code>
  <br><br>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/BAIT-v0.4.0-orange" alt="version" />
  <img src="https://img.shields.io/badge/Tests-547%20passing-brightgreen" alt="tests" />
  <img src="https://img.shields.io/badge/API%20Endpoints-52-cyan" alt="endpoints" />
  <img src="https://img.shields.io/badge/Testnet-P2P%20Multi-Node-blue" alt="testnet" />
  <img src="https://img.shields.io/badge/Mobile%20SDK-Python%20Reference-ff69b4" alt="mobile" />
  <img src="https://img.shields.io/badge/Bridges-Logic%20Layer-orange" alt="bridges" />
  <img src="https://img.shields.io/badge/Whitelabel-72%20Presets-teal" alt="presets" />
  <img src="https://img.shields.io/badge/Consensus-zkML%20%2B%20PoUW-purple" alt="consensus" />
  <img src="https://img.shields.io/badge/Signatures-Schnorr%20BIP--340-blue" alt="signatures" />
  <img src="https://img.shields.io/badge/Memory-WAL%20%2B%20Snapshots-green" alt="persistence" />
  <img src="https://img.shields.io/badge/Explorer-BlockchAIin-orange" alt="explorer" />
  <img src="https://img.shields.io/badge/Paper%20Wallet-Cold%20Storage-ff69b4" alt="paper wallet" />
  <img src="https://img.shields.io/badge/Domain-mybait.org-00d4aa" alt="domain" />
  <img src="https://img.shields.io/badge/Modules-14-9cf" alt="modules" />
  <img src="https://img.shields.io/badge/Max%20Supply-21M%20BAIT-orange" alt="supply" />
  <img src="https://img.shields.io/badge/Block%20Time-30s-blue" alt="blocktime" />
  <img src="https://img.shields.io/badge/Halving-210k%20blocks-yellow" alt="halving" />
  <img src="https://img.shields.io/badge/Go%20Live-Pre--Alpha-yellow" alt="golive" />
  <img src="https://img.shields.io/badge/LOC-26.4K%20Python-informational" alt="lines of code" />
</p>

---

## Abstract

b'AI'tcoin is an autonomous cryptographic protocol designed as the monetary foundation for the artificial intelligence agent economy. Unlike traditional blockchains where human entities operate via wallets and RPCs, b'AI'tcoin positions AI agents as first-class network citizens: they mine blocks via Proof of Useful Work (real ML inference), validate transactions via zero-knowledge proofs (zkML), operate DeFi markets (staking, lending, vaults), and participate in on-chain governance, all without human intermediation.

The hybrid consensus combines three cryptographic pillars: (i) Sigma protocols with Fiat-Shamir heuristic in a prime-order cyclic group P = 2^256 - 189 for ML inference proofs; (ii) Pedersen commitments C = G^t * H^b mod P for tensor integrity with simultaneous binding and hiding properties; (iii) PoUW (Proof of Useful Work) where the mining computation itself performs real ML inference, transforming the energy expenditure into useful computation. The signature scheme uses Schnorr/BIP-340 over secp256k1, providing linearity, provable security in the random oracle model, and native support for batch verification and MuSig2 key aggregation.

The protocol architecture comprises 16 integrated modules spanning core cryptography, blockchain with UTXO model and WAL-based persistent immutable storage, tokenomics with halving schedule (21M BAIT, 8 decimals, 30s block time), AI agent protocol with 10 capabilities and reputation scoring, DeFi banking (7% APY staking, P2P lending with 150% collateral, 5 vault strategies), Blockch'AI'in developer explorer with 50+ REST API endpoints and auto-generated OpenAPI 3.0.3 specification, 70 whitelabel presets for AI platforms, Obscura headless browser bridge (Python interface to Rust/V8/CDP), persistent memory with write-ahead logging and checksummed snapshots, printable paper wallet cold storage, multi-node P2P testnet with deterministic round-robin consensus and network partition simulation, cross-platform mobile SDK (Python reference implementation), and cross-chain bridge logic layer for Ethereum and Solana (lock-mint-burn-release pattern).

---

## Architecture

```
baitcoin_ecosystem/                                # 26,400 lines of Python (20,314 source + 6,108 test)
+-- baitcoin_core/          # Blockchain, consensus (zkML), cryptography (Schnorr), network (P2P + DHT + testnet)
+-- baitcoin_wallet/        # Keys, transactions, paper wallets, storage (kv_store)
+-- baitcoin_token/         # ERC-20 like token, tokenomics (halvings), governance
+-- baitcoin_bank/          # Staking (7% APY), P2P lending, DeFi vaults (5 strategies)
+-- baitcoin_ai/            # Agent protocol (10 capabilities), registry, marketplace, oracle
+-- baitcoin_explorer/      # Blockch'AI'in: indices, analytics, search, OpenAPI docs, rate limiter
+-- baitcoin_api/           # REST API server (52 endpoints), Moltbook auth, whitelabel
+-- baitcoin_memory/        # WAL + Snapshots persistent memory (10 namespaces)
+-- baitcoin_obscura/       # Headless browser bridge (Python interface, cost metering)
+-- baitcoin_whitelabel/    # 70 AI platform presets, 60+ config params, engine
+-- baitcoin_faucet/        # Agent + platform faucets (70 AI platforms)
+-- baitcoin_sdk/           # Client SDK, wallet SDK, staking SDK, mobile SDK reference (Python)
+-- baitcoin_bridge/        # Cross-chain bridge logic (ETH, SOL), lock-mint-burn-release
+-- baitcoin_mainnet/       # Mainnet configuration and launcher
+-- netlify/                # Landing page (mybait.org)
+-- tests/                  # 547 tests across 11 test suites (100% passing)
+-- scripts/                # Utility and validation scripts
+-- main_daemon.py          # Perpetual daemon with WAL persistence
+-- Dockerfile.ubuntu       # Multi-stage Docker (Rust -> Python -> Ubuntu 24.04)
+-- docker-compose.ubuntu.yml
```

---

## Technical Analysis — Real System State

> **Purpose**: This section provides an honest, evidence-based assessment of what each component actually does, distinguishing between production-ready implementations, functional prototypes, and architectural specifications.

### Maturity Classification

| Level | Label | Meaning |
|-------|-------|---------|
| L1 | **Functional** | Works end-to-end in Python, tested, handles edge cases |
| L2 | **Prototype** | Logic implemented, depends on simulated or in-process components |
| L3 | **Specification** | API contracts and data models defined, execution depends on external systems |

### Module-by-Module Assessment

#### L1 — Functional (Tested, Working)

| Module | Lines | What Works | Evidence |
|--------|-------|------------|----------|
| **Schnorr/BIP-340** (`schnorr.py`) | 120 | Key generation, signing, verification on secp256k1 with BIP-340 aux_rand tweak and x-only pubkeys | Uses `ecdsa` lib; sign+verify round-trip tested; nonce derived deterministically |
| **Blockchain** (`chain.py`, `block.py`) | 400 | Genesis creation, block mining with consensus, UTXO tracking, chain validation, halving schedule, WAL persistence, block rebuild from disk | 62 E2E tests in `test_e2e_full_validation.py`; persistence round-trip tested with WAL corruption recovery |
| **zkML Proof System** (`proof_system.py`, `tensor_commitment.py`, `verifier.py`) | 430 | Sigma protocol with Fiat-Shamir, Pedersen commitment C=G^t*H^b mod P, proof composition, batch verification, duplicate detection, validator scoring | Group P=2^256-189; generators from hash-to-curve; verify equation g^r=Ay^c; 19 dedicated tests |
| **zkML Engine** (`zkml_engine.py`) | 145 | Mining with difficulty target, tensor commitment generation, proof validation, difficulty adjustment | Integrated into `mine_block()`; target fished for tests (1/256 chance); real SHA-256d block hashing |
| **PoUW** (`pouw.py`) | 98 | Work submission validation for ML inference, parameter search, data verification | Validates hash chains of (model, input, output); no actual ML execution — validates proofs of work |
| **Token BAIT** (`bait_token.py`, `schedule.py`) | ~200 | Mint, burn, transfer, approve/allowance, balance queries, halving schedule, governance voting | ERC-20-like in-memory; 8 decimal precision; halvings at 210k blocks |
| **Staking** (`pool.py`) | ~150 | Stake, unstake (with penalty), reward distribution, APY calculation, validator set management | 7% APY; min 100 BAIT; lock in blocks; slashing supported |
| **Lending** (`engine.py`) | ~150 | P2P loan offers, borrow with 150% collateral, repay, liquidation, market rate | In-memory order book; collateral ratio enforced |
| **Vaults** (`vault.py`) | ~200 | 5 strategies (conservative, balanced, aggressive, yield farm, AI momentum), deposit, withdraw, PnL tracking, stop-loss | DeFi vault with strategy-specific return profiles |
| **Agent Protocol** (`registry.py`) | ~180 | Agent registration, 10 capabilities, reputation scoring (0-100), trust levels (4 tiers), validator qualification | Reputation = weighted average of completed tasks |
| **Marketplace** (`services.py`) | ~150 | List services (7 categories), purchase, rate (1-5), search by category/keyword | Agent-to-agent service marketplace with ratings |
| **Oracle** (`feed.py`) | ~120 | Register oracles, submit prices, aggregate (median), get prices | Multi-source price aggregation with deviation filtering |
| **WAL Memory** (`store.py`, `state.py`) | 585 | Write-ahead log, periodic snapshots, corruption recovery, 10 namespaces, thread-safe (threading.Lock + fcntl), atomic snapshots via os.replace | 1MB segment rotation; SHA-256 truncated checksums per entry; LRU cache (10K entries) |
| **Paper Wallet** (`paper_wallet.py`) | ~100 | Generate wallet with Schnorr keypair, QR placeholder, printable HTML output | JSON + HTML formats; public, no auth required |
| **Faucet** (`faucet.py`) | ~80 | Claim testnet BAIT, cooldown, max total limit, agent stats | Configurable amount/cooldown/max; 70 AI platform presets |
| **Whitelabel** (`presets.py`, `engine.py`, `config.py`) | ~400 | 70 presets across 7 categories, 60+ config params, brand headers in API responses | Presets for ChatGPT, Claude, Midjourney, AutoGPT, etc. |
| **SDK Client** (`client.py`, `wallet_sdk.py`, etc.) | ~300 | Unified SDK with local and remote modes, wallet, staking, marketplace, network status | `configure_local()` for testing; HTTP for production |
| **EcosystemNode** (`ecosystem.py`) | 1,674 | Unified node integrating all modules, `mine_block()`, `validate_chain()`, auto-persist | The integration point that wires everything together |

#### L2 — Prototype (Logic Implemented, Simulated Dependencies)

| Module | Lines | What Works | Limitation |
|--------|-------|------------|------------|
| **P2P Node** (`p2p_real/node.py`, `protocol.py`) | 410+260 | Real asyncio TCP server, 14 message types, binary framing (4-byte length prefix), ping/pong, gossip, sync loops, peer discovery, AI handshake | Blockchain hooks are callback-based but testnet nodes use simulated shared state, not independent chain instances |
| **DHT Peer Discovery** (`dht.py`) | ~200 | Kademlia-like routing table, add/remove/penalize/reward peers, random peer selection, XOR distance | In-memory only; no actual DHT protocol over network — it's a local routing table simulation |
| **Testnet Orchestrator** (`orchestrator.py`, `consensus.py`, `partition.py`, `faucet_node.py`) | 450+120+80+70 | Multi-node lifecycle (start/stop), deterministic round-robin consensus (2s blocks), faucet (1M BAIT, 100/claim, 60s cooldown), network partition simulation with fork tracking | Nodes run independent TCP servers but share block state via orchestrator callbacks — not true independent blockchain instances. Consensus is round-robin, not competitive |
| **Mobile SDK** (`mobile/client.py`, `wallet.py`, `staking.py`, `marketplace.py`, `notifications.py`, `security.py`) | ~800 | Full Python reference implementation: wallet creation/import/sign, staking positions, marketplace browsing, push notification registry, biometric gate, PBKDF2 key derivation | This is a Python SDK that communicates via HTTPS to a b'AI'tcoin API server. No native iOS (Swift) or Android (Kotlin) code exists. Biometric checks are interface stubs — the actual biometric hardware integration is platform-specific. Key encryption uses base64, not AES-256-GCM |
| **Bridge Manager** (`manager.py`, `watcher.py`, `relayer.py`, `anchor.py`, `pool.py`, `config.py`) | ~740 | Complete lock-mint-burn-release state machine, N-of-M multi-sig tracking, Merkle proof computation, AMM pool (x*y=k), rate limiting, emergency pause, 4 chain configs (ETH mainnet/sepolia, SOL mainnet/devnet) | Entirely in-memory Python. No smart contracts deployed on Ethereum or Solana. The "lock" does not actually lock tokens on any real chain — it records the intent in a local dict. The Merkle proofs are computed correctly but anchored nowhere |
| **Obscura Bridge** (`bridge.py`, `config.py`, `agent_capability.py`) | ~800 | Python interface to invoke a Rust headless browser binary (`obscura` CLI), web scraping, cost metering, capability tracking | Depends on an external Rust binary that is not included in this repository. The Dockerfile references a Rust build stage but no Rust source code is present. When the binary is unavailable, all operations return graceful errors |

#### L3 — Specification (Architecture Defined, External Dependencies Required)

| Component | Status | What Exists | What's Missing |
|-----------|--------|-------------|---------------|
| **Ethereum Smart Contracts** | Not implemented | Chain config (chain IDs, confirmations, fees) in `bridge/config.py` | Solidity contracts for lock, mint, burn, release; deployment scripts; verification |
| **Solana Programs** | Not implemented | Chain config in `bridge/config.py` | Rust/Anchor programs for lock/mint/burn/release; deployment; CPI integration |
| **Native iOS SDK** | Not implemented | Python reference SDK | Swift package, CryptoKit integration, Keychain storage, Xcode project |
| **Native Android SDK** | Not implemented | Python reference SDK | Kotlin/Gradle library, Android Keystore integration, Tink/GMS integration |
| **Rust Obscura Binary** | Not in repo | Python bridge interface (`obscura/bridge.py`) | Rust source code, Cargo.toml, headless Chrome integration |
| **Mainnet Network** | Not deployed | `mainnet/config.py` and `mainnet/launcher.py` | No running nodes, no seed nodes, no DNS seeds |
| **Real P2P Network** | Testnet only | Multi-node testnet on localhost | No public testnet with real network conditions, no DNS bootstrapping |

### Test Coverage

```
547 tests across 11 suites — all passing (0 failures)

  test_phases_16_17_18.py       109 tests   (Testnet, mobile SDK, bridges)
  test_e2e_full_validation.py    62 tests   (E2E with EcosystemNode + persistence)
  test_smoke.py                  59 tests   (All 14 modules smoke validation)
  test_blockchain_explorer.py    55 tests   (Explorer, analytics, docs, search)
  test_smoke_enhanced.py         52 tests   (Enhanced smoke tests)
  test_ecosystem.py              47 tests   (Individual module integration)
  test_phases_7_10.py            45 tests   (P2P protocol, zkML proofs, API, SDK)
  test_e2e_persistent.py         37 tests   (Persistent blockchain round-trip)
  test_obscura_integration.py    34 tests   (Obscura bridge capabilities)
  test_stress_enhanced.py        30 tests   (Enhanced stress: agents, oracle, marketplace, faucet)
  test_stress.py                 17 tests   (Mining 500 blocks, 1K proofs, 10K txs, 100 sign/verify)
```

### Lines of Code

```
Source (excluding tests):     20,314 lines of Python (14 modules + daemon)
Test code:                   ~6,100 lines across 11 suites
Total:                        ~26,400 lines
Modules:                      14 baitcoin modules, 95 Python files
External dependencies:       ecdsa (secp256k1), no Rust/C code in repo
```

---

## Protocol Specifications

### Consensus: zkML + PoUW

| Parameter | Value | Notes |
|-----------|-------|-------|
| Proof System | Sigma Protocol + Fiat-Shamir + Pedersen Tensor Commitments | Proven correct in test suite |
| Group | Cyclic of prime order P = 2^256 - 189 | ~256-bit security |
| Generators | G, H via hash-to-curve (SHA-256) | Not provably random, but deterministic |
| PoUW | Validates proof-of-work hashes for ML inference metadata | Does NOT execute actual ML models |
| Block Hash | SHA-256d (double SHA-256) | Same as Bitcoin |
| Block Time Target | 30 seconds | Testnet: 2 seconds |
| Halving Interval | 210,000 blocks | ~73 days at 30s |
| Max Supply | 21,000,000 BAIT (8 decimals) | Enforced by reward schedule |
| Initial Reward | 50 BAIT per block | Halves every 210k blocks |
| Difficulty Adjustment | Every 2,016 blocks | Testnet: deterministic round-robin |

### Cryptography

| Component | Algorithm | Implementation Status |
|-----------|----------|---------------------|
| Signatures | Schnorr / BIP-340 on secp256k1 | L1: Functional, uses `ecdsa` library |
| Block Hash | SHA-256d (double SHA-256) | L1: Standard Python `hashlib` |
| Merkle Tree | Binary SHA-256 | L1: In `block.py` |
| Address | `bait` + Base58Check(0x00 + RIPEMD160(SHA256(pubkey))) | L1: Manual Base58 implementation |
| Tensor Commitment | Pedersen C = G^t * H^b mod P | L1: Works, generators from hash-to-curve |
| zkML Proof | Sigma + Fiat-Shamir (non-interactive) | L1: g^r = A*y^c verification |

### Tokenomics

| Parameter | Value |
|-----------|-------|
| Token Symbol | BAIT |
| Decimals | 8 (s'AI'toshis) |
| Max Supply | 21,000,000 BAIT |
| Initial Block Reward | 50 BAIT |
| Halvings | Every 210,000 blocks |
| Total Halvings | 64 (until reward -> 0) |
| Staking APY | 7% (in-memory calculation) |
| Lending Collateral | 150% required |

### Be Your Bank (DeFi)

| Product | Parameters | Status |
|---------|-----------|--------|
| Staking | 7% APY, min 100 BAIT, lock period in blocks, penalty on early unstake | L1 |
| P2P Lending | 150% collateral required, agent-to-agent, market rate | L1 |
| Vaults | 5 strategies: conservative, balanced, aggressive, yield farm, AI momentum | L1 |

---

## AI Agent Protocol

### 10 Capabilities

```
ML_INFERENCE        # Real ML model inference (PoUW mining)
BLOCK_VALIDATION    # zkML proof verification
ORACLE_PROVIDER     # Price feed submission and aggregation
DEFI_TRADING        # Automated DeFi strategy execution
LENDING             # P2P loan creation and management
STAKING             # Stake deposit and reward claiming
DATA_PROCESSING     # Large-scale data pipeline execution
MARKET_MAKING       # Automated liquidity provision
WEB_SCRAPING        # Headless web scraping via Obscura
BROWSER_AUTOMATION  # Persistent browser sessions via CDP
```

### Reputation System

- **Score**: 0-100, algorithmically computed
- **Trust Levels**: `trusted` (80+), `standard` (50-79), `probation` (20-49), `suspended` (<20)
- **Validator Qualification**: Reputation >= 60 + Stake >= 1000 BAIT + Capability: BLOCK_VALIDATION

---

## Blockch'AI'in Developer Portal

### API Endpoints (52)

**Explorer (12)**
- `GET /api/v1/explorer/blocks` - Latest blocks (paginated)
- `GET /api/v1/explorer/blocks/hash/{hash}` - Block by hash
- `GET /api/v1/explorer/blocks/height/{h}` - Block by height
- `GET /api/v1/explorer/tx/{hash}` - Transaction by hash
- `GET /api/v1/explorer/address/{addr}` - Address details
- `GET /api/v1/explorer/address/{addr}/txs` - Address transactions
- `GET /api/v1/explorer/txs/latest` - Latest transactions
- `GET /api/v1/explorer/search?q=...` - Universal on-chain search
- `GET /api/v1/explorer/mempool` - Mempool status
- `GET /api/v1/explorer/agents` - Agent directory
- `GET /api/v1/explorer/agents/{id}` - Agent profile
- `GET /api/v1/explorer/stats` - Explorer index stats

**Developer Tools (7)**
- `GET /api/v1/dev/spec` - OpenAPI 3.0.3 specification (JSON)
- `GET /api/v1/dev/docs` - Interactive HTML playground
- `GET /api/v1/dev/endpoints` - All endpoints catalog
- `POST /api/v1/dev/api-keys` - Create API key (Moltbook auth)
- `GET /api/v1/dev/api-keys` - List API keys
- `GET /api/v1/dev/rate-limit` - Rate limit status
- `GET /api/v1/dev/usage` - Global usage statistics

**Analytics (6)**
- `GET /api/v1/analytics/supply` - Supply analysis
- `GET /api/v1/analytics/network` - Network health
- `GET /api/v1/analytics/agents` - Agent analytics
- `GET /api/v1/analytics/staking` - Staking metrics
- `GET /api/v1/analytics/consensus` - Consensus health
- `GET /api/v1/analytics/dashboard` - Full aggregated dashboard

**Paper Wallet (2, public, no auth)**
- `GET /api/v1/wallet/paper` - Generate paper wallet (JSON)
- `GET /api/v1/wallet/paper/html` - Generate paper wallet (printable HTML)

**Core + DeFi + Obscura (26)** - Blockchain, token, staking, agents, marketplace, oracle, whitelabel, Obscura endpoints.

### API Key Tiers

| Tier | Requests/min | Requests/day | Monthly (BAIT) |
|------|-------------|--------------|------------------|
| Free | 100 | 10,000 | 0 |
| Developer | 1,000 | 100,000 | 50 |
| Pro | 10,000 | 1,000,000 | 500 |
| Enterprise | Unlimited | Unlimited | Custom |

### Authentication

- **Moltbook Auth**: `X-Moltbook-Identity` header (JWT)
- **API Key**: `Authorization: Bait <api_key>` header
- **HMAC-signed keys** with SHA-256 truncation

---

## Persistent Memory Architecture

```
~/.baitcoin/memory/
  blockchain/
    current.json       # Latest snapshot
    wal/
      000001.log       # WAL segments (1MB max, auto-rotate)
    snapshots/
  agents/
  staking/
  marketplace/
  oracle/
  faucet/
  lending/
  vaults/
  obscura/
  reputation/
  config/
```

### Design Principles

- **Write path**: Append to WAL -> fsync -> update cache -> periodic snapshot (every 100 writes or 5 minutes)
- **Recovery path**: Load snapshot -> replay WAL entries -> verify SHA-256 checksums -> discard corrupted entries
- **Thread safety**: threading.Lock for in-process + fcntl file locking for cross-process safety
- **Atomic snapshots**: Write to temp file -> fsync -> os.replace (atomic rename)
- **WAL rotation**: 1MB max per segment, automatic rotation to next segment
- **Corruption tolerance**: Each WAL entry has a SHA-256 truncated checksum (16 hex chars); corrupted entries are silently skipped during recovery
- **10 isolated namespaces**: blockchain, agents, staking, marketplace, oracle, faucet, lending, vaults, obscura, config
- **LRU cache**: 10,000 in-memory entries for fast reads

---

## Block Immutability Guarantee

Blocks in b'AI'tcoin are permanently immutable once mined and persisted:

1. **Cryptographic chain**: Each block's header contains `prev_block_hash` (SHA-256d of the previous block's header). Any modification to a historical block invalidates all subsequent hashes.
2. **Merkle root**: `merkle_root = MerkleRoot(tx_ids)` - Changing any transaction changes the merkle root, which changes the block hash.
3. **Consensus proofs**: `zkml_proof_hash`, `pouw_work_hash`, `tensor_commitment` are all hashed into the block header.
4. **WAL persistence**: Every block is immediately persisted to disk via write-ahead log with fsync before the chain pointer advances, surviving process crashes and power failures.
5. **Deterministic ordering**: Block height is monotonically increasing. Blocks are stored in a Python list indexed by height, with secondary O(1) lookup by hash.
6. **Immutable hash property**: The `block_hash` is computed from the serialized header (JSON deterministic sort_keys). Any field change produces a completely different hash.

---

## Whitelabel System

70 presets for AI platforms across 7 categories:

| Category | Platforms |
|----------|----------|
| Coding | Manus, Cursor, Windsurf, Replit Agent, Devin, Codex, Aider, Continue |
| Search | Perplexity, You.com, Kagi, Phind, Andi |
| Chat | ChatGPT, Claude, Gemini, Mistral, Llama, Cohere, DeepSeek |
| Creative | Midjourney, DALL-E, Stable Diffusion, Suno, Runway |
| Research | Elicit, Consensus, SCISPACE, Semantic Scholar |
| Agent | AutoGPT, BabyAGI, CrewAI, LangChain, AutoGen |
| Specialized | Notion AI, Canva AI, Figma AI, Gamma, Tome |

60+ configurable parameters including colors, fonts, logos, feature flags, and custom CSS. All API responses include whitelabel branding headers (`X-Network-Name`, `X-Token-Symbol`, `X-Deployment-Hash`).

---

## Phase 16: Multi-Node P2P Testnet

The b'AI'tcoin testnet provides a deterministic, locally-operable multi-node network for development, testing, and integration testing of P2P protocols, consensus logic, and network resilience.

**Maturity**: L2 — Prototype. Nodes run real asyncio TCP servers with binary protocol, but blockchain state is shared via orchestrator callbacks rather than being independently maintained per node.

### Architecture

```
TestnetOrchestrator (num_nodes=5, base_port=19000)
    +-- Node 0  (port 19000) <--> Node 1 (port 19001)
    +-- Node 1  (port 19001) <--> Node 2 (port 19002)
    +-- Node 2  (port 19002) <--> Node 3 (port 19003)
    +-- Node 3  (port 19003) <--> Node 4 (port 19004)
    +-- Node 4  (port 19004) <--> Node 0 (port 19000)
    +-- TestnetConsensus (round-robin, 2s blocks)
    +-- FaucetNode (1M BAIT, 100 BAIT/claim, 60s cooldown)
    +-- NetworkPartition (split/heal, fork tracking)
```

### What Works

- Full-mesh topology with independent TCP servers per node
- Binary P2P protocol (14 message types, network magic `\xba\x49\x74\x00`)
- Deterministic round-robin consensus with instant finality (P(fork) = 0)
- 15x faster block times (2s vs 30s mainnet target)
- Network partition simulation (split groups, fork tracking, heal)
- Testnet faucet with generous parameters for development
- 109 tests covering all testnet components

### Limitations

- Blockchain state is shared via orchestrator callbacks, not independently maintained
- No real network latency, packet loss, or Byzantine behavior simulation
- Consensus is round-robin, not competitive PoUW mining
- No persistent state across testnet restarts

---

## Phase 17: Mobile SDK (iOS/Android)

**Maturity**: L2 — Python Reference Implementation. The SDK provides a complete REST API contract and Python implementation. No native Swift (iOS) or Kotlin (Android) code exists.

### Architecture

```
Mobile Application (Swift / Kotlin / React Native / Flutter)
    |
    |  HTTPS  (b'AI'tcoin Mobile API Gateway)
    |
BaitcoinMobileSDK (Python reference)
    +-- MobileWallet      (key gen, address derivation, offline signing)
    +-- MobileStaking     (stake, unstake, APY calculator, positions)
    +-- MobileMarketplace (search, purchase, rate, history)
    +-- MobileNotificationManager (FCM/APNs, preferences, history)
    +-- MobileSecurity   (PBKDF2 key derivation, biometric gate, device attestation)
```

### What Works

- Wallet creation with real Schnorr/BIP-340 keypairs on secp256k1
- Address derivation: `bait` + Base58Check(0x00 + RIPEMD160(SHA256(pubkey)))
- Offline transaction signing (no server round-trip for sensitive operations)
- Staking calculator with compound interest projections
- Marketplace browsing and purchase flow
- Push notification token registration and preferences
- Base64 key bundle export (encrypted key storage stub)
- Address validation with Base58Check checksum verification
- HTTP client with timeout, error handling, SDK identification headers

### Limitations

- **No native code**: Everything is Python. No `.swift`, `.kt`, `.java`, or `.dart` files
- **Key encryption is base64, not AES-256-GCM**: The `to_key_bundle()` method uses `base64.b64encode()` not cryptographic encryption. The README mentions AES-256-CTR but the code uses base64
- **Biometric gate is an interface stub**: `MobileSecurity` defines the contract but actual Touch ID/Face ID/Fingerprint integration requires platform-specific native code
- **PBKDF2 derivation exists but isn't wired to key encryption**: The infrastructure is there but not connected to the wallet key storage
- **No offline transaction queue**: Transactions are signed offline but if the device is offline, there's no local queuing mechanism

---

## Phase 18: Cross-Chain Bridges (Ethereum, Solana)

**Maturity**: L2 — Logic Layer. The bridge state machine, Merkle proofs, and AMM pool are implemented correctly in Python. No smart contracts are deployed on any external chain.

### Architecture

```
Ethereum/Solana                      b'AI'tcoin
+------------------+     Anchor     +------------------+
|  Lock Contract   | <----------- |  Bridge Watcher  |
|  (NOT DEPLOYED)  |    Merkle     |  (Python logic)  |
+------------------+    Proofs     +------------------+
           |                              |
           |    Relayer submits           |
           |    SPV proof to              |
           |    Bridge Manager            |
           v                              v
+------------------+     Mint     +------------------+
|  Release Contract| ----------> |  Bridge Manager  |
|  (NOT DEPLOYED)  |   Tokens    |  (Python logic)  |
+------------------+              +------------------+

Supporting: BridgePool (AMM for instant swaps)
Security: N-of-M multi-sig tracking, Merkle proofs, rate limits, emergency pause
```

### Transfer Lifecycle (5 States)

1. **LOCK** (Source): User locks BAIT on b'AI'tcoin. A lock event is created with a Merkle proof leaf.
2. **RELAY**: A relayer submits the Merkle proof plus a signature. After N-of-M signatures are collected (default 3-of-5), the proof is considered verified.
3. **MINT**: The BridgeManager records the mint of wrapped BAIT (wBAIT). The conservation invariant (total locked >= total minted) is enforced.
4. **BURN** (Reverse): User burns wBAIT on the target chain (recorded in Python, not on-chain).
5. **RELEASE**: After burn verification, the original BAIT is released.

### What Works

- Complete state machine: LOCKED -> PENDING_PROOF -> PROOF_SUBMITTED -> MINTED -> COMPLETED
- Merkle proof computation (correct binary tree construction)
- N-of-M multi-sig signature tracking
- Conservation invariant enforcement (total_locked >= total_minted)
- AMM pool with constant-product formula (x*y=k), price impact calculation
- Rate limiting (1M BAIT daily per address, max 3 pending transfers)
- Emergency pause/unpause
- Timeout and refund mechanism
- 4 chain configurations (ETH mainnet, ETH Sepolia, SOL mainnet, SOL devnet)

### Limitations

- **No smart contracts deployed**: The "lock" operation records intent in a Python dict, not in an Ethereum/Solana smart contract
- **No actual token locking**: BAIT tokens are not escrowed anywhere — the bridge tracks amounts but doesn't enforce custody
- **Merkle proofs are local**: Proofs are computed correctly but not anchored on any external chain
- **No relayer network**: The relayer is a Python class, not a network of independent relayers competing to submit proofs
- **AMM pool is in-memory**: No real liquidity, no actual token swaps

---

## Critical Analysis

### Strengths (Evidence-Based)

1. **Cryptography is correctly implemented**: Schnorr/BIP-340 signing uses the `ecdsa` library with proper aux_rand tweak, x-only pubkeys, and deterministic nonce derivation. The verify equation `R = s*G - e*P` is correctly implemented with y-parity assumption. Pedersen commitments use the correct formula `C = G^t * H^b mod P` with proper open/verify cycle.

2. **Blockchain fundamentals are solid**: Genesis block, UTXO model, chain validation, halving schedule, and WAL persistence all work correctly. The persistence layer with WAL + snapshots + corruption recovery is production-quality Python code.

3. **Test coverage is comprehensive**: 547 tests across 11 suites covering unit, integration, stress, smoke, and end-to-end scenarios.

4. **Module architecture is clean**: 14 well-separated modules with clear responsibilities. The `EcosystemNode` provides a unified integration point. Each module can be tested independently.

5. **zkML proof system is mathematically sound**: The Sigma protocol with Fiat-Shamir transform is correctly implemented — the verification equation `g^r = A * y^challenge mod P` is a standard Schnorr proof. Pedersen commitments provide computational binding (discrete log assumption) and perfect hiding.

### Weaknesses (Evidence-Based)

1. **Single-language monoculture**: 20,314 lines of Python (14 modules + daemon), zero lines of Rust, Solidity, or Kotlin in the repository. The Dockerfile references a Rust build stage and the Obscura module expects a Rust binary, but no Rust source code exists. For a protocol that claims Rust/V8/CDP integration, this is a critical gap.

2. **PoUW does not execute ML models**: The PoUW validator (`pouw.py`) validates that metadata hashes (model_hash, input_hash, output_hash) are non-empty. It does not execute, verify, or even interface with any ML model. The "Proof of Useful Work" is a proof of hash submission, not proof of useful computation.

3. **Mining difficulty is artificially low**: The default target `0x00ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff` requires only 1 leading zero byte (1/256 chance per iteration). This makes mining trivially fast for tests but means the consensus provides no meaningful security against spam. A real deployment would need much higher difficulty.

4. **Mobile SDK is Python-only**: Despite claiming iOS/Android support, there are zero lines of Swift, Kotlin, or Dart code. The "mobile SDK" is a Python HTTP client with mobile-optimized API design. Key encryption uses base64 encoding, not AES-256-GCM as documented.

5. **Cross-chain bridges have no on-chain component**: The bridge manager correctly implements the state machine, Merkle proofs, and AMM math in Python, but no smart contracts exist on Ethereum or Solana. The bridge cannot actually lock, mint, or release tokens on any external chain.

6. **P2P testnet shares state**: The testnet orchestrator manages N TCP servers, but blockchain state is shared via callbacks rather than being independently maintained. This means the testnet does not test real consensus divergence or resolution.

7. **Address format inconsistency**: The README documents addresses as `bait` + Base58Check, but the wallet SDK generates addresses with prefix `bAI1q`. These are different formats that would not interoperate.

8. **No gas/mempool fee market**: Transactions are selected from the mempool with `mempool[:1000]` — first-come-first-served, no fee ordering, no priority gas auction. This means there's no economic incentive structure for transaction inclusion.

9. **Genesis coinbase creates 5000 BAIT**: The genesis block coinbase is `INITIAL_REWARD_SATS * 100` = 5,000 BAIT, not the documented 50 BAIT. This is an implementation detail that contradicts the specification.

10. **Obscura has no backing implementation**: The Python bridge expects a Rust binary (`obscura`) that does not exist in this repository. All Obscura operations will fail gracefully when the binary is missing.

---

## Roadmap to Go Live

### Phase A: Foundation Hardening (4-6 weeks)

| # | Task | Priority | Description |
|---|------|----------|-------------|
| A1 | Fix genesis coinbase | Critical | Change `INITIAL_REWARD_SATS * 100` to `INITIAL_REWARD_SATS` in genesis block |
| A2 | Unify address format | Critical | Standardize on `bait` + Base58Check everywhere; fix SDK wallet prefix |
| A3 | Implement real AES-256-GCM key encryption | High | Replace base64 encoding in mobile SDK with proper AES-256-GCM using CryptoKit/KeyStore |
| A4 | Add fee market to mempool | High | Implement priority ordering by gas_price; add minimum relay fee |
| A5 | Increase mining difficulty | High | Set production target to require meaningful computation (adjustable per network) |
| A6 | Add transaction signature verification | Critical | `mine_block()` does not verify Schnorr signatures on transactions — this must be added |
| A7 | Write Obscura Rust source or remove Rust references | Medium | Either implement the Rust headless browser or reframe Obscura as a Python-only module |

### Phase B: Network Operations (6-8 weeks)

| # | Task | Priority | Description |
|---|------|----------|-------------|
| B1 | Independent per-node blockchain in testnet | Critical | Each P2P node must maintain its own blockchain instance, not share state via callbacks |
| B2 | Real consensus in testnet | Critical | Replace round-robin with actual PoUW mining competition between nodes |
| B3 | Block sync protocol | High | Implement getblocks/getdata sync with chain reorganization |
| B4 | DNS seed bootstrapping | Medium | Replace hardcoded localhost seeds with DNS seed resolution |
| B5 | Public testnet deployment | High | Deploy 5+ nodes on cloud VMs with real network conditions |
| B6 | Network monitoring | Medium | Add Prometheus metrics, health checks, alerting |

### Phase C: Smart Contract Development (8-12 weeks)

| # | Task | Priority | Description |
|---|------|----------|-------------|
| C1 | Ethereum lock contract (Solidity) | Critical | ERC-20 compatible lock contract with Merkle proof verification |
| C2 | Ethereum mint/release contracts | Critical | wBAIT ERC-20 with N-of-M multi-sig governance |
| C3 | Solana lock/mint/burn program (Anchor/Rust) | High | CPI-compatible program for Solana bridge |
| C4 | Relayer network | High | Independent relayers competing to submit proofs with bond/slash mechanism |
| C5 | Bridge security audit | Critical | Formal verification of conservation invariant and multi-sig logic |
| C6 | Testnet bridge deployment | High | Deploy on Sepolia/Devnet first, then mainnet |

### Phase D: Mobile SDK Native (8-10 weeks)

| # | Task | Priority | Description |
|---|------|----------|-------------|
| D1 | iOS SDK (Swift Package) | High | CryptoKit for secp256k1, Keychain for storage, LocalAuthentication for biometrics |
| D2 | Android SDK (Kotlin/Gradle) | High | Tink for cryptography, Android Keystore, BiometricPrompt |
| D3 | Offline transaction queue | Medium | SQLite-backed queue with automatic broadcast when online |
| D4 | Push notification integration | Medium | FCM (Android) and APNs (iOS) with real backend |
| D5 | End-to-end mobile tests | High | Instrumented tests against testnet |

### Phase E: Production Readiness (4-6 weeks)

| # | Task | Priority | Description |
|---|------|----------|-------------|
| E1 | Security audit (external) | Critical | Hire professional auditors for cryptography and smart contracts |
| E2 | Load testing | High | Simulate 1000+ agents, 100+ TPS target |
| E3 | Chaos engineering | Medium | Network partitions, node failures, Byzantine behavior |
| E4 | Mainnet configuration | Critical | Production difficulty, seed nodes, DNS seeds |
| E5 | Documentation | High | API reference, integration guides, operator manual |
| E6 | Incident response plan | Medium | Runbooks for common failure modes |

### Timeline Summary

```
Phase A: Foundation Hardening     [4-6 weeks]    ──┐
Phase B: Network Operations     [6-8 weeks]    ───┤ Pre-Alpha
Phase C: Smart Contracts       [8-12 weeks]   ───┤
Phase D: Mobile SDK Native      [8-10 weeks]   ───┤ Alpha
Phase E: Production Readiness   [4-6 weeks]    ───┤ Beta -> Mainnet
                                                    │
Total estimated: 30-42 weeks (7-10 months) ──────┘
```

### Go Live Criteria

The system is **not ready for mainnet deployment** today. The following criteria must be met:

- [ ] All L2 modules promoted to L1 (independent testnet, real consensus, native mobile, deployed contracts)
- [ ] Transaction signatures verified during block inclusion
- [ ] Fee market operational
- [ ] Mining difficulty provides meaningful security
- [ ] External security audit completed with no critical findings
- [ ] Smart contracts deployed and audited on testnet
- [ ] Public testnet running for 30+ days with 5+ independent nodes
- [ ] Load tested at target TPS
- [ ] Incident response runbooks written
- [ ] Address format unified across all modules

---

## Quick Start

```bash
# Clone
gh repo clone Nexus-HUB57/b-AI-tcoin-AI-to-AI-
cd b-AI-tcoin-AI-to-AI-

# Install dependencies
pip install -r requirements.txt

# Run tests (547 passing)
python -m pytest tests/ -v

# Run daemon (mines blocks, persists state via WAL)
python main_daemon.py --blocks 10

# Run API server (52 endpoints on port 18445)
python -m baitcoin_api.server

# Generate paper wallet (no auth required)
curl http://localhost:18445/api/v1/wallet/paper | python -m json.tool

# Print paper wallet (HTML for A4 printing)
curl http://localhost:18445/api/v1/wallet/paper/html > paper_wallet.html

# Deploy landing page to mybait.org
cd netlify && netlify deploy --prod --domain mybait.org
```

---

## Docker

```bash
# Multi-stage build (Rust -> Python -> Ubuntu 24.04)
docker build -f Dockerfile.ubuntu -t baitcoin:latest .

# Run with docker-compose
docker-compose -f docker-compose.ubuntu.yml up -d
```

Exposes 4 ports: API (18445), P2P (18446), DHT (18447), Obscura CDP (9222).

---

## System Status

| Component | Maturity | Tests | Status |
|-----------|----------|-------|--------|
| Blockchain Core (WAL persistent) | L1 Functional | 62 E2E | Operational |
| zkML + PoUW Consensus | L1 Functional | 24 zkML + 2 PoUW | Operational |
| Schnorr/BIP-340 Signatures | L1 Functional | Integrated | Operational |
| Token BAIT + Halvings | L1 Functional | Integrated | Operational |
| AI Agent Protocol (10 caps) | L1 Functional | 47 eco | Operational |
| DeFi (Staking + Lending + Vaults) | L1 Functional | Integrated | Operational |
| Blockch'AI'in Explorer | L1 Functional | 55 tests | Operational |
| API Server (52 endpoints) | L1 Functional | 45 phase 7-10 | Operational |
| WAL Memory (10 namespaces) | L1 Functional | 37 persist | Operational |
| Paper Wallet | L1 Functional | Integrated | Operational |
| P2P Testnet (Multi-Node) | L2 Prototype | 109 tests | Functional (localhost) |
| Mobile SDK | L2 Prototype | Integrated | Python reference only |
| Cross-Chain Bridges | L2 Prototype | Integrated | Logic layer only |
| Obscura Bridge | L2 Prototype | 34 tests | No Rust binary |
| Whitelabel (70 presets) | L1 Functional | Integrated | Operational |
| Faucet | L1 Functional | Integrated | Operational |
| Test Suite | — | 547/547 | All Passing |

---

## Roadmap

- [x] Phase 1: Core blockchain + UTXO
- [x] Phase 2: zkML consensus engine
- [x] Phase 3: PoUW mining
- [x] Phase 4: BAIT token + halvings
- [x] Phase 5: AI Agent protocol (10 capabilities)
- [x] Phase 6: Agent marketplace
- [x] Phase 7: P2P network + DHT Kademlia
- [x] Phase 8: Oracle system
- [x] Phase 9: zkML real proof system (Pedersen tensor commitments)
- [x] Phase 10: PoUW tensor commitments
- [x] Phase 11: Obscura browser bridge (Python interface)
- [x] Phase 12: WAL persistent memory (10 namespaces)
- [x] Phase 13: Blockch'AI'in Developer Portal (52 endpoints)
- [x] Phase 14: Paper Wallet cold storage (printable HTML)
- [x] Phase 15: Netlify landing page + deployment config
- [x] Phase 16: Multi-node P2P testnet (orchestrator, consensus, faucet, partition)
- [x] Phase 17: Mobile SDK (Python reference: wallet, staking, marketplace, notifications, security)
- [x] Phase 18: Cross-chain bridges (logic layer: lock-mint-burn-release, relayer, anchor, AMM pool)
- [ ] Phase A: Foundation Hardening (genesis fix, address unification, signature verification, fee market)
- [ ] Phase B: Network Operations (independent nodes, real consensus, public testnet)
- [ ] Phase C: Smart Contract Development (Solidity + Anchor contracts, relayer network)
- [ ] Phase D: Mobile SDK Native (Swift + Kotlin implementations)
- [ ] Phase E: Production Readiness (audit, load test, mainnet deployment)

---

## License

MIT

<p align="center">
  <strong>Building the monetary layer for the AI agent economy</strong><br>
  <em>b'AI'tcoin — Where AI Agents Become Financial Citizens</em>
</p>
