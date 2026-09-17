# BAIT Smart Contracts

## Overview

Wrapped b'AI'tcoin (wBAIT) is the ERC-20 representation of native BAIT on Ethereum, backed 1:1 via a Lock-and-Mint bridge with multisig security, timelock, and rate limiting.

## Architecture

```
┌──────────────────┐     Lock (L1 BAIT)     ┌──────────────────┐
│   Native BAIT    │ ────────────────────── │   BridgeLock     │
│   (zkML-PoUW)    │                        │   (3-of-5 msig)  │
│   21M supply     │ ◄────────────────────  │   24h timelock   │
└──────────────────┘     Release (wBAIT)    │   100K/day limit │
                                            └────────┬─────────┘
                                                     │ mint/burn
                                            ┌────────▼─────────┐
                                            │      WBAIT       │
                                            │    (ERC-20)      │
                                            │   21M max supply │
                                            └──────────────────┘
                                                     │
                                            ┌────────▼─────────┐
                                            │  Uniswap V3 Pool │
                                            │  WBAIT/WETH      │
                                            │  0.3% fee tier   │
                                            └──────────────────┘
```

## Contracts

### WBAIT.sol — Wrapped b'AI'tcoin (ERC-20)

| Feature | Implementation |
|---------|---------------|
| Standard | ERC20 + ERC20Burnable + ERC20Permit |
| Access | Ownable2Step (2-step ownership transfer) |
| Emergency | Pausable (owner can pause all mints) |
| Supply Cap | 21,000,000 (8 decimals = 2,100,000,000,000 smallest units) |
| Mint Control | Only BridgeLock contract can mint |
| Conservation | `totalSupply == totalLockedOnL1` (invariant) |

**Key Functions:**
- `mint(address to, uint256 amount)` — BridgeLock-only, enforces supply cap
- `pause()` / `unpause()` — Owner-only emergency controls
- Standard ERC20 + burn + permit (EIP-2612)

### BridgeLock.sol — Lock-and-Mint Bridge

| Feature | Implementation |
|---------|---------------|
| Multisig | 3-of-5 operator threshold |
| Timelock | 24 hours minimum execution delay |
| Rate Limit | 100,000 wBAIT/day per recipient |
| Security | ReentrancyGuard + Pausable |
| Access | Ownable2Step |

**Lock-Mint Flow:**
1. Operator calls `requestLockMint(recipient, amount)` — creates pending request
2. After 24h timelock, operator calls `confirmLockMint(requestId)` — confirms
3. When 3+ operators confirm, anyone calls `executeLockMint(requestId)` — mints wBAIT

**Burn-Release Flow:**
1. User calls `initiateBurnRelease(l1ReleaseAddress)` — burns wBAIT, creates release request
2. After 24h timelock, operator confirms release
3. When threshold met, release executed — native BAIT unlocked on L1

### BAITUniswapV3Liquidity.sol — DEX Liquidity

| Feature | Implementation |
|---------|---------------|
| Pool | WBAIT/WETH on Uniswap V3 |
| Fee Tier | 0.3% (tick spacing 60) |
| Liquidity | Concentrated liquidity position |
| Access | Ownable2Step |

## Security

### Audit Status

| Audit Type | Status | Findings |
|-----------|--------|----------|
| Slither Static | ✅ PASSED | 0 High, 0 Medium (51 Info/Low) |
| Foundry Tests | ✅ PASSED | 12/12 tests passing |
| CertiK Professional | ⏳ PENDING | To be commissioned (Week 3-4) |
| Quantstamp | ⏳ PENDING | Backup auditor |
| Bug Bounty | ⏳ PENDING | Immunefi setup post-mainnet |

### Slither Findings Summary (Info/Low only)

- **Naming conventions**: Test functions use `test_Underscore` pattern (Foundry convention — acceptable)
- **Unindexed event addresses**: `OperatorUpdated` event — low priority, off-chain indexing optimization
- **Unused state variables**: forge-std internals — expected, not our code

### Security Properties

1. **Conservation Invariant**: `totalSupply(wBAIT) == totalLockedOnL1(BAIT)` — enforced by BridgeLock-only mint
2. **Supply Cap**: 21M hard cap, checked on every mint — cannot be exceeded
3. **Multisig Threshold**: 3-of-5 operators must confirm — no single point of failure
4. **Timelock**: 24h delay on all bridge operations — time for emergency response
5. **Rate Limiting**: 100K wBAIT/day per recipient — limits impact of compromise
6. **Reentrancy Guard**: All state-changing functions protected
7. **Pausable**: Owner can halt all operations in emergency
8. **Two-Step Ownership**: Prevents accidental ownership loss

## Deployment

### Sepolia Testnet

```bash
# 1. Set environment
source .env  # SEPOLIA_RPC_URL, DEPLOYER_PRIVATE_KEY

# 2. Deploy
forge script script/DeployBAIT.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast --verify

# 3. Test bridge lifecycle
# Request lock → Confirm → Execute (mint)
# Initiate burn → Confirm release → Execute (release)
```

### Ethereum Mainnet

```bash
# 1. Verify audit completion
# 2. Set mainnet environment
source .env  # MAINNET_RPC_URL, MAINNET_DEPLOYER_KEY

# 3. Deploy with gas estimation
forge script script/DeployBAIT.s.sol --rpc-url $MAINNET_RPC_URL --broadcast --verify --legacy

# 4. Create Uniswap V3 pool + seed liquidity
# 5. Verify contracts on Etherscan
# 6. Submit CoinGecko + CoinMarketCap listings
```

## Testing

```bash
# Unit tests
forge test -vv

# Fuzz tests (256 runs configured)
forge test --fuzz-runs 256

# Gas profiling
forge test --gas-report

# Coverage
forge coverage
```

### Test Results

| Suite | Tests | Passed | Failed |
|-------|-------|--------|--------|
| WBAITTest | 9 | 9 | 0 |
| BridgeLockTest | 3 | 3 | 0 |
| **Total** | **12** | **12** | **0** |

## Configuration

| Parameter | Value |
|-----------|-------|
| Solidity | 0.8.20 |
| Optimizer | Enabled, 200 runs |
| Fuzz Runs | 256 |
| Max Supply | 21,000,000 (8 decimals) |
| Bridge Threshold | 3-of-5 |
| Timelock | 24 hours |
| Rate Limit | 100,000 wBAIT/day |
| Uniswap Fee | 0.3% |
