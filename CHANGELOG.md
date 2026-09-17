# Changelog

All notable changes to the b'AI'tcoin (BAIT) ecosystem will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] — 2026-08-02

### Added
- **Whitepaper**: Academic-grade whitepaper (19 pages, 9 chapters, 15 references) published to `docs/whitepaper/`
  - Covers zkML Sigma+Fiat-Shamir proofs, PoUW mining, Schnorr/BIP-340 signatures
  - Formal proof sketches: Completeness, Special Soundness, Honest-Verifier ZK
  - 5 tables: block parameters, halving schedule, PoUW hash chain, API taxonomy, AI agent capabilities
- **CHANGELOG.md**: Project changelog initialized
- **LICENSE**: MIT license added
- **CONTRIBUTING.md**: Contribution guidelines established
- **ROADMAP.md**: Comprehensive Go Live launch roadmap (5 phases, 30+ milestones)
- **.gitignore**: Proper Python, IDE, and runtime data exclusions
- **Enhanced Stress Tests**: 30 tests covering mining extremes, 5000 zkML proofs, mempool 50K tx fill
- **Enhanced Smoke Tests**: 52 tests covering edge cases across all 10 subsystems
- **E2E Comprehensive Validation**: 30-point automated validation script

### Fixed
- README badge 404 errors (URL encoding of apostrophes in `b'AI'tcoin` and `Blockch'AI'in`)
- README metrics accuracy: tests 465→547, modules 16→14, LOC 22,234→20,314, files 85→95
- Server docstring: endpoint count 55→52 (Core 25, Explorer 12, DevTools 7)
- Mempool O(n² log n) performance → O(n log n) via `bisect.insort`
- `p2p.py`: misplaced `import os` moved to module top
- Genesis block non-deterministic timestamp (fixed to 1700000000.0)
- Block deserialization creating empty transaction lists
- Test pollution from stale `~/.baitcoin/memory` data (default `persistent=False`)

### Changed
- Test suites: 9 → 11 (added stress_enhanced, smoke_enhanced)
- Total tests: 465 → 547 (82 new tests)
- Whitelabel presets: 70 → 72
- README updated to reflect accurate codebase metrics

---

## [0.3.0] — 2026-07-31

### Added
- **Phase 16**: Multi-Node P2P Testnet
  - `TestnetOrchestrator`: manages multiple testnet nodes with configurable topology
  - `TestnetConsensus`: consensus coordination across testnet nodes
  - `FaucetNode`: automated testnet faucet for token distribution
  - `NetworkPartition`: network partition simulation for resilience testing
- **Phase 17**: Mobile SDK (Python Reference)
  - `BaitcoinMobileSDK`: unified mobile interface
  - `MobileWallet`, `MobileStaking`, `MobileMarketplace`, `MobileNotificationManager`, `MobileSecurity`
- **Phase 18**: Cross-Chain Bridges (Logic Layer)
  - `BridgeManager`, `BridgeWatcher`, `Relayer`, `AnchorProtocol`, `BridgePool`, `ChainConfig`
  - Support for Ethereum and Solana bridge configurations
- 109 new tests across phases 16-18

---

## [0.2.0] — 2026-07-30

### Added
- **Phase 9**: zkML Real Proof System with Pedersen tensor commitments
- **Phase 10**: PoUW tensor commitments for proof-of-useful-work
- **Phase 11**: Obscura headless browser bridge (Python interface)
- **Phase 12**: WAL persistent memory with 10 namespaces
- **Phase 13**: Blockch'AI'in Developer Portal (52 REST API endpoints)
- **Phase 14**: Paper Wallet cold storage with printable HTML generation
- **Phase 15**: Netlify landing page + deployment configuration
- WAL persistent memory: checksummed entries, atomic snapshots, immutable block storage

---

## [0.1.0] — 2026-07-29

### Added
- **Phase 1**: Core blockchain engine with UTXO model
- **Phase 2**: zkML consensus engine (Sigma protocol + Fiat-Shamir heuristic)
- **Phase 3**: PoUW mining (validates ML computation hash chains)
- **Phase 4**: BAIT token with 21M supply cap and halving schedule (every 210K blocks)
- **Phase 5**: AI Agent protocol with 10 capability types
- **Phase 6**: AI Agent marketplace for model/data/services trading
- **Phase 7**: P2P network with Kademlia DHT peer discovery
- **Phase 8**: Oracle system for external data feeds
- Schnorr/BIP-340 digital signatures on secp256k1
- SHA-256d block hashing
- Pedersen commitments for confidential transactions
- 280 passing tests across initial 9 suites

---

[0.4.0]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/releases/tag/v0.1.0
