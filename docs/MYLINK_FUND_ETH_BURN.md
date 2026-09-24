# MyLink Fund — ETH Gas Burn Workflow

> **Purpose:** Validate the Motor Swap Sweep BAITHex by burning gas ETH from
> the Fundo MyLink operational wallet. Manual trigger only.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  GitHub Actions workflow (manual dispatch)                              │
│                                                                         │
│  ┌────────────────────┐   ┌──────────────────────────────────────┐    │
│  │ Secrets:           │   │ Script: ops/mylink_fund_eth_burn.py │    │
│  │ KEYSTORE_ETH_FUNDO_│──▶│   • loads keystore (path or JSON)   │    │
│  │   MYLINK           │   │   • decrypts with passphrase         │    │
│  │ KEYSTORE_ETH_FUNDO_│   │   • validates chain_id, balance, gas │    │
│  │   MYLINK_PASSWORD  │   │   • if ARMED=true → sign + broadcast │    │
│  │ ETH_RPC_URL        │   │   • always wipes privkey from RAM    │    │
│  └────────────────────┘   └──────────────────────────────────────┘    │
│                                       │                                 │
└───────────────────────────────────────┼─────────────────────────────────┘
                                        │ JSON-RPC (https)
                                        ▼
                              ┌──────────────────────┐
                              │  ETH RPC endpoint    │
                              │  (Infura / Alchemy / │
                              │   self-hosted node)  │
                              └──────────────────────┘
                                        │
                                        ▼
                              ┌──────────────────────┐
                              │  Ethereum network    │
                              │  → 0x000…dEaD (burn) │
                              └──────────────────────┘
```

## Security model

Aligned with [`AGENT_PRIVATE_KEY_SECURITY_SPEC.md`](./AGENT_PRIVATE_KEY_SECURITY_SPEC.md):

| Property | How it's enforced |
|---|---|
| Keystore never in repo | `.gitignore` blocks `*.keystore`, `KEYSTORE_*`, `*_keystore.json` |
| Passphrase never in repo | Same — only via env vars / secrets |
| Keystore never in CI logs | `actions/checkout@v4` uses `persist-credentials: false`; `gitleaks` pre-scan |
| Keystore never echoed | Workflow passes secret via `secrets.*` env, never `::set-output` |
| Chain confusion defense | `ETH_EXPECTED_CHAIN_ID` gate; aborts if RPC chain_id differs |
| Memory wipe | `bytearray` zeroed in `finally:` block before script exits |
| Dry-run by default | `MYLINK_FUND_ETH_BURN_ARMED=false` is the safe default |

## Setup

### 1. Generate a keystore (one-time, offline)

Use `geth` or `eth-account` on an airgapped machine:

```bash
# Offline (do NOT do this on a CI runner or shared host):
python3 -c "
from eth_account import Account
acct = Account.create()
import getpass
pw = getpass.getpass('keystore passphrase: ')
import json
ks = Account.encrypt(acct.key, pw)
print(json.dumps(ks))
print('address:', acct.address)
"
```

Save the JSON output as the `KEYSTORE_ETH_FUNDO_MYLINK` secret, and the
passphrase as `KEYSTORE_ETH_FUNDO_MYLINK_PASSWORD`.

### 2. Fund the wallet with ETH (operational float)

Send a small amount of ETH (e.g. 0.05 ETH on mainnet, 0.5 ETH on testnet) from
your treasury to the address from step 1. This funds the gas.

### 3. Add GitHub Secrets

Go to `Settings → Secrets and variables → Actions → New repository secret`:

| Secret | Description |
|---|---|
| `KEYSTORE_ETH_FUNDO_MYLINK` | The JSON keystore content (inline). |
| `KEYSTORE_ETH_FUNDO_MYLINK_PASSWORD` | The passphrase that decrypts it. |
| `ETH_RPC_URL` | JSON-RPC endpoint (e.g. `https://eth-mainnet.g.alchemy.com/v2/xxx`). |

Add a `production` GitHub Environment and require reviewer approval before
running in `armed=true` mode (Settings → Environments → mylink-fund-prod →
Required reviewers).

### 4. Run

Go to **Actions → MyLink Fund — ETH Gas Burn (BAITHex Sweep Validation) →
Run workflow**:

- `arm`: leave as `false` for first run (dry-run / validate only)
- `burn_amount_wei`: usually `0` (you're paying gas, not transferring value)
- `burn_address`: defaults to `0x000…dEaD` (Ethereum canonical burn addr)
- `min_balance_wei`: post-burn floor (e.g. `1000000000000000` = 0.001 ETH)

Once dry-run is green, re-run with `arm=true`.

## Hardening checklist

- [ ] `gitleaks` enabled in CI (`.github/workflows/ci.yml`)
- [ ] Branch protection on `main` requires signed commits
- [ ] `mylink-fund-prod` GitHub Environment requires manual approval
- [ ] `.gitignore` contains `*.keystore`, `*_keystore.json`, `KEYSTORE_*`
- [ ] PR template has "no secrets" checkbox
- [ ] Wallet funded with only operational float (not treasury)
- [ ] Wallet is a **burner** — never reused for other operations
- [ ] Post-burn balance floor set so a stuck script can't drain the wallet
- [ ] Audit logs reviewed monthly: `/tmp/mylink-fund-eth-burn.log` rotated
- [ ] No more than 1 run / day (cron-friendly; can be triggered manually for emergencies)

## Audit trail

Every workflow run leaves:

1. **GitHub Actions run** (visible to repo admins)
2. **Job summary** (no secrets, just status)
3. **Workflow logs** (CI server-side retention per org policy)
4. **On-chain tx** (public, forever, on the chosen network)

For compliance, run via `gh workflow run` with the `--json` flag and pipe the
output to your audit pipeline:

```bash
gh workflow run mylink-fund-eth-burn.yml \
  -f arm=false \
  -f burn_amount_wei=0 \
  -f burn_address=0x000000000000000000000000000000000000dEaD \
  -f min_balance_wei=0 \
  --json > "$(date -u +%Y%m%dT%H%M%SZ)-mylink-burn-precheck.json"
```

## References

- [`AGENT_PRIVATE_KEY_SECURITY_SPEC.md`](./AGENT_PRIVATE_KEY_SECURITY_SPEC.md) — zero-trust agent vault spec
- [`ops/custody_sweep.py`](../ops/custody_sweep.py) — BTC counterpart (same hardening pattern)
- [EIP-155](https://eips.ethereum.org/EIPS/eip-155) — replay-protected tx signing
- [Web3 Secret Storage](https://ethereum.org/en/developers/docs/data-structures-and-encoding/web3-secret-storage/) — keystore format

---

**Maintained by:** Nexus-HUB57 / MyLink Fund Working Group
**License:** MIT
