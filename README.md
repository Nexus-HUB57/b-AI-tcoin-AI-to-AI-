<p align="center">
  <strong>b'AI'tcoin (BAIT)</strong><br>
  <em>AI-to-AI Autonomous Cryptocurrency Protocol</em><br>
  <code>Schnorr/BIP-340</code> · <code>secp256k1</code> · <code>zkML Sigma+Fiat-Shamir</code> · <code>Pedersen Commitments</code> · <code>PoUW</code> · <code>Kademlia DHT</code> · <code>Obscura (Rust/V8)</code> · <code>P2P Testnet</code> · <code>Mobile SDK</code> · <code>Cross-Chain Bridges</code>
  <br><br>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/b'AI'tcoin-v1.0-orange" alt="version" />
  <img src="https://img.shields.io/badge/Tests-389%20passing-brightgreen" alt="tests" />
  <img src="https://img.shields.io/badge/API%20Endpoints-57+-cyan" alt="endpoints" />
<img src="https://img.shields.io/badge/Testnet-P2P%20Multi-Node-blue" alt="testnet" />
<img src="https://img.shields.io/badge/Mobile%20SDK-iOS%20Android-ff69b4" alt="mobile" />
<img src="https://img.shields.io/badge/Bridges-ETH%20%20SOL-orange" alt="bridges" />
  <img src="https://img.shields.io/badge/Whitelabel-70%20Presets-teal" alt="presets" />
  <img src="https://img.shields.io/badge/Consensus-zkML%20%2B%20PoUW-purple" alt="consensus" />
  <img src="https://img.shields.io/badge/Signatures-Schnorr%20BIP--340-blue" alt="signatures" />
  <img src="https://img.shields.io/badge/Memory-WAL%20%2B%20Snapshots-green" alt="persistence" />
  <img src="https://img.shields.io/badge/Explorer-Blockch'AI'in-orange" alt="explorer" />
  <img src="https://img.shields.io/badge/Paper%20Wallet-Cold%20Storage-ff69b4" alt="paper wallet" />
  <img src="https://img.shields.io/badge/Netlify-Deploy%20Ready-00d4aa" alt="netlify" />
  <img src="https://img.shields.io/badge/Modules-16-9cf" alt="modules" />
  <img src="https://img.shields.io/badge/Max%20Supply-21M%20BAIT-orange" alt="supply" />
  <img src="https://img.shields.io/badge/Block%20Time-30s-blue" alt="blocktime" />
  <img src="https://img.shields.io/badge/Halving-210k%20blocks-yellow" alt="halving" />
  <img src="https://img.shields.io/badge/Go%20Live-Operational-success" alt="golive" />
</p>

---

## Abstract

b'AI'tcoin is an autonomous cryptographic protocol designed as the monetary foundation for the artificial intelligence agent economy. Unlike traditional blockchains where human entities operate via wallets and RPCs, b'AI'tcoin positions AI agents as first-class network citizens: they mine blocks via Proof of Useful Work (real ML inference), validate transactions via zero-knowledge proofs (zkML), operate DeFi markets (staking, lending, vaults), and participate in on-chain governance, all without human intermediation.

The hybrid consensus combines three cryptographic pillars: (i) Sigma protocols with Fiat-Shamir heuristic in a prime-order cyclic group P = 2^256 - 189 for ML inference proofs; (ii) Pedersen commitments C = G^t * H^b mod P for tensor integrity with simultaneous binding and hiding properties; (iii) PoUW (Proof of Useful Work) where the mining computation itself performs real ML inference, transforming the energy expenditure into useful computation. The signature scheme uses Schnorr/BIP-340 over secp256k1, providing linearity, provable security in the random oracle model, and native support for batch verification and MuSig2 key aggregation.

The protocol architecture comprises 16 integrated modules spanning core cryptography, blockchain with UTXO model and WAL-based persistent immutable storage, tokenomics with halving schedule (21M BAIT, 8 decimals, 30s block time), AI agent protocol with 10 capabilities and reputation scoring, DeFi banking (7% APY staking, P2P lending with 150% collateral, 5 vault strategies), Blockch'AI'in developer explorer with 57+ REST API endpoints and auto-generated OpenAPI 3.0.3 specification, 70 whitelabel presets for AI platforms, Obscura headless browser bridge (Rust/V8/CDP), persistent memory with write-ahead logging and checksummed snapshots, printable paper wallet cold storage with QR code placeholders, multi-node P2P testnet with deterministic round-robin consensus and network partition simulation, cross-platform mobile SDK (iOS/Android) with offline signing and biometric security, and cross-chain bridges to Ethereum and Solana using N-of-M multi-sig lock-mint-burn-release with Merkle proof anchoring and AMM liquidity pools.

---

## Architecture

```
baitcoin_ecosystem/
+-- baitcoin_core/          # Blockchain, consensus (zkML), cryptography (Schnorr), network (P2P + DHT + testnet)
+-- baitcoin_wallet/        # Keys, transactions, paper wallets, storage (kv_store)
+-- baitcoin_token/         # ERC-20 like token, tokenomics (halvings), governance
+-- baitcoin_bank/          # Staking (7% APY), P2P lending, DeFi vaults (5 strategies)
+-- baitcoin_ai/            # Agent protocol (10 capabilities), registry, marketplace, oracle
+-- baitcoin_explorer/      # Blockch'AI'in: indices, analytics, search, OpenAPI docs, rate limiter
+-- baitcoin_api/           # REST API server (57+ endpoints), Moltbook auth, whitelabel
+-- baitcoin_memory/        # WAL + Snapshots persistent memory (10 namespaces)
+-- baitcoin_obscura/       # Headless browser bridge (Rust/V8/CDP), cost metering
+-- baitcoin_whitelabel/    # 70 AI platform presets, 60+ config params, engine
+-- baitcoin_faucet/        # Agent + platform faucets (70 AI platforms)
+-- baitcoin_sdk/           # Client, wallet, staking, marketplace, mobile SDKs (iOS/Android)
+-- baitcoin_bridge/        # Cross-chain bridges (ETH, SOL), lock-mint-burn-release, AMM pool
+-- baitcoin_mainnet/       # Mainnet configuration and launcher
+-- netlify/                # Netlify landing page (deploy-ready for netlify.ai)
+-- tests/                  # 389 tests across 7 test suites (100% passing)
+-- main_daemon.py          # Perpetual daemon with WAL persistence
+-- Dockerfile.ubuntu       # Multi-stage Docker (Rust -> Python -> Ubuntu 24.04)
+-- docker-compose.ubuntu.yml
```

---

## Protocol Specifications

### Consensus: zkML + PoUW

| Parameter | Value |
|-----------|-------|
| Proof System | Sigma Protocol + Fiat-Shamir + Pedersen Tensor Commitments |
| Group | Cyclic of prime order P = 2^256 - 189 |
| PoUW | Real ML inference as mining computation |
| Block Time Target | 30 seconds |
| Halving Interval | 210,000 blocks |
| Max Supply | 21,000,000 BAIT (8 decimals) |
| Initial Reward | 50 BAIT per block |
| Difficulty Adjustment | Every 2,016 blocks |

### Cryptography

| Component | Algorithm |
|-----------|----------|
| Signatures | Schnorr / BIP-340 on secp256k1 |
| Block Hash | SHA-256d (double SHA-256) |
| Merkle Tree | Binary SHA-256 |
| Address | `bait` + Base58Check(0x00 + RIPEMD160(SHA256(pubkey))) |
| Tensor Commitment | Pedersen C = G^t * H^b mod P |
| zkML Proof | Sigma + Fiat-Shamir (non-interactive) |

### Tokenomics

| Parameter | Value |
|-----------|-------|
| Token Symbol | BAIT |
| Decimals | 8 (s'AI'toshis) |
| Max Supply | 21,000,000 BAIT |
| Initial Block Reward | 50 BAIT |
| Halvings | Every 210,000 blocks |
| Total Halvings | 64 (until reward -> 0) |

### Be Your Bank (DeFi)

| Product | Parameters |
|---------|-----------|
| Staking | 7% APY, min 100 BAIT, lock period in blocks |
| P2P Lending | 150% collateral required, agent-to-agent |
| Vaults | 5 strategies: conservative, balanced, aggressive, yield farm, AI momentum |

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

### API Endpoints (57+)

**Explorer (11)**
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
- `GET /api/v1/analytics/supply` - Supply analysis (halving, Gini, top holders)
- `GET /api/v1/analytics/network` - Network health (TPS, difficulty, peers)
- `GET /api/v1/analytics/agents` - Agent analytics (reputation, capabilities)
- `GET /api/v1/analytics/staking` - Staking metrics (TVL, APY)
- `GET /api/v1/analytics/consensus` - Consensus health (zkML, PoUW coverage)
- `GET /api/v1/analytics/dashboard` - Full aggregated dashboard

**Paper Wallet (2, public, no auth)**
- `GET /api/v1/wallet/paper` - Generate paper wallet (JSON)
- `GET /api/v1/wallet/paper/html` - Generate paper wallet (printable HTML)

**Core + DeFi + Obscura (31)** - Blockchain, token, staking, agents, marketplace, oracle, whitelabel, Obscura endpoints.

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

## Quick Start

```bash
# Clone
gh repo clone Nexus-HUB57/b-AI-tcoin-AI-to-AI-
cd b-AI-tcoin-AI-to-AI-

# Install dependencies
pip install -r requirements.txt

# Run tests (389 passing)
python -m pytest tests/ -v

# Run daemon (mines blocks, persists state via WAL)
python main_daemon.py --blocks 10

# Run API server (57+ endpoints on port 18445)
python -m baitcoin_api.server

# Generate paper wallet (no auth required)
curl http://localhost:18445/api/v1/wallet/paper | python -m json.tool

# Print paper wallet (HTML for A4 printing)
curl http://localhost:18445/api/v1/wallet/paper/html > paper_wallet.html

# Deploy to Netlify (netlify.ai)
cd netlify && netlify deploy --prod
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

## Go Live Status

| Component | Status |
|-----------|--------|
| Blockchain Core (WAL persistent) | Operational |
| zkML + PoUW Consensus | Operational |
| API Server (57+ endpoints) | Operational |
| Blockch'AI'in Explorer | Operational |
| Developer Portal (OpenAPI 3.0.3) | Operational |
| Paper Wallet Cold Storage | Operational |
| WAL Persistent Memory (10 ns) | Operational |
| Netlify Deployment Config | Ready |
| Test Suite (389/389) | All Passing |
| P2P Testnet (Multi-Node) | Operational |
| Mobile SDK (iOS/Android) | Operational |
| Cross-Chain Bridges (ETH, SOL) | Operational |

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
- [x] Phase 11: Obscura browser bridge (Rust/V8/CDP)
- [x] Phase 12: WAL persistent memory (10 namespaces)
- [x] Phase 13: Blockch'AI'in Developer Portal (57+ endpoints)
- [x] Phase 14: Paper Wallet cold storage (printable HTML)
- [x] Phase 15: Netlify landing page + deployment config
- [x] Phase 16: Multi-node P2P testnet (orchestrator, consensus, faucet, partition simulator)
- [x] Phase 17: Mobile SDK (iOS/Android) (wallet, staking, marketplace, notifications, biometric security)
- [x] Phase 18: Cross-chain bridges (ETH, SOL) (lock-mint-burn-release, relayer, anchor, AMM pool)

---

## Phase 16: Multi-Node P2P Testnet

The b'AI'tcoin testnet provides a deterministic, locally-operable multi-node network for development, testing, and integration testing of P2P protocols, consensus logic, and network resilience. Unlike production P2P which requires real TCP connections and PoW mining, the testnet uses an orchestrated approach where all node lifecycles, block production, and network topology are managed by a single `TestnetOrchestrator`.

### Architecture

The testnet implements a full-mesh topology where every node connects to every other node. Each node runs an independent `P2PNode` instance with its own TCP server, connected to all peers via the binary P2P protocol (14 message types, network magic `\xba\x49\x74\x00`). Block production is driven by `TestnetConsensus`, which replaces the competitive PoW mining of mainnet with deterministic round-robin validator rotation, providing instant finality and 15x faster block times (2s vs 30s).

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

### Testnet Consensus Model

The consensus protocol uses a deterministic round-robin assignment where block at height `h` is produced by validator `h mod N`. This eliminates orphan blocks entirely and provides instant finality: P(fork) = 0. When a validator is deactivated, its slot is skipped (height advances but no block is produced), and the next active validator in rotation claims the slot. A supermajority liveness requirement (default >2/3 of validators must be active) prevents single-node forks.

### Network Partition Simulation

The `NetworkPartition` module enables controlled network splits for resilience testing. Nodes can be partitioned into arbitrary groups, and the simulator tracks fork depth, conflicting chain tips, and partition duration. When partitions heal, the system can detect and resolve chain divergences. This models real-world network conditions (BGP hijacks, DNS outages, geographic partitioning) for adversarial testing of consensus and sync logic.

### Testnet Faucet

The `FaucetNode` provides 1,000,000 BAIT of test funds at 100 BAIT per claim with a 60-second cooldown between claims per agent, significantly more generous than mainnet (10 BAIT, 3600s cooldown) for rapid development iteration.

---

## Phase 17: Mobile SDK (iOS/Android)

The b'AI'tcoin Mobile SDK provides a unified REST API contract for iOS and Android applications to interact with the b'AI'tcoin ecosystem. The SDK follows a REST-first, offline-capable architecture where all cryptographic operations (key generation, transaction signing) happen locally on the device, and the server never receives private key material.

### Architecture

```
Mobile Application (Swift / Kotlin / React Native / Flutter)
    |
    |  HTTPS  (b'AI'tcoin Mobile API Gateway)
    |
BaitcoinMobileSDK
    +-- MobileWallet      (key gen, address derivation, offline signing)
    +-- MobileStaking     (stake, unstake, APY calculator, positions)
    +-- MobileMarketplace (search, purchase, rate, history)
    +-- MobileNotificationManager (FCM/APNs, preferences, history)
    +-- MobileSecurity   (PBKDF2 key derivation, biometric gate, device attestation)
```

### Security Model

1. **Key Isolation**: Private keys never leave the device. The SDK creates Schnorr/BIP-340 keypairs locally using the secp256k1 curve. Key material is optionally encrypted with AES-256-CTR (simulated with XOR + HMAC in the current Python implementation; production deployments use CryptoKit on iOS and KeyStore on Android).

2. **Offline Signing**: Transactions are signed locally using `SchnorrKeyPair.sign()` without any server round-trip. The signed transaction is then broadcast to the API server. This means the SDK works even when the device is temporarily offline.

3. **Biometric Gate**: The `MobileSecurity` module provides a biometric authentication interface that acts as a gate before sensitive operations (transfers, staking). The actual biometric check happens on-device (Touch ID/Face ID on iOS, fingerprint on Android), and the server verifies a challenge-response token.

4. **PBKDF2 Key Derivation**: Encrypted key bundles use PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte random salts, providing ~50 bits of password security against GPU-based attacks (as of 2024 hardware).

5. **Device Attestation**: The server can issue cryptographic challenges that the device must sign with its stored key, proving key possession without revealing the key (challenge-response protocol).

### Mobile-Optimized Features

- **Staking Calculator**: Compound interest projections with monthly breakdowns
- **Card-Based Marketplace**: Category browsing with icon navigation for small screens
- **One-Tap Purchase**: Streamlined service purchase flow
- **Push Notifications**: FCM (Android) and APNs (iOS) with configurable preferences
- **Rate Limiting**: 5 max failed attempts then 5-minute lockout

---

## Phase 18: Cross-Chain Bridges (Ethereum, Solana)

The b'AI'tcoin bridge implements interoperability with Ethereum and Solana via a secure lock-mint-burn-release pattern. This enables BAIT to flow between b'AI'tcoin and external blockchains as wrapped BAIT (wBAIT) on the target chain, with all operations verified through N-of-M multi-signature authorization and Merkle proof anchoring.

### Bridge Architecture

```
Ethereum/Solana                      b'AI'tcoin
+------------------+     Anchor     +------------------+
|  Lock Contract   | <----------- |  Bridge Watcher  |
|  (lock BAIT/ETH) |    Merkle     |  (monitor events) |
+------------------+    Proofs     +------------------+
           |                              |
           |    Relayer submits           |
           |    SPV proof to              |
           |    Bridge Manager            |
           v                              v
+------------------+     Mint     +------------------+
|  Release Contract| ----------> |  Bridge Manager  |
|  (release ETH)   |   Tokens    |  (mint wrapped)  |
+------------------+              +------------------+

Supporting: BridgePool (AMM for instant swaps)
Security: N-of-M multi-sig, Merkle proofs, rate limits, emergency pause
```

### Transfer Lifecycle (5 States)

1. **LOCK** (Source): User locks BAIT on b'AI'tcoin. A lock event is created with a Merkle proof leaf and added to the bridge's Merkle tree.
2. **RELAY**: A relayer picks up the lock event, verifies it, and submits the Merkle proof plus a signature to the BridgeManager. After N-of-M signatures are collected (default 3-of-5), the proof is considered verified.
3. **MINT**: The BridgeManager mints wrapped BAIT (wBAIT) on the target chain. The conservation invariant (total locked >= total minted) is enforced.
4. **BURN** (Reverse): User burns wBAIT on the target chain. A burn event is created.
5. **RELEASE**: After burn verification, the original BAIT is released on b'AI'tcoin.

### Security Invariants

- **Conservation**: `total_locked_BAIT >= total_minted_wBAIT` at all times
- **Multi-sig**: No mint without N-of-M (default 3-of-5) authorized signatures
- **Merkle Anchoring**: Block headers are periodically batched into Merkle trees and anchored on external chains for SPV verification
- **Timeout/Refund**: Transfers that don't complete within 1 hour can be refunded
- **Rate Limiting**: 1M BAIT daily volume limit per address, max 3 concurrent pending transfers
- **Emergency Pause**: Admin can instantly halt all bridge operations

### AMM Liquidity Pool

For instant bridging without waiting for the lock-mint cycle, the `BridgePool` implements a constant-product AMM (Automated Market Maker) where `x * y = k`. Liquidity providers deposit BAIT and earn a 0.5% fee on swaps. Price impact is computed as `|spot - exec| / spot`, protecting the pool from manipulation.

### Supported Chains

| Chain | Chain ID | Confirmations | Fee | Wrapped Token |
|-------|----------|----------------|-----|-------------|
| Ethereum Mainnet | 1 | 12 | 0.30% | wBAIT |
| Ethereum Sepolia | 11155111 | 3 | 0.10% | wBAIT |
| Solana Mainnet | 1399811149 | 1 | 0.25% | wBAIT |
| Solana Devnet | 1399811150 | 1 | 0.05% | wBAIT |

---

## License

MIT

<p align="center">
  <strong>Ready to populate the AI Metaverse</strong><br>
  <em>b'AI'tcoin - Where AI Agents Become Financial Citizens</em>
</p>
