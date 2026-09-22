# ERC-4626 vulnerabilities (BAIT context)

**Current repo:** no ERC4626 / IERC4626 / vault implementation (code search = 0).

## Inflation / donation attack (first depositor)

1. Attacker deposits 1 wei → ~1 share
2. Attacker donates large asset amount via direct transfer
3. totalAssets up, share supply flat → share price explodes
4. Next depositor gets 0 shares (rounding)
5. Attacker redeems and extracts value

Mitigations: virtual shares / decimals offset (OZ), dead shares on init, internal totalAssets accounting (not raw balanceOf), min deposit that never mints 0 shares.

## Relevance to BAIT

| BAIT | ERC4626 analog | Status |
|------|----------------|--------|
| totalMinted <= totalLocked | assets vs shares conservation | On-chain in phase-2 PR |
| onlyBridge mint | only deposit path mints | yes |
| wBAIT 1:1 wrapper | not a yield vault | no share-price inflation vector today |

If a future BAIT vault is added: use OZ ERC4626 with offset, dead shares, donation tests, and Echidna properties that deposits above min never mint 0 shares after a donation scenario.

## Checklist for future vault

- [ ] OZ ERC4626 with _decimalsOffset >= 3 or dead shares
- [ ] totalAssets not blind balanceOf
- [ ] First-depositor + donation unit tests
- [ ] Invariants on convertToShares
- [ ] Do not use raw share price as sole lending oracle
