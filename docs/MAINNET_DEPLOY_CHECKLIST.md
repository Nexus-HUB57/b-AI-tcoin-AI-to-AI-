# Checklist Deploy Mainnet Ethereum — Nexus b'AI'tcoin

**Data:** 24/09/2026

## Order
1. TimelockController (Safe proposers/executors, minDelay 48h)
2. WBAIT(address(0), timelock)
3. BridgeLock(wbait, timelock, operators[5])
4. wbait.initializeBridgeLock(bridge)
5. Optional Uniswap liquidity bootstrap
6. Ownable2Step transferOwnership(Safe) + acceptOwnership

## Go criteria
- [x] H-02 no auto-confirm
- [x] Partial burn API
- [x] Foundry tests + invariants
- [x] Fork dry-run PASS
- [ ] Production Safe + 5 operator HW/HSM keys
- [ ] External audit / Slither offline
- [ ] Broadcast only after sign-off

## Official custody (BTC sweep)
`bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s`
