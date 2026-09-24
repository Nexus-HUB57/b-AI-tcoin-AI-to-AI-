# Chainlink Data Feeds nativos

`AggregatorV3Interface.latestRoundData()` via **proxy**.

| Par | Proxy mainnet |
|-----|----------------|
| ETH/USD | `0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419` |
| BTC/USD | `0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c` |
| LINK/USD | `0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c` |

Stale check: `updatedAt >= block.timestamp - HEARTBEAT`.
BridgeLock mint não depende de preço; Chainlink para valuation/risk.
