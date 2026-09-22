# E2E system validation checklist

PR: https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/pull/34

```bash
forge build && forge test -vvv
forge test --match-contract BridgeFoundryInvariant -vv
slither . --filter-paths "lib|node_modules|test" --exclude-dependencies --fail-high
forge test --gas-report
# anvil + DeployBAIT.s.sol smoke
```

Must pass: rate-limit parallel revert, no double-charge dailyMinted, 3 confirms mint, bridge wired, conservation.

Slippage: amount0Min/amount1Min > 0 on addLiquidity; seed scripts use bps.

Timelock ownership before mainnet.
