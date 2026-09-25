# ERC-4337 Verifying Paymaster — E2E (b'AI'tcoin / MyLink)

## Architecture

```
Smart Account / Wallet
        │  UserOperation (unsigned pm)
        ▼
 Backend sponsor API  ── signs with PAYMASTER_SIGNER_KEY
        │  paymasterAndData
        ▼
 Bundler ──► EntryPoint v0.6 ──► BAITVerifyingPaymaster.validatePaymasterUserOp
                                      │
                                      └─ gas paid from EntryPoint deposit
```

| Component | Path |
|-----------|------|
| Contract | `contracts/src/aa/BAITVerifyingPaymaster.sol` |
| Interfaces | `contracts/src/aa/{IEntryPoint,IPaymaster,UserOperation}.sol` |
| Tests | `contracts/test/Paymaster.t.sol` |
| Deploy | `contracts/script/DeployPaymaster.s.sol` |
| Signer (ops) | `server/aa/paymasterSigner.ts` |
| Client helper | `client/aa/sponsorUserOp.ts` |

## Canonical addresses

| Network | EntryPoint v0.6 |
|---------|-----------------|
| Ethereum / Sepolia / most L2 | `0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789` |

## Security rules

1. **`PAYMASTER_SIGNER_KEY`** is an **ops** key only — never `KEYSTORE_ETH_FUNDO_MYLINK` or user seeds.
2. User wallets remain self-custodial (TokenPocket / AA owner key).
3. Cap spend with `maxCostWei` and optional `restrictSenders`.
4. Keep `validUntil` short (≤ 5–15 minutes).
5. Fund **EntryPoint deposit**, not the paymaster EOA balance alone: `paymaster.deposit{value: …}()`.

## Local test

```bash
cd contracts
forge test --match-contract PaymasterTest -vv
```

## Deploy (Sepolia example)

```bash
cd contracts
export PRIVATE_KEY=0x...          # deployer (funded for gas)
export VERIFYING_SIGNER=0x...     # address of PAYMASTER_SIGNER_KEY
export OWNER=0x...                # Safe recommended
export DEPOSIT_ETH=100000000000000000   # 0.1 ETH in wei
forge script script/DeployPaymaster.s.sol:DeployPaymaster \
  --rpc-url $SEPOLIA_RPC --broadcast
```

## Sponsor API sketch

```http
POST /api/aa/sponsor
{ "userOpHash": "0x…", "validUntil": 1730000000 }
→ { "paymasterAndData": "0x…", "signature": "0x…" }
```

Wire `server/aa/paymasterSigner.ts` `sponsorHandler` behind auth + rate limits.

## E2E checklist

- [ ] `forge test --match-contract PaymasterTest` green
- [ ] Deploy paymaster; `getDeposit() > 0`
- [ ] Signer recovers to `verifyingSigner`
- [ ] Bundler accepts UserOp with `paymasterAndData`
- [ ] `UserOpSponsored` event on success
- [ ] Bad signature → `validationData` sigFailed bit set (bundler rejects)
- [ ] Mainnet: owner = multisig; deposit from treasury **public** address (watch-only balance checks)

## Funding note

Documented BAIT deployer/operator EOAs currently show **0 ETH** on mainnet. Capitalize EntryPoint deposit only after deliberate treasury transfer — do not automate from user keystores.
