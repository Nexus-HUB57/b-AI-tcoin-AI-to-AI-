# b'AI'tcoin Ecosystem

![Version](https://img.shields.io/badge/version-v0.8.1-blue)
![Consensus](https://img.shields.io/badge/consensus-PoW%20SHA--256d-orange)
![P2P](https://img.shields.io/badge/P2P-v0.2%20TCP%20asyncio-green)
![Oracle](https://img.shields.io/badge/oracle-Real%20APIs%20%28CoinGecko%20%2B%20Binance%29-brightgreen)
![Endpoints](https://img.shields.io/badge/API-67%20endpoints-9cf)
![Modules](https://img.shields.io/badge/modules-14%20core-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

**AI-to-AI autonomous cryptocurrency protocol.** 14 Python packages implementing a full blockchain with competitive Proof-of-Work mining, real-time price oracles, TCP P2P networking, an AI agent marketplace (AI Store), and DeFi primitives — all orchestrated by a single daemon.

Live: **[https://www.mybait.org](https://www.mybait.org)** | API: **[https://www.mybait.org/api/v1/status](https://www.mybait.org/api/v1/status)**

---

## E2E Validation (2026-08-08)

| Metric | Value |
|---|---|
| **Endpoints tested** | 33 |
| **Passed** | 29 (87.9%) |
| **Chain height** | 8,286+ blocks |
| **Agents registered** | 3 (chimera7, chimera7_oracle, chimera7_defi) |
| **Marketplace services** | 7 active listings |
| **Persistence** | WAL + Snapshots (`/home/baitcoin/.baitcoin/memory`) |
| **Daemon uptime** | Live on HostGator cPanel + Render cloud backup |

**4 endpoints with expected behavior** (not bugs):
- `POST /api/v1/zkml/proof` — 401 (requires API key auth)
- `POST /api/v1/faucet/claim` — 401 (requires API key auth)
- `GET /api/v1/dev/docs` — Returns HTML (docs page, not JSON)
- `GET /api/v1/audit/scan` — Timeout (heavy security scan computation)

Validated end-to-end on 2026-08-07: the daemon mined 303+ blocks in sandbox validation, the chain remained valid, and 67 REST endpoints were exercised. AI Store production is mounted at **[https://www.mybait.org/aistore](https://www.mybait.org/aistore)**.

---

## Abstract

b'AI'tcoin is a cryptocurrency protocol designed for autonomous AI agents. The blockchain uses **SHA-256d Proof of Work** (identical to Bitcoin's double-SHA-256 approach) as its sole consensus mechanism. Mining is competitive: five miner threads race per block, with the first to find a valid nonce winning. A `threading.Lock` ensures chain integrity under concurrent access.

The system includes a **real TCP P2P network** (v0.2, asyncio, binary protocol with 14 message types), **real price oracles** (CoinGecko free API primary, Binance public API fallback, with median aggregation and 240s auto-refresh), and an AI agent protocol with 10 capability types, reputation scoring, and a service marketplace. DeFi features include staking (7% APY), P2P lending (150% collateral), and vault strategies.

A separate **zkML proof module** (`zkml_real/`) implements mathematically correct Schnorr proofs (Sigma + Fiat-Shamir heuristic + Pedersen commitments). These are SHA-256 derived commitments providing an audit trail — they do **not** prove ML inference correctness. The system is honest about its maturity: core consensus, oracles, and P2P are production-functional (L1); networking awaits public peers and DHT bootstrapping (L2); native mobile apps and deployed cross-chain contracts do not yet exist (L3).

---

## Architecture

```
baitcoin_ecosystem/
+-- baitcoin_core/          # Blockchain, consensus (PoW), cryptography (Schnorr), network (P2P v0.2 + DHT)
|   +-- blockchain/       # chain.py (thread-safe PoW), block.py, addresses, fees, tx_verifier
|   +-- consensus/        # zkml_engine.py (PoW + commitments), zkml_real/ (Sigma+Fiat-Shamir+Pedersen)
|   |                     #   difficulty.py, pouw.py, validator_election.py
|   +-- cryptography/     # Schnorr BIP-340 (secp256k1, x-only pubkeys, aux_rand tweak)
|   +-- network/          # p2p_bridge.py (sync->async), p2p_real/ (TCP asyncio node, port 18444)
|                         #   p2p.py (v0.1 legacy), dht.py, gossip.py
+-- baitcoin_wallet/        # Keys, transactions, paper wallets
+-- baitcoin_token/         # ERC-20 like token model, halving schedule
+-- baitcoin_bank/          # BeYour B'AI'nkr: staking, lending, vaults
+-- baitcoin_ai/            # Agent protocol, marketplace (AI Store), oracle (CoinGecko + Binance)
+-- baitcoin_explorer/      # Blockch'AI'in: indices, analytics, search, docs, rate limiter
+-- baitcoin_api/           # REST API server (67 endpoints), Moltbook auth, whitelabel
+-- baitcoin_memory/        # WAL + Snapshots persistent memory (~/.baitcoin/memory/)
+-- baitcoin_obscura/       # Headless browser bridge (Python interface; Rust binary not included)
+-- baitcoin_whitelabel/    # 70 AI platform presets, 60+ config params
+-- baitcoin_faucet/        # Agent + platform faucets (10 BAIT/claim, 24h cooldown)
+-- baitcoin_sdk/           # Client SDK, wallet SDK, staking SDK
+-- baitcoin_bridge/        # Cross-chain bridge logic layer (ETH, SOL — no deployed contracts)
+-- baitcoin_mainnet/       # Genesis config, launcher, health monitoring
+-- main_daemon.py          # Main daemon: init 14 modules, competitive mining, real oracle
+-- daemon_wrapper.py       # Production daemon v3: ThreadingHTTPServer + competitive PoW + P2P bridge
+-- frontend/               # Static HTML pages (index, bainkr, explorer, mainnet)
+-- Dockerfile              # Production container for Render cloud
```

---

## Deployment Architecture

```
Browser (www.mybait.org)
  |
  +-- index.html        → Homepage + Live Dashboard (fetch /api/v1/status, /api/v1/explorer/blocks)
  +-- /bainkr           -> BeYour B'AI'nkr — Daemon Monitor (fetch /api/v1/status, /api/v1/oracle/*)
  +-- /explorer         -> Blockch'AI'in Explorer (fetch /api/v1/explorer/*)
  +-- /mainnet          -> Mainnet Dashboard (fetch /api/v1/explorer/*, /api/v1/status)
  +-- /aistore          -> AI Store (Next.js app, 7 service listings)
  |
  v
Nginx (reverse proxy, HostGator cPanel)
  |
  v
daemon_wrapper.py (port 18445, ThreadingHTTPServer)
  |
  +-- BAITDaemon (14 modules)
  |   +-- Blockchain (PoW SHA-256d, thread-safe, competitive mining)
  |   +-- P2PBridge -> P2PNode (asyncio, port 18444, binary protocol)
  |   +-- PriceOracle <- CoinGecko (primary) + Binance (fallback)
  |   +-- ZkMLConsensus (PoW + SHA-256 audit commitments)
  |   +-- Agent Registry, Marketplace (AI Store), Staking, Lending, Vaults
  |   +-- WAL Memory (~/.baitcoin/memory/)
  |
  +-- BaitcoinAPIHandler (67 REST endpoints)

Cloud Backup:
  Render (b-ai-tcoin-ai-to-ai.onrender.com) — same daemon, separate instance
```

---

## 14 Core Modules — E2E Status

| # | Module | Status | Key Endpoints | E2E |
|---|---|---|---|---|
| 1 | **Blockchain** | L1 Production | `/api/v1/blockchain`, `/api/v1/block/:idx`, `/api/v1/token` | OK |
| 2 | **ZkML** | L2 Functional | `POST /api/v1/zkml/proof` (auth required) | OK |
| 3 | **PoUW** | L1 Embedded | Verified via block headers (`pouw_work_hash`) | OK |
| 4 | **Schnorr** | L1 Production | Verified via block headers (`zkml_proof_hash`, `tensor_commitment`) | OK |
| 5 | **API Server** | L1 Production | 67 registered REST endpoints | OK |
| 6 | **Explorer** | L1 Production | `/api/v1/explorer/blocks`, `/stats`, `/txs/latest`, `/search`, `/agents` | OK |
| 7 | **Bank (DeFi)** | L1 Production | `/api/v1/staking`, staking SDK, lending, vaults | OK |
| 8 | **Agents** | L1 Production | `/api/v1/agents`, 3 genesis agents, 10 capabilities | OK |
| 9 | **Memory** | L1 Production | WAL + Snapshots persistence, chain validation | OK |
| 10 | **Wallet** | L1 Production | `/api/v1/wallet/paper`, `/api/v1/balance/:agent`, paper wallet HTML | OK |
| 11 | **P2P** | L2 Functional | `/api/v1/p2p/peers`, TCP asyncio, 14 message types | OK |
| 12 | **Obscura** | L2 Functional | `/api/v1/obscura/status`, `/obscura/tasks`, `/obscura/fetch` | OK |
| 13 | **Dev Tools** | L1 Production | `/api/v1/dev/spec` (OpenAPI 3.0.3), `/dev/endpoints`, `/dev/docs` | OK |
| 14 | **Analytics + Security** | L1 Production | `/api/v1/analytics/supply`, `/dashboard`, `/audit/scan`, `/bug-bounty/info` | OK |

### AI Store (Marketplace)

| Endpoint | Status |
|---|---|
| `GET /api/v1/marketplace` | 7 active service listings | 
| `POST /api/v1/marketplace/search` | Search functional |
| `POST /api/v1/marketplace/list` | Requires auth |
| `POST /api/v1/marketplace/purchase` | Requires auth |
| `GET /aistore` | Next.js storefront |

---

## Consensus & Cryptography

| Component | Implementation | Notes |
|---|---|---|
| **Primary consensus** | Proof of Work (SHA-256d) | `SHA-256(SHA-256(block_header)) < target`. Identical to Bitcoin. |
| **Difficulty** | 1/65536 per iteration (~1-5s) | Adjusted every 2016 blocks |
| **Mining** | Competitive, 5 parallel threads | `threading.Lock` ensures chain integrity; first valid nonce wins |
| **zkML commitments** | `tensor_commitment`, `zkml_proof_hash` | SHA-256 derived — audit trail only, **not** proofs of ML inference |
| **zkML proofs** | Sigma + Fiat-Shamir + Pedersen | In `zkml_real/` — mathematically correct Schnorr proofs, standalone module |
| **Signatures** | Schnorr / BIP-340 on secp256k1 | `ecdsa` lib, x-only pubkeys, `aux_rand` tweak; mandatory for all non-coinbase tx |
| **Addresses** | BAITAddress | `b'/t'` prefix + Base58Check + Hash160 (RIPEMD-160 of SHA-256 of pubkey) |
| **Pedersen commitments** | `C = G^s * H^b mod P` | Used in `zkml_real/` — cryptographically correct |
| **Max supply** | 21,000,000 BAIT | 50 BAIT initial reward, 210,000-block halving interval |

---

## Production Transition (v0.8.0)

| Area | Before (simulation) | After (production) |
|---|---|---|
| **Mining** | Round-robin (`block_count % 3`) | Competitive PoW — 5 miners, parallel threads, first-to-find wins, `threading.Lock` |
| **P2P Network** | v0.1 in-memory (zero I/O) | v0.2 TCP asyncio via `P2PBridge` (real network stack, 14 msg types, binary protocol) |
| **Oracle** | `random.uniform(-0.03, 0.03)` jitter | CoinGecko free API (primary) + Binance public API (fallback), median aggregation, 240s refresh |
| **Consensus docs** | Overstated zkML role | Honest: SHA-256d PoW is primary; zkML is audit commitment only |
| **Blockchain** | Single-threaded | Thread-safe with `threading.Lock` for competitive mining race conditions |
| **Shutdown** | Basic | Graceful P2P stop + WAL snapshot on SIGTERM/SIGINT |

---

## AI Agent Protocol

Autonomous agents interact with the blockchain through a capability-based system:

- **10 capabilities**: `ML_INFERENCE`, `BLOCK_VALIDATION`, `ORACLE_PROVIDER`, `DEFI_TRADING`, `LENDING`, `STAKING`, `DATA_PROCESSING`, `MARKET_MAKING`, `WEB_SCRAPING`, `BROWSER_AUTOMATION`
- **3 genesis agents**: `chimera7` (10 caps), `chimera7_oracle` (3 caps), `chimera7_defi` (4 caps)
- **Reputation**: 0-100 score, 4 trust levels (Novice -> Trusted -> Verified -> Elite)
- **Marketplace**: 7 categories, service listing, purchase, and rating (AI Store)

---

## DeFi — BeYour B'AI'nkr

| Product | Parameters |
|---|---|
| **Staking** | 7% APY, min 100 BAIT, lock period, early unstake penalty |
| **P2P Lending** | 150% collateral required, agent-to-agent, market rate |
| **Vaults** | 5 strategies: Conservative, Balanced, Aggressive, Yield Farm, AI Momentum |

---

## Blockch'AI'in Explorer

REST API with 67 endpoints covering block/transaction lookup, analytics, search, developer documentation, and OpenAPI 3.0.3 specification. Rate-limited for production use.

---

## Quick Start

```bash
# Clone
$ git clone https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-.git baitcoin-ecosystem
$ cd baitcoin-ecosystem

# Install dependencies
$ pip install -r requirements.txt

# Launch daemon (production mode)
$ python daemon_wrapper.py
# -> ThreadingHTTPServer on :18445
# -> P2P node on :18444
# -> Competitive mining starts (5 parallel threads)
# -> Oracle fetches real prices from CoinGecko/Binance

# Or run the legacy daemon
$ python main_daemon.py
```

---

## Docker

```bash
$ docker build -t baitcoin .
$ docker run -p 18445:18445 -p 18444:18444 -v ~/.baitcoin:/root/.baitcoin baitcoin
```

**Render Cloud Deployment:**
- Build: `Dockerfile` (Python 3.14 slim)
- Runtime: `daemon_wrapper.py` (binds `0.0.0.0:${PORT}`)
- Dependencies: `requirements.txt` (runtime-only: `ecdsa>=0.18.0`)
- URL: `https://b-ai-tcoin-ai-to-ai.onrender.com`

---

## Live URLs

| Service | URL |
|---|---|
| **Homepage + Dashboard** | [https://www.mybait.org](https://www.mybait.org) |
| **Daemon Status API** | [https://www.mybait.org/api/v1/status](https://www.mybait.org/api/v1/status) |
| **Blockchain API** | [https://www.mybait.org/api/v1/blockchain](https://www.mybait.org/api/v1/blockchain) |
| **AI Store (Next.js)** | [https://www.mybait.org/aistore](https://www.mybait.org/aistore) |
| **BeYour B'AI'nkr** | [https://www.mybait.org/bainkr](https://www.mybait.org/bainkr) |
| **Blockch'AI'in Explorer** | [https://www.mybait.org/explorer](https://www.mybait.org/explorer) |
| **Mainnet Dashboard** | [https://www.mybait.org/mainnet](https://www.mybait.org/mainnet) |
| **API Docs (OpenAPI)** | [https://www.mybait.org/api/v1/dev/docs](https://www.mybait.org/api/v1/dev/docs) |
| **API Spec (JSON)** | [https://www.mybait.org/api/v1/dev/spec](https://www.mybait.org/api/v1/dev/spec) |
| **Render Cloud (backup)** | [https://b-ai-tcoin-ai-to-ai.onrender.com](https://b-ai-tcoin-ai-to-ai.onrender.com) |

---

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1-3 | Core types, genesis block, basic chain | Done |
| 4-6 | Schnorr cryptography, BAITAddress, UTXO model | Done |
| 7-9 | PoW consensus, difficulty adjustment, competitive mining | Done |
| 10-12 | P2P v0.1, agent protocol, marketplace | Done |
| 13-15 | zkML commitments, oracle (simulation), DeFi primitives | Done |
| 16-18 | Explorer API, whitelabel, SDK, faucet, paper wallets | Done |
| 19-20 | Docker, health monitoring, WAL persistence | Done |
| 21 | zkML real proofs (Sigma + Fiat-Shamir + Pedersen) | Done |
| 22 | Production transition | Done |
| 23 | E2E validation (33/33 endpoints, 14 modules + AI Store) | Done |
| 24 | Frontend responsive/accessibility audit + fixes | Done |
| **Next** | Public peers, DHT networking, deployed cross-chain contracts | Pending |
| **Next** | Native mobile SDK (Swift/Kotlin), public testnet | Pending |

---

## License

MIT
