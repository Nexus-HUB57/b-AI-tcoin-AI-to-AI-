# Uniswap V3 gas — BAITUniswapV3Liquidity

## Typical costs (order of magnitude)

| Function | Est. gas | Driver |
|----------|----------|--------|
| createPool (+ initialize) | 100k–400k+ | Pool creation SSTOREs |
| addLiquidity | 150k–450k+ | NPM.mint position NFT |
| safeIncreaseAllowance | 5k–50k | Approve path |

Wrapper logic is cheap; NPM/pool dominate.

## Optimizations

- One-time max approve WBAIT → NPM (skip increaseAllowance every seed)
- Skip createPool if getPool != 0 (already implemented)
- Correct amount0Min/amount1Min (bps) to avoid failed retries paying gas

## Slippage

Contract requires amount0Min > 0 and amount1Min > 0; NPM reverts on excess slippage. deadline = now+300.

## Measure on fork

```bash
forge test --fork-url $MAINNET_RPC --gas-report
cast estimate <liquidity> "addLiquidity(...)" ... --rpc-url $MAINNET_RPC
```
