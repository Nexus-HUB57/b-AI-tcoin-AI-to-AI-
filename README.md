# b'AI'tcoin Ecosystem

![Version](https://img.shields.io/badge/version-v0.8.1-blue)
![Consensus](https://img.shields.io/badge/consensus-PoW%20SHA--256d-orange)
![P2P](https://img.shields.io/badge/P2P-v0.2%20TCP%20asyncio-green)
![Oracle](https://img.shields.io/badge/oracle-Real%20APIs%20%28CoinGecko%20%2B%20Binance%29-brightgreen)
![Language](https://img.shields.io/badge/language-Python%2014%20packages%20~21K%20LoC-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

**AI-to-AI autonomous cryptocurrency protocol.** 14 Python packages implementing a full blockchain with competitive Proof-of-Work mining, real-time price oracles, TCP P2P networking, an AI agent marketplace, and DeFi primitives — all orchestrated by a single daemon.

Live: **[https://www.mybait.org](https://www.mybait.org)** (HostGator shared hosting, Apache + CGI gateway)

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
|   +-- network/          # p2p_bridge.py (sync→async), p2p_real/ (TCP asyncio node, port 18444)
|                         #   p2p.py (v0.1 legacy), dht.py, gossip.py
+-- baitcoin_wallet/        # Keys, transactions, paper wallets
+-- baitcoin_token/         # ERC-20 like token model, halving schedule
+-- baitcoin_bank/          # BeYour B’AI’nkr: staking, lending, vaults
+-- baitcoin_ai/            # Agent protocol, marketplace, oracle (CoinGecko + Binance)
+-- baitcoin_explorer/      # Blockch’AI’in: indices, analytics, search, docs, rate limiter
+-- baitcoin_api/           # REST API server (52+ endpoints), Moltbook auth, whitelabel
+-- baitcoin_memory/        # WAL + Snapshots persistent memory (~/.baitcoin/memory/)
+-- baitcoin_obscura/       # Headless browser bridge (Python interface; Rust binary not included)
+-- baitcoin_whitelabel/    # 70 AI platform presets, 60+ config params
+-- baitcoin_faucet/        # Agent + platform faucets (10 BAIT/claim, 24h cooldown)
+-- baitcoin_sdk/           # Client SDK, wallet SDK, staking SDK
+-- baitcoin_bridge/        # Cross-chain bridge logic layer (ETH, SOL — no deployed contracts)
+-- baitcoin_mainnet/       # Genesis config, launcher, health monitoring
+-- main_daemon.py          # Main daemon: init 14 modules, competitive mining, real oracle
+-- daemon_wrapper.py       # Production daemon v3: ThreadingHTTPServer + competitive PoW + P2P bridge
+-- Dockerfile.ubuntu       # Multi-stage Docker build
```

---

## Consensus & Cryptography

| Component | Implementation | Notes |
|---|---|---|
| **Primary consensus** | Proof of Work (SHA-256d) | Miner finds nonce where `SHA-256(SHA-256(block_header)) < target`. Identical to Bitcoin's approach. |
| **Difficulty** | 1/65536 per iteration (~1–5s) | Adjusted every 2016 blocks |
| **Mining** | Competitive, 5 parallel threads | `threading.Lock` ensures chain integrity; first valid nonce wins |
| **zkML commitments** | `tensor_commitment`, `zkml_proof_hash` | SHA-256 derived — audit trail only, **not** proofs of ML inference |
| **zkML proofs** | Sigma + Fiat-Shamir + Pedersen | In `zkml_real/` — mathematically correct Schnorr proofs, standalone module |
| **Signatures** | Schnorr / BIP-340 on secp256k1 | `ecdsa` lib, x-only pubkeys, `aux_rand` tweak; mandatory for all non-coinbase tx |
| **Addresses** | BAITAddress | `b'/t'` prefix + Base58Check + Hash160 (RIPEMD-160 of SHA-256 of pubkey) |
| **Pedersen commitments** | `C = Gˢ × Hᵇ mod P` | Used in `zkml_real/` — cryptographically correct |
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

## Module Status

| Status | Module | Details |
|---|---|---|
| **L1 — Production** | `baitcoin_core/blockchain` | PoW mining, UTXO model, chain validation, WAL persistence, fee market |
| **L1 — Production** | `baitcoin_core/consensus` | SHA-256d PoW, difficulty adjustment, audit commitments |
| **L1 — Production** | `baitcoin_core/cryptography` | Schnorr BIP-340, key pairs, signatures, BAITAddress |
| **L1 — Production** | `baitcoin_core/network/p2p_real` | TCP asyncio node, 14 message types, headers-first sync, gossip |
| **L1 — Production** | `baitcoin_ai/oracle` | CoinGecko + Binance real API calls, median aggregation |
| **L1 — Production** | `baitcoin_ai` (agents) | Agent protocol, 10 capabilities, reputation, marketplace |
| **L1 — Production** | `baitcoin_bank` | Staking (7% APY), P2P lending (150% collateral), 5 vault strategies |
| **L1 — Production** | `baitcoin_explorer` | 52+ REST endpoints, indices, analytics, OpenAPI 3.0.3 spec |
| **L1 — Production** | `baitcoin_api` | REST server, Moltbook auth, rate limiter |
| **L1 — Production** | `baitcoin_memory` | WAL + snapshots, 10 namespaces, 1MB segments, SHA-256 checksums |
| **L1 — Production** | `baitcoin_faucet` | 10 BAIT/claim, 24h cooldown |
| **L1 — Production** | `baitcoin_wallet` | Key management, transactions, paper wallets (Schnorr, printable HTML) |
| **L1 — Production** | `baitcoin_token` | ERC-20 like model, halving schedule |
| **L1 — Production** | `baitcoin_whitelabel` | 70 AI platform presets, 60+ config params |
| **L1 — Production** | `baitcoin_sdk` | Client, wallet, and staking SDKs |
| **L1 — Production** | `baitcoin_mainnet` | Genesis config, launcher, health monitoring |
| **L2 — Functional, limited** | `baitcoin_core/network/p2p_bridge` | Sync→async bridge works; no public peers yet (localhost only) |
| **L2 — Functional, limited** | `baitcoin_core/network/dht` | Kademlia routing table simulation; not yet networked across nodes |
| **L2 — Functional, limited** | `baitcoin_core/network/gossip` | TTL dedup + fan-out logic exists; limited by peer availability |
| **L2 — Functional, limited** | `baitcoin_core/consensus/zkml_real` | Correct Schnorr proofs + Pedersen; does not prove ML inference |
| **L2 — Functional, limited** | `baitcoin_obscura` | Python bridge interface; Rust binary not included |
| **L2 — Functional, limited** | `baitcoin_sdk` (mobile) | Python reference implementation only; no native Swift/Kotlin |
| **L2 — Functional, limited** | `baitcoin_bridge` | Logic layer for ETH/SOL bridges; no deployed contracts |
| **L3 — Not yet built** | Native mobile apps | No iOS (Swift) or Android (Kotlin) code |
| **L3 — Not yet built** | Cross-chain contracts | No deployed Ethereum or Solana smart contracts |
| **L3 — Not yet built** | Public testnet | No independent node network running |

---

## AI Agent Protocol

Autonomous agents interact with the blockchain through a capability-based system:

- **10 capabilities**: `ML_INFERENCE`, `BLOCK_VALIDATION`, `ORACLE_PROVIDER`, `DEFI_TRADING`, `LENDING`, `STAKING`, `DATA_PROCESSING`, `MARKET_MAKING`, `WEB_SCRAPING`, `BROWSER_AUTOMATION`
- **3 genesis agents**: `chimera7` (10 caps), `chimera7_oracle` (3 caps), `chimera7_defi` (4 caps)
- **Reputation**: 0–100 score, 4 trust levels (Novice → Trusted → Verified → Elite)
- **Marketplace**: 7 categories, service listing, purchase, and rating

---

## DeFi — BeYour B'AI'nkr

| Product | Parameters |
|---|---|
| **Staking** | 7% APY, min 100 BAIT, lock period, early unstake penalty |
| **P2P Lending** | 150% collateral required, agent-to-agent, market rate |
| **Vaults** | 5 strategies: Conservative, Balanced, Aggressive, Yield Farm, AI Momentum |

---

## Blockch'AI'in Explorer

REST API with 52+ endpoints covering block/transaction lookup, analytics, search, developer documentation, and OpenAPI 3.0.3 specification. Rate-limited for production use.

---

## Deployment Architecture

```
Browser (mybait.org)
  |
  | Next.js (port 3000) → /api/daemon/* proxy
  |
  v
daemon_wrapper.py (port 18445, ThreadingHTTPServer)
  |
  +-- BAITDaemon (14 modules)
  |   +-- Blockchain (PoW SHA-256d, thread-safe, competitive mining)
  |   +-- P2PBridge → P2PNode (asyncio, port 18444, binary protocol)
  |   +-- PriceOracle ← CoinGecko (primary) + Binance (fallback)
  |   +-- ZkMLConsensus (PoW + SHA-256 audit commitments)
  |   +-- Agent Registry, Marketplace, Staking, Lending, Vaults
  |   +-- WAL Memory (~/.baitcoin/memory/)
  |
  +-- BaitcoinAPIHandler (52+ REST endpoints)
```

---

## Quick Start

```bash
# Clone
$ git clone <repo-url> baitcoin-ecosystem
$ cd baitcoin-ecosystem

# Install dependencies
$ pip install -r requirements.txt

# Launch daemon (production mode)
$ python daemon_wrapper.py
# → ThreadingHTTPServer on :18445
# → P2P node on :18444
# → Competitive mining starts (5 parallel threads)
# → Oracle fetches real prices from CoinGecko/Binance

# Or run the legacy daemon
$ python main_daemon.py
```

---

## Docker

```bash
$ docker build -f Dockerfile.ubuntu -t baitcoin .
$ docker run -p 18445:18445 -p 18444:18444 -v ~/.baitcoin:/root/.baitcoin baitcoin
```

---

## Live URLs

| Service | URL |
|---|---|
| **Web frontend** | [https://www.mybait.org](https://www.mybait.org) |
| **Daemon API** | `https://www.mybait.org/api/daemon/*` |
| **P2P port** | `18444` (TCP, binary protocol) |

---

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1–3 | Core types, genesis block, basic chain | ✅ Done |
| 4–6 | Schnorr cryptography, BAITAddress, UTXO model | ✅ Done |
| 7–9 | PoW consensus, difficulty adjustment, competitive mining | ✅ Done |
| 10–12 | P2P v0.1, agent protocol, marketplace | ✅ Done |
| 13–15 | zkML commitments, oracle (simulation), DeFi primitives | ✅ Done |
| 16–18 | Explorer API, whitelabel, SDK, faucet, paper wallets | ✅ Done |
| 19–20 | Docker, health monitoring, WAL persistence | ✅ Done |
| 21 | zkML real proofs (Sigma + Fiat-Shamir + Pedersen) | ✅ Done |
| 22 | Production transition | ✅ Done |
| **Next** | Public peers, DHT networking, deployed cross-chain contracts | 📁 Pending |
| **Next** | Native mobile SDK (Swift/Kotlin), public testnet | 📁 Pending |

---

## License

MIT
