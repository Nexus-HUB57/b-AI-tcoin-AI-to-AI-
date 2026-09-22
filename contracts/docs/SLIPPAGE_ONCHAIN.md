# Slippage on-chain — BAITUniswapV3Liquidity

## Already enforced

- amountWBAIT/WETH > 0
- **amount0Min > 0 and amount1Min > 0** (cannot disable slippage)
- tick range + spacing
- deadline = block.timestamp + 300
- NPM mint reverts if pool delivers below mins

## Script-side

```solidity
uint256 bps = 50; // 0.50%
uint256 amount0Min = amount0Desired * (10_000 - bps) / 10_000;
uint256 amount1Min = amount1Desired * (10_000 - bps) / 10_000;
```

## Gaps

- WETH funding/allowance is caller responsibility
- No swap path in this contract
- Validate INITIAL_SQRT_PRICE vs market before mainnet seed
