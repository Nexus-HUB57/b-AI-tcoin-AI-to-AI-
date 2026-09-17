# Contributing to b'AI'tcoin (BAIT)

Thank you for your interest in contributing to the b'AI'tcoin ecosystem. This guide covers the essential information for effective participation.

## Code of Conduct

- Be respectful and constructive in all interactions
- Focus on technical merit when reviewing code
- Maintain academic rigor in cryptographic implementations
- Never modify consensus-critical code without formal review

## Development Setup

### Prerequisites

```bash
# Python 3.10+
python3 --version

# Install dependencies
pip install -r requirements.txt

# Run full test suite (547 tests)
pytest tests/ -v
```

### Repository Structure

```
baitcoin-ecosystem/
├── baitcoin_core/          # Blockchain, consensus, cryptography, networking
├── baitcoin_ai/            # AI agent protocol, marketplace, oracle
├── baitcoin_api/           # REST API server (52 endpoints)
├── baitcoin_token/         # Token economics, governance, ERC-20-like interface
├── baitcoin_wallet/        # Wallet, key management, transactions, paper wallet
├── baitcoin_bank/          # DeFi: staking pools, lending, vaults
├── baitcoin_bridge/        # Cross-chain bridge logic (Ethereum, Solana)
├── baitcoin_sdk/           # SDK: client, wallet, staking, marketplace + mobile
├── baitcoin_explorer/      # Blockch'AI'in: block explorer, search, analytics
├── baitcoin_memory/        # WAL persistent memory, snapshots
├── baitcoin_obscura/       # Headless browser bridge
├── baitcoin_whitelabel/    # 72 whitelabel presets
├── baitcoin_faucet/        # Testnet faucet
├── baitcoin_mainnet/       # Mainnet launcher and configuration
├── config/                 # Network configuration (network.yaml)
├── tests/                  # 11 test suites, 547 tests
├── docs/                   # Documentation and whitepaper
├── scripts/                # Validation and utility scripts
└── netlify/                # Landing page and deployment config
```

## Development Workflow

1. **Fork** the repository
2. **Branch** from `main` with a descriptive name: `feat/description` or `fix/description`
3. **Implement** your changes with tests
4. **Verify** all 547 tests pass: `pytest tests/ -v`
5. **Run** E2E validation: `python scripts/validate_e2e_comprehensive.py`
6. **Submit** a Pull Request with a clear description

## Testing Standards

- All new code must include corresponding tests
- Tests must be deterministic (no reliance on `time.time()` in consensus paths)
- Use `persistent=False` for blockchain fixtures to avoid test pollution
- Follow existing test patterns in `tests/`

## Cryptographic Code Review

Any changes to the following modules require **mandatory** cryptographic review:

- `baitcoin_core/cryptography/schnorr.py` — Schnorr/BIP-340 signatures
- `baitcoin_core/consensus/zkml_real/` — zkML proof system
- `baitcoin_core/consensus/pouw.py` — PoUW mining validation
- `baitcoin_core/consensus/zkml_engine.py` — zkML consensus engine

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: resolve bug
docs: update documentation
test: add or update tests
refactor: code restructuring
chore: maintenance tasks
```

## Module Ownership

| Module | Domain |
|--------|--------|
| `baitcoin_core` | Blockchain, consensus, cryptography, P2P |
| `baitcoin_ai` | AI agent protocol, marketplace, oracle |
| `baitcoin_api` | REST API, developer portal |
| `baitcoin_token` | Tokenomics, governance |
| `baitcoin_wallet` | Wallet, keys, transactions |
| `baitcoin_bank` | DeFi primitives |
| `baitcoin_bridge` | Cross-chain bridges |
| `baitcoin_sdk` | SDK and mobile SDK |

## Questions?

Open an issue with the `question` label for any clarifications.
