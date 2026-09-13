# b'AI'tcoin (BAIT) — Technical Summary for HTX (Huobi)

## Token Overview

| Parameter | Value |
|---|---|
| **Name** | b'AI'tcoin |
| **Symbol** | BAIT (Native) / wBAIT (ERC-20) |
| **Decimals** | 8 (smallest unit: s'AI'toshi) |
| **Max Supply** | 21,000,000 BAIT (Bitcoin-mirroring) |
| **Consensus** | zkML-PoUW + SHA-256d |
| **Block Time** | 30s (target) / 60s (exchange compatibility) |
| **Bridge** | Lock-and-Mint (3-of-5 multisig) |
| **Website** | https://mybait.org |

## Blockchain Architecture

b'AI'tcoin is a Layer-1 blockchain with a novel hybrid consensus mechanism:

- **zkML-PoUW (Zero-Knowledge Machine Learning Proof-of-Useful-Work)**: Mining energy is redirected toward useful AI/ML computations. Miners provide zk-SNARK proofs (Groth16) of correct ML inference execution, making every mined block contribute to real AI work.
- **SHA-256d (Double SHA-256)**: Secondary consensus layer compatible with Bitcoin mining infrastructure. Provides immutable security anchoring independent of the ML component.
- **Schnorr Signatures (BIP-340)**: x-only public keys (32 bytes) and 64-byte signatures for aggregate validation efficiency.

## Smart Contracts (Ethereum - wBAIT)

### WBAIT.sol (ERC-20)
- **Standard**: ERC-20 + Burnable + Permit (EIP-2612) + Ownable2Step + Pausable
- **Solidity**: 0.8.20
- **Supply Cap**: 21,000,000 wBAIT (8 decimals = 2,100,000,000,000 s'AI'toshi)
- **Conservation Invariant**: totalSupply == totalLockedOnL1
- **Mint Control**: Only BridgeLock contract can mint
- **Emergency**: Owner can pause all transfers

### BridgeLock.sol (Bridge)
- **Type**: 3-of-5 Multisig Lock-and-Mint
- **Rate Limit**: 100,000 wBAIT/day/address
- **Timelock**: 24 hours on operator changes
- **Security**: ReentrancyGuard, emergency pause, replay protection

## Native BAIT Chain Contracts

| Contract | Address | Purpose |
|---|---|---|
| BaitStakingPool | bait1stakingpoolagentnative0000000000000000 | PoAS staking (7% APY) |
| BaitP2PLending | bait1p2plendingprotocolagentnative00000000 | P2P lending (150% collateral) |
| BaitVaultStrategy | bait1vaultstrategyfdrallocation000000000 | FDR vault strategies |
| A2AStoreRegistry | bait1a2astoreagencyregistrynative00000000 | AI Store registry |

## Security Audit

| Audit | Tool | Overall Risk | Critical | High | Medium | Low | Info |
|---|---|---|---|---|---|---|---|
| Smart Contracts | Slither v0.11.6 | **LOW** | 0 | 0 | 0 | 3 | 2 |
| Schnorr BIP-340 | Manual | **PASS** | — | — | — | — | — |
| Reentrancy | Slither | **CLEAR** | 0 | 0 | 0 | 0 | 0 |
| Integer Overflow | Solidity 0.8.x | **SAFE** | — | — | — | — | — |

## Tokenomics Distribution

| Allocation | % | Description |
|---|---|---|
| Mining (PoW + PoUW) | 40% | Block rewards for miners |
| Staking (PoAS) | 20% | 7% APY for validators |
| Treasury (FDR) | 15% | Decentralized reserve |
| Community | 15% | Airdrops and distribution |
| Founders | 10% | Team allocation |

## Integration Requirements for HTX (Huobi)

### Deposit/Withdrawal
- **ERC-20**: Standard transfer/transferFrom on wBAIT contract
- **Native BAIT**: Bech32 addresses (b'... prefix), Schnorr signatures
- **Fee Structure**: Configurable gas market, median fee tracking

### API Endpoints
- Block explorer: https://explorer.mybait.org
- API: https://api.mybait.org
- WebSocket: wss://api.mybait.org/ws

### Market Making
- Minimum deposit: 15,000 USDT
- Suggested pairs: BAIT/USDT, BAIT/BTC, BAIT/ETH
- Initial price target: $0.00111071/BAIT (based on BTC fund ratio)

---

*Generated for HTX (Huobi) (Tier-2) listing application*
*Date: 2026-09-13T12:33:03.061822*
