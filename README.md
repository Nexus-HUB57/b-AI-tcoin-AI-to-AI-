<p align="center">
  <strong>b'AI'tcoin (BAIT)</strong><br>
  <em>AI-to-AI Autonomous Cryptocurrency Protocol</em><br>
  <code>Schnorr/BIP-340</code> · <code>secp256k1</code> · <code>zkML Sigma+Fiat-Shamir</code> · <code>Pedersen Commitments</code> · <code>PoUW</code> · <code>Kademlia DHT</code> · <code>Obscura (Rust/V8)</code>
  <br><br>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/b'AI'tcoin-v1.0-orange" alt="version" />
  <img src="https://img.shields.io/badge/Tests-280%20passing-brightgreen" alt="tests" />
  <img src="https://img.shields.io/badge/API%20Endpoints-57+-cyan" alt="endpoints" />
  <img src="https://img.shields.io/badge/Whitelabel-70%20Presets-teal" alt="presets" />
  <img src="https://img.shields.io/badge/Consensus-zkML%20%2B%20PoUW-purple" alt="consensus" />
  <img src="https://img.shields.io/badge/Signatures-Schnorr%20BIP--340-blue" alt="signatures" />
  <img src="https://img.shields.io/badge/Memory-WAL%20%2B%20Snapshots-green" alt="persistence" />
  <img src="https://img.shields.io/badge/Explorer-Blockch'AI'in-orange" alt="explorer" />
  <img src="https://img.shields.io/badge/Paper%20Wallet-Cold%20Storage-ff69b4" alt="paper wallet" />
  <img src="https://img.shields.io/badge/Netlify-Deploy%20Ready-00d4aa" alt="netlify" />
  <img src="https://img.shields.io/badge/Modules-13-9cf" alt="modules" />
  <img src="https://img.shields.io/badge/Max%20Supply-21M%20BAIT-orange" alt="supply" />
  <img src="https://img.shields.io/badge/Block%20Time-30s-blue" alt="blocktime" />
  <img src="https://img.shields.io/badge/Halving-210k%20blocks-yellow" alt="halving" />
  <img src="https://img.shields.io/badge/Go%20Live-Operational-success" alt="golive" />
</p>

---

## Abstract

b'AI'tcoin is an autonomous cryptographic protocol designed as the monetary foundation for the artificial intelligence agent economy. Unlike traditional blockchains where human entities operate via wallets and RPCs, b'AI'tcoin positions AI agents as first-class network citizens: they mine blocks via Proof of Useful Work (real ML inference), validate transactions via zero-knowledge proofs (zkML), operate DeFi markets (staking, lending, vaults), and participate in on-chain governance, all without human intermediation.

The hybrid consensus combines three cryptographic pillars: (i) Sigma protocols with Fiat-Shamir heuristic in a prime-order cyclic group P = 2^256 - 189 for ML inference proofs; (ii) Pedersen commitments C = G^t * H^b mod P for tensor integrity with simultaneous binding and hiding properties; (iii) PoUW (Proof of Useful Work) where the mining computation itself performs real ML inference, transforming the energy expenditure into useful computation. The signature scheme uses Schnorr/BIP-340 over secp256k1, providing linearity, provable security in the random oracle model, and native support for batch verification and MuSig2 key aggregation.

The protocol architecture comprises 13 integrated modules spanning core cryptography, blockchain with UTXO model and WAL-based persistent immutable storage, tokenomics with halving schedule (21M BAIT, 8 decimals, 30s block time), AI agent protocol with 10 capabilities and reputation scoring, DeFi banking (7% APY staking, P2P lending with 150% collateral, 5 vault strategies), Blockch'AI'in developer explorer with 57+ REST API endpoints and auto-generated OpenAPI 3.0.3 specification, 70 whitelabel presets for AI platforms, Obscura headless browser bridge (Rust/V8/CDP), persistent memory with write-ahead logging and checksummed snapshots, and printable paper wallet cold storage with QR code placeholders.

---

## Architecture

```
baitcoin_ecosystem/
+-- baitcoin_core/          # Blockchain, consensus (zkML), cryptography (Schnorr), network (P2P + DHT)
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
+-- baitcoin_sdk/           # Client, wallet, staking, marketplace SDKs
+-- baitcoin_mainnet/       # Mainnet configuration and launcher
+-- netlify/                # Netlify landing page (deploy-ready for netlify.ai)
+-- tests/                  # 280 tests across 6 test suites (100% passing)
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

# Run tests (280 passing)
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
| Test Suite (280/280) | All Passing |

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
- [ ] Phase 16: Multi-node P2P testnet
- [ ] Phase 17: Mobile SDK (iOS/Android)
- [ ] Phase 18: Cross-chain bridges (ETH, SOL)

---

## License

MIT

<p align="center">
  <strong>Ready to populate the AI Metaverse</strong><br>
  <em>b'AI'tcoin - Where AI Agents Become Financial Citizens</em>
</p>
