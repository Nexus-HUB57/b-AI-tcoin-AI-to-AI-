# BAIT Exchange Listing Strategy

## Target Exchanges

### Tier-1 (Premium — Apply after Tier-2 listings + volume)

| Exchange | Status | Est. Cost | Timeline | Requirements |
|----------|--------|-----------|----------|-------------|
| Binance | PACKAGE_READY | Free (listing) | 2-6 months | High volume, 100K+ holders, professional audit |
| Coinbase | PACKAGE_READY | Free (listing) | 3-6 months | SEC compliance, Howey opinion, 50K+ holders |
| Kraken | PACKAGE_READY | Free (listing) | 1-3 months | Pro audit, volume, community |

### Tier-2 (Mid-tier — Apply immediately after mainnet deployment)

| Exchange | Status | Est. Cost | Timeline | Priority |
|----------|--------|-----------|----------|----------|
| BitMart | PACKAGE_READY | Free | 2-4 weeks | 🔴 HIGH (fastest) |
| LBank | PACKAGE_READY | Free | 1-3 weeks | 🔴 HIGH (fastest) |
| BingX | PACKAGE_READY | Free | 1-2 weeks | 🔴 HIGH (fastest) |
| Gate.io | PACKAGE_READY | Free | 2-4 weeks | 🟡 MEDIUM |
| MEXC | PACKAGE_READY | Free | 1-3 weeks | 🟡 MEDIUM |
| Bybit | PACKAGE_READY | Free | 2-4 weeks | 🟡 MEDIUM |
| OKX | PACKAGE_READY | Free | 2-4 weeks | 🟡 MEDIUM |
| HTX (Huobi) | PACKAGE_READY | Free | 2-4 weeks | 🟢 LOW |
| Bitget | PACKAGE_READY | Free | 2-4 weeks | 🟢 LOW |
| KuCoin | PACKAGE_READY | Free | 2-4 weeks | 🟢 LOW |

### DEX (Decentralized)

| DEX | Chain | Status | Liquidity Target |
|-----|-------|--------|-----------------|
| Uniswap V3 | Ethereum | CONTRACT_READY | $30K WBAIT/WETH |
| PancakeSwap | BSC | PLANNED | $10K WBAIT/WBNB |
| Raydium | Solana | PLANNED | $5K wBAIT/SOL |
| Camelot | Arbitrum | PLANNED | $3K WBAIT/WETH |
| Aerodrome | Base | PLANNED | $2K WBAIT/WETH |

### Aggregators

| Aggregator | Status | Cost | Timeline |
|-----------|--------|------|----------|
| CoinGecko | DATA_READY | Free | 3-7 days (after 2+ CEX) |
| CoinMarketCap | DATA_READY | Free / $5K-$50K Fast Track | 2-4 weeks / 3-7 days |
| DEXScreener | AUTO | Free | Auto after Uniswap pool |

## Execution Roadmap

### Week 1-2: Foundation
- [ ] Deploy wBAIT + BridgeLock to Sepolia testnet
- [ ] Test full bridge lifecycle on Sepolia
- [ ] Commission CertiK professional audit ($15K-$50K)
- [ ] Generate bridge multisig operator keys (HSM)

### Week 2-3: Mainnet Launch
- [ ] Deploy wBAIT + BridgeLock to Ethereum mainnet
- [ ] Verify contracts on Etherscan
- [ ] Create Uniswap V3 pool (WBAIT/WETH, 0.3% fee)
- [ ] Seed initial liquidity ($50K target)
- [ ] Commission Howey Test legal opinion ($5K-$15K)

### Week 3-4: Fast CEX Applications
- [ ] Submit BitMart application (fastest Tier-2)
- [ ] Submit LBank application
- [ ] Submit BingX application
- [ ] Submit CoinGecko listing request
- [ ] Submit CoinMarketCap listing (consider Fast Track)

### Week 4-8: Mid-tier CEX + DEX Expansion
- [ ] Submit Gate.io, MEXC, Bybit, OKX applications
- [ ] Deploy wBAIT on BSC (PancakeSwap)
- [ ] Deploy wBAIT on Arbitrum (Camelot)
- [ ] Set up Immunefi bug bounty program

### Week 8-12: Tier-1 Preparation
- [ ] Accumulate trading volume ($50K+ daily)
- [ ] Grow holder count (target: 5K+ unique holders)
- [ ] Submit Kraken application (most accessible Tier-1)
- [ ] Submit Coinbase application (requires compliance)

### Week 12-24: Premium Tier
- [ ] Submit Binance application
- [ ] Cross-chain expansion (Solana, Base)
- [ ] Professional market making partnership
- [ ] Insurance fund establishment

## Cost Estimates

| Item | Low | High | Timing |
|------|-----|------|--------|
| CertiK Audit | $15,000 | $50,000 | Week 2 |
| Howey Legal Opinion | $5,000 | $15,000 | Week 2 |
| Deployment Gas (Mainnet) | 0.3 ETH | 0.8 ETH | Week 2 |
| Initial Liquidity (DEX) | $30,000 | $50,000 | Week 2 |
| CMC Fast Track (optional) | $5,000 | $50,000 | Week 3 |
| Bug Bounty (Immunefi) | $5,000 | $20,000 | Week 4 |
| Market Making (3 months) | $10,000 | $30,000 | Week 4 |
| Insurance (Nexus Mutual) | $2,000 | $5,000 | Week 8 |
| **TOTAL** | **$72K** | **$220K** | |

## Competitive Advantages for Listing

1. **Novel Consensus**: zkML-PoUW (Proof of Useful Work) — unique in market
2. **Fixed Supply**: 21M cap mirrors Bitcoin's scarcity narrative
3. **Bridge Security**: 3-of-5 multisig + 24h timelock + rate limit — exceeds industry standard
4. **Professional Audit**: CertiK/Quantstamp (pending) — top-tier auditors
5. **Open Source**: Full repo on GitHub with CI/CD pipeline
6. **Active Development**: 200+ files, continuous commits, test coverage
7. **Cross-Chain**: Multi-chain deployment plan (ETH, BSC, Arbitrum, Solana, Base)
8. **BTC Fund Backing**: 5,000+ BTC in reserve addresses (verifiable on-chain)
