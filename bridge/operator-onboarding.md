# BAIT BridgeLock Operator Onboarding Guide

> **Version:** 2.0.0 | **Contract:** BridgeLock.sol | **Threshold:** 3-of-5 multisig
> **Last Updated:** 2026-03-05 | **Review Cycle:** Quarterly

This guide walks a new bridge operator through the complete onboarding process,
from HSM key generation to active participation in the 3-of-5 multisig bridge.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [HSM Key Generation Ceremony](#2-hsm-key-generation-ceremony)
3. [Operator Address Registration](#3-operator-address-registration)
4. [Monitoring Setup](#4-monitoring-setup)
5. [Confirmation Workflow](#5-confirmation-workflow)
6. [Emergency Procedures](#6-emergency-procedures)
7. [Security Hygiene](#7-security-hygiene)
8. [Troubleshooting](#8-troubleshooting)
9. [Pre-Flight Checklist](#9-pre-flight-checklist)

---

## 1. Prerequisites

### Hardware & Software

| Item | Requirement | Notes |
|------|-------------|-------|
| Air-gapped workstation | Linux (Ubuntu 22.04+), no network interfaces enabled | Dedicated machine, no WiFi/Bluetooth |
| HSM access | AWS CloudHSM / Azure Key Vault / HashiCorp Vault | Per your organization's choice |
| Data diode or QR transfer | For moving signed txs from air-gapped to online system | QR codes work; USB is acceptable if wiped after use |
| Python 3.10+ | For bridge-monitoring.py | `python3 --version` to verify |
| web3.py | `pip install web3` | Core Ethereum interaction library |
| Foundry | For forge/cast contract interactions | `curl -L https://foundry.paradigm.xyz \| bash && foundryup` |
| GPG | For encrypting communications | `gpg --gen-key` if not already set up |
| Signal/Telegram | For encrypted operator communication | Install on mobile + desktop |

### Access Credentials

Before starting, ensure you have:

- [ ] HSM cluster credentials (PKCS#11 PIN, Azure CLI login, or Vault token)
- [ ] BridgeLock contract address (from deployment — ask coordinator)
- [ ] WBAIT contract address (from deployment — ask coordinator)
- [ ] Ethereum RPC endpoint URL (free options listed below)
- [ ] Operator index number (0-4, assigned by ceremony coordinator)
- [ ] Operator communication channel access (Signal group invite)
- [ ] Emergency contact information for all other operators

### Free RPC Endpoints (No API Key Required)

| Provider | URL | Rate Limit | Notes |
|----------|-----|------------|-------|
| DRPC | `https://eth.drpc.org` | ~1000 req/min | Recommended primary |
| Ankr | `https://rpc.ankr.com/eth` | ~600 req/min | Good fallback |
| PublicNode | `https://ethereum.publicnode.com` | ~500 req/min | Community-run |
| 1RPC | `https://1rpc.io/eth` | ~400 req/min | Privacy-focused |

### Knowledge Requirements

Before proceeding, ensure you understand:

- **ECDSA secp256k1 signing** — the curve used by Ethereum and our HSM keys
- **BridgeLock.sol contract interface** — read the contract source before ceremony
- **3-of-5 multisig threshold semantics** — any 3 of 5 operators can execute; 2 cannot
- **Rate limiting** — 100,000 wBAIT/day/address cap enforced on-chain
- **24h timelock** — operator parameter changes delayed by 24 hours
- **Conservation invariant** — totalSupply(wBAIT) == totalLockedOnL1(BAIT)

---

## 2. HSM Key Generation Ceremony

The key ceremony is a formal, witnessed procedure. **All 5 operators must attend**
(in person or verified video call with identity verification).

### Step 2.1: Schedule Ceremony

```bash
# Coordinator schedules ceremony with all operators
# Minimum attendees: 5 operators + 1 coordinator + 1 witness = 7
# Duration: ~2h 30m (see hsm-configuration.json for detailed breakdown)
# Prerequisite: Rehearsal ceremony completed on testnet
```

**Scheduling checklist:**
- [ ] All 5 operators confirmed availability (no proxies allowed)
- [ ] Coordinator confirmed
- [ ] External auditor or witness confirmed
- [ ] Air-gapped workstations prepared and verified
- [ ] Video recording equipment set up
- [ ] Data transfer mechanism tested (air-gap → online)

### Step 2.2: Initialize HSM Session

Choose your provider below:

#### AWS CloudHSM

```bash
# Install CloudHSM client
wget https://s3.amazonaws.com/cloudhsmv2-software/CloudHsmClient/EL6/latest/cloudhsm-client-latest.el6.x86_64.rpm
sudo yum install -y cloudhsm-client-latest.el6.x86_64.rpm

# Configure cluster IP (get from AWS Console → CloudHSM → Cluster → ENI IP)
sudo /opt/cloudhsm/bin/configure -a <HSM_CLUSTER_IP>

# Start CloudHSM client
sudo start cloudhsm-client

# Verify connectivity
/opt/cloudhsm/bin/listUsers

# Login as Crypto User (CU)
export CLOUDHSM_PIN=<CU_USER_PIN>

# Verify FIPS mode
/opt/cloudhsm/bin/listUsers  # Should show CU user

# Check firmware version (record in ceremony transcript)
# AWS CloudHSM firmware is managed by AWS — check release notes
```

#### Azure Key Vault (Managed HSM)

```bash
# Login via Azure CLI
az login
az account set --subscription <SUBSCRIPTION_ID>

# Verify Managed HSM exists
az keyvault list --resource-group <RG> --output table

# Verify HSM is active
az keyvault show --hsm-name <HSM_NAME> --query properties.provisioningState
# Expected: "Succeeded"

# Assign yourself Key Vault Crypto Officer role (if not already)
az keyvault role assignment create \
  --hsm-name <HSM_NAME> \
  --role "Key Vault Crypto Officer" \
  --assignee $(az ad signed-in-user show --query objectId -o tsv) \
  --scope "/"

# Verify access
az keyvault key list --hsm-name <HSM_NAME>
```

#### HashiCorp Vault

```bash
# Verify Vault is running and unsealed
vault status
# Expected: Initialized: true, Sealed: false

# Login with your operator token (provided by Vault admin)
vault login <YOUR_OPERATOR_TOKEN>

# Verify Transit engine is enabled
vault secrets list | grep transit
# Expected: transit/

# Verify audit logging is enabled
vault audit list
# Expected: At least one audit device (file or syslog)
```

### Step 2.3: Generate Key Pair

**IMPORTANT:** Key generation happens INSIDE the HSM. The private key NEVER leaves
the HSM boundary. Only the public key (and derived Ethereum address) are extracted.

#### AWS CloudHSM

```bash
# Generate ECDSA secp256k1 key pair inside HSM
/opt/cloudhsm/bin/pkcs11-tool --login --pin=$CLOUDHSM_PIN \
  --keypairgen --key-type EC:secp256k1 \
  --label "bait-bridge-operator-<N>" \
  --id "<N>"

# Extract ONLY the public key
/opt/cloudhsm/bin/pkcs11-tool --login --pin=$CLOUDHSM_PIN \
  --read-object --type pubkey --label "bait-bridge-operator-<N>" \
  --output-file operator-<N>-pubkey.der

# Derive Ethereum address from public key
# Use openssl or cast to convert DER public key → Ethereum address
cast wallet address --public-key $(cat operator-<N>-pubkey.der | xxd -p)
```

#### Azure Key Vault

```bash
# Create key in Managed HSM (non-exportable, sign-only)
az keyvault key create \
  --hsm-name <HSM_NAME> \
  --name bait-bridge-operator-<N> \
  --kty EC \
  --curve P-256K \
  --exportable false \
  --attributes enabled=true \
  --ops sign

# Retrieve public key
az keyvault key show \
  --hsm-name <HSM_NAME> \
  --name bait-bridge-operator-<N> \
  --query key.n

# Derive Ethereum address from public key components (x, y)
# Use cast or custom script to convert → Ethereum address
```

#### HashiCorp Vault

```bash
# Create key in Transit engine (non-exportable, sign-only)
vault write transit/keys/bait-bridge-operator-<N> \
  type=ecdsa-p256k1 \
  exportable=false \
  allow_plaintext_backup=false \
  deletion_allowed=false

# Verify key exists and is configured correctly
vault read transit/keys/bait-bridge-operator-<N>
# Expected: type=ecdsa-p256k1, exportable=false, deletion_allowed=false

# Extract public key (Vault returns it in the read output)
vault read -format=json transit/keys/bait-bridge-operator-<N> | jq -r '.data.keys["1"].public_key'

# Derive Ethereum address from public key
# Use cast or eth_utils to convert → Ethereum address
```

### Step 2.4: Verify Key (Sign Test Message)

```bash
# Create a test message unique to this ceremony
TEST_MSG="BAIT-BRIDGE-KEY-CEREMONY-$(date -u +%Y%m%dT%H%M%SZ)-OPERATOR-<N>"
TEST_HASH=$(cast keccak "$TEST_MSG")

# Sign test message via HSM
# AWS CloudHSM:
/opt/cloudhsm/bin/pkcs11-tool --login --pin=$CLOUDHSM_PIN \
  --sign --mechanism ECDSA \
  --input-file <(echo -n "$TEST_HASH" | xxd -r -p) \
  --label "bait-bridge-operator-<N>" \
  --output-file test-sig.bin

# HashiCorp Vault:
vault write transit/sign/bait-bridge-operator-<N> \
  input=$(echo -n "$TEST_HASH" | base64)

# Verify signature matches public key
# If verification fails: STOP. Do not proceed. Investigate HSM issue.

# Record in ceremony transcript
echo "Operator <N>:" >> ceremony-transcript.txt
echo "  Public Key: <PUBLIC_KEY_HEX>" >> ceremony-transcript.txt
echo "  Address: <ETHEREUM_ADDRESS>" >> ceremony-transcript.txt
echo "  Test Message: $TEST_MSG" >> ceremony-transcript.txt
echo "  Timestamp: $(date -u +%Y%m%dT%H%M%SZ)" >> ceremony-transcript.txt
```

### Step 2.5: Lock Key Policy

After all 5 keys are generated and verified:

```bash
# Verify key attributes (should already be set at creation)
# AWS CloudHSM: Attributes set via pkcs11-tool at key generation
# Azure: --exportable false set at creation
# Vault: exportable=false, allow_plaintext_backup=false set at creation

# Explicitly verify non-exportable:
# Attempt key export — should FAIL
# AWS:
/opt/cloudhsm/bin/pkcs11-tool --login --pin=$CLOUDHSM_PIN \
  --read-object --type privkey --label "bait-bridge-operator-<N>"
# Expected: Error or no output (private key not extractable)

# Azure:
az keyvault key download --hsm-name <HSM_NAME> --name bait-bridge-operator-<N> -f test.pem
# Expected: Error "Key is not exportable"

# Vault:
vault read transit/export/key/bait-bridge-operator-<N>
# Expected: Error "key is not exportable"
```

---

## 3. Operator Address Registration

After all 5 public keys are collected during the ceremony, the coordinator
registers them with the BridgeLock contract.

### Step 3.1: Verify Collected Addresses

```bash
# All 5 operator addresses must be:
# 1. Unique (no duplicates)
# 2. Non-zero (not 0x0000...0000)
# 3. Valid Ethereum checksum addresses
# 4. Derived from keys generated in the ceremony (cross-check with transcript)

# Example verification:
cast wallet verify --address 0x1234...abcd
# Expected: valid checksum address

# Record in transcript:
# operator[0] = 0x1234... (US-East, operator-1)
# operator[1] = 0x5678... (EU-West, operator-2)
# operator[2] = 0x9abc... (AP-Southeast, operator-3)
# operator[3] = 0xdef0... (US-West, operator-4)
# operator[4] = 0x2468... (EU-North, operator-5)
```

### Step 3.2: Deploy to Testnet First

```bash
# ALWAYS deploy to Sepolia testnet first
# This validates constructor args, operator registration, and basic functionality

export SEPOLIA_RPC_URL=https://rpc.sepolia.org

# Deploy via Foundry
forge script script/DeployBAIT.s.sol \
  --rpc-url $SEPOLIA_RPC_URL \
  --constructor-args $WBAIT_ADDRESS \
    $OPERATOR_0 $OPERATOR_1 $OPERATOR_2 $OPERATOR_3 $OPERATOR_4 \
  --broadcast \
  --verify

# Record testnet addresses
echo "SEPOLIA_BRIDGELOCK=<deployed_address>" >> .env.testnet
echo "SEPOLIA_WBAIT=<deployed_address>" >> .env.testnet
```

### Step 3.3: Verify On-Chain Registration (Testnet)

```bash
# Check each operator is registered
for i in 0 1 2 3 4; do
  echo "Operator[$i]:"
  cast call $BRIDGELOCK_ADDRESS "operators(uint256)(address)" $i --rpc-url $RPC_URL
done

# Verify isOperator mapping for YOUR address
cast call $BRIDGELOCK_ADDRESS "isOperator(address)(bool)" $YOUR_ADDRESS --rpc-url $RPC_URL
# Expected: true

# Verify contract constants
cast call $BRIDGELOCK_ADDRESS "REQUIRED_CONFIRMATIONS()(uint256)" --rpc-url $RPC_URL
# Expected: 3

# Verify WBAIT link
cast call $BRIDGELOCK_ADDRESS "wbait()(address)" --rpc-url $RPC_URL
# Expected: WBAIT contract address
```

### Step 3.4: Functional Test (Testnet Only)

```bash
# Submit a test lock-mint request
# All 5 operators should test their confirmLockMint access
TEST_REQUEST_ID=$(cast keccak "test-$(date +%s)")
TEST_L1_TXID=$(cast keccak "l1-test-tx")
TEST_RECIPIENT=0x1234567890123456789012345678901234567890  # Any test address
TEST_AMOUNT=100000000  # 1 wBAIT (8 decimals)

# Operator 0 submits request (auto-confirms)
cast send $BRIDGELOCK_ADDRESS "requestLockMint(bytes32,bytes32,address,uint256)" \
  $TEST_REQUEST_ID $TEST_L1_TXID $TEST_RECIPIENT $TEST_AMOUNT \
  --rpc-url $RPC_URL --private-key $OPERATOR_0_KEY

# Operators 1, 2 confirm (to reach 3-of-5 threshold)
cast send $BRIDGELOCK_ADDRESS "confirmLockMint(bytes32)" $TEST_REQUEST_ID \
  --rpc-url $RPC_URL --private-key $OPERATOR_1_KEY

cast send $BRIDGELOCK_ADDRESS "confirmLockMint(bytes32)" $TEST_REQUEST_ID \
  --rpc-url $RPC_URL --private-key $OPERATOR_2_KEY

# Verify execution: check LockExecuted event
cast logs --address $BRIDGELOCK_ADDRESS --rpc-url $RPC_URL \
  --from-block latest --to-block latest

# Verify wBAIT was minted to recipient
cast call $WBAIT_ADDRESS "balanceOf(address)(uint256)" $TEST_RECIPIENT --rpc-url $RPC_URL
# Expected: 100000000 (1 wBAIT)
```

### Step 3.5: Deploy to Mainnet

```bash
# ONLY after successful testnet validation + 48h observation period
# Follow the same steps as testnet, but with mainnet RPC

export RPC_URL=https://eth.drpc.org

# Deploy
forge script script/DeployBAIT.s.sol \
  --rpc-url $RPC_URL \
  --constructor-args $WBAIT_ADDRESS \
    $OPERATOR_0 $OPERATOR_1 $OPERATOR_2 $OPERATOR_3 $OPERATOR_4 \
  --broadcast \
  --verify \
  --etherscan-api-key $ETHERSCAN_KEY

# Record mainnet addresses
echo "BRIDGELOCK_ADDRESS=<deployed_address>" >> .env.mainnet
echo "WBAIT_ADDRESS=<deployed_address>" >> .env.mainnet

# Verify on Etherscan
# https://etherscan.io/address/<BRIDGELOCK_ADDRESS>#code
```

---

## 4. Monitoring Setup

### Step 4.1: Install Dependencies

```bash
pip install web3 python-dotenv rich prometheus-client
```

### Step 4.2: Configure Bridge Monitor

```bash
# Copy the monitoring script
mkdir -p ~/bridge-monitor
cp bridge/bridge-monitoring.py ~/bridge-monitor/

# Create .env file
cat > ~/bridge-monitor/.env << 'EOF'
# Required
BRIDGELOCK_ADDRESS=0x...  # Your deployed BridgeLock address
RPC_URL=https://eth.drpc.org  # Free community RPC (primary)

# Your operator identity (for highlighting your pending confirmations)
YOUR_OPERATOR_ADDRESS=0x...  # Your operator address

# Optional alerting
ALERT_WEBHOOK=  # Slack/Discord webhook URL (leave empty if not using)

# Tuning
STALL_THRESHOLD_MIN=30  # Alert if request stalls > 30 min without enough confirmations
RATE_LIMIT_PCT=80  # Alert when daily usage reaches 80% of 100K cap
POLL_INTERVAL=15  # Seconds between block checks
METRICS_PORT=9090  # Prometheus metrics port (0 to disable)

# State persistence
STATE_FILE=bridge-monitor-state.json  # Resume from last processed block on restart
EOF
```

### Step 4.3: Test Bridge Monitor

```bash
# Run in foreground first to verify it works
python3 ~/bridge-monitor/bridge-monitoring.py

# You should see:
# - "Connected to <RPC_URL> (block: <number>)"
# - "Operator [0]: <address>" through "Operator [4]: <address>"
# - "Processing historical events from block X to Y"
# - Dashboard showing current bridge state

# If you see errors:
# - "FATAL: BRIDGELOCK_ADDRESS not set" → Set it in .env
# - "FATAL: Cannot connect to any RPC endpoint" → Try a different RPC_URL
# - Import errors → pip install the missing package
```

### Step 4.4: Run as Systemd Service (Production)

```bash
sudo cat > /etc/systemd/system/bait-bridge-monitor.service << 'EOF'
[Unit]
Description=BAIT BridgeLock Monitor
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=bait-bridge
Group=bait-bridge
WorkingDirectory=/home/bait-bridge/bridge-monitor
ExecStart=/usr/bin/python3 /home/bait-bridge/bridge-monitor/bridge-monitoring.py
Restart=always
RestartSec=30
StartLimitIntervalSec=300
StartLimitBurst=5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/bait-bridge/bridge-monitor
EnvironmentFile=/home/bait-bridge/bridge-monitor/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable bait-bridge-monitor
sudo systemctl start bait-bridge-monitor

# Check status
sudo systemctl status bait-bridge-monitor

# View logs
journalctl -u bait-bridge-monitor -f
```

### Step 4.5: Prometheus Metrics (Optional but Recommended)

The bridge monitor exposes Prometheus metrics on port 9090 (configurable).
Add this to your Prometheus config:

```yaml
scrape_configs:
  - job_name: 'bait-bridge-monitor'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 30s
```

Key metrics exposed:
- `bait_bridge_lock_requests_total` — Total lock-mint requests
- `bait_bridge_lock_requests_pending` — Pending (unconfirmed) requests
- `bait_bridge_burn_releases_total` — Total burn-release requests
- `bait_bridge_burn_releases_pending` — Pending burn-releases
- `bait_bridge_rate_limit_usage_percent` — Rate limit usage per recipient
- `bait_bridge_confirmation_stall_seconds` — Time stalled requests waiting
- `bait_bridge_last_processed_block` — Last block processed

### Step 4.6: Events to Monitor

| Event | Meaning | Your Action |
|-------|---------|-------------|
| `LockRequested` | New lock-mint request submitted | Review and confirm if valid (see §5) |
| `LockConfirmed` | Operator confirmed lock-mint | Track progress toward 3-of-5 |
| `LockExecuted` | 3 confirmations reached, wBAIT minted | Verify correct execution on Etherscan |
| `BurnInitiated` | User burned wBAIT for L1 release | Review and confirm L1 release (see §5) |
| `BurnConfirmed` | Operator confirmed burn-release | Track progress toward 3-of-5 |
| `BurnExecuted` | 3 confirmations reached, L1 release OK | Verify on L1 chain |
| `OperatorUpdated` | Operator address changed | Verify authorized change — ALERT if unexpected |

### Step 4.7: Rate Limit Monitoring

The bridge enforces a **100,000 wBAIT/day/address** rate limit. Your monitor will:

- Alert when any recipient approaches the cap (default: 80% = 80K wBAIT)
- Track daily minted amounts per recipient
- Alert on potential Sybil patterns (many addresses near cap simultaneously)

---

## 5. Confirmation Workflow

### Overview: Request-Verify-Sign-Submit (RVSS)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. DETECT   │────>│  2. VERIFY   │────>│   3. SIGN    │────>│  4. SUBMIT   │
│  (Online)    │     │  (Air-Gap)   │     │   (HSM)      │     │  (Online)    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
  Monitor event        Verify details       Sign via HSM          Broadcast tx
  LockRequested        on air-gapped WS     PKCS#11 call          via RPC
  < 30 sec             < 15 min             < 2 min               < 5 min
```

**Total SLA: < 25 minutes from event detection to on-chain confirmation**

### 5.1: Detect Pending Request

The bridge monitor alerts you of a new `LockRequested` event:

```
┌─────────────────────────────────────────────────┐
│  NEW LOCK REQUEST REQUIRES YOUR CONFIRMATION    │
├─────────────────────────────────────────────────┤
│  Request ID:  0xabcd1234...                     │
│  L1 Tx ID:    0x5678def0...                     │
│  Recipient:   0x9abc2468...                     │
│  Amount:      10,000,000,000 s'AI'toshi (100 wBAIT) │
│  Confirmations: 1/3 (need 2 more)               │
│  Your status: NOT YET CONFIRMED                 │
└─────────────────────────────────────────────────┘
```

### 5.2: Verify on Air-Gapped Workstation

Transfer request details to your air-gapped workstation and verify **ALL** of the following:

#### Lock-Mint Verification Checklist

- [ ] **L1 transaction exists** — Look up l1TxId on BAIT blockchain explorer (offline copy or verified snapshot)
- [ ] **L1 transaction has 6+ confirmations** — Ensure L1 lock is finalized
- [ ] **Amount matches** L1 lock transaction — No amount tampering
- [ ] **Recipient address** is valid and matches expected destination
- [ ] **Rate limit check** — dailyMinted(recipient) + amount <= 100,000 wBAIT/day
- [ ] **No duplicate requestId** — Check this isn't a replay of a previous request
- [ ] **Request is not already executed** — Check LockExecuted event doesn't exist for this requestId
- [ ] **No double-spend indicators** — Same L1 txId not used in another request
- [ ] **Amount is reasonable** — Not suspiciously large for this recipient

#### Burn-Release Verification Checklist

- [ ] **wBAIT was actually burned** — Verify BurnInitiated event with matching releaseId
- [ ] **Burn amount matches** — Amount burned matches amount in release request
- [ ] **L1 release address** is valid BAIT address format (starts with `b'`, proper Bech32)
- [ ] **No double-release** — This releaseId not previously executed
- [ ] **L1 release is safe** — Releasing on L1 won't cause issues (sufficient L1 liquidity)

### 5.3: Sign Confirmation via HSM

```bash
# On AIR-GAPPED workstation:

# 1. Construct confirmation calldata
CALLDATA=$(cast calldata "confirmLockMint(bytes32)" $REQUEST_ID)
echo "Calldata: $CALLDATA"

# 2. Build the transaction (offline)
#    - to: BridgeLock contract address
#    - value: 0
#    - data: $CALLDATA
#    - nonce: get from online system (transfer via QR)
#    - gasLimit: 100,000 (safe overestimate for confirmLockMint)
#    - maxFeePerGas, maxPriorityFeePerGas: get from online system

# 3. Sign via HSM (the private key NEVER leaves the HSM)

# AWS CloudHSM:
SIGNED_TX=$(hsm_sign_evm \
  --key-label "bait-bridge-operator-<N>" \
  --to $BRIDGELOCK_ADDRESS \
  --data "$CALLDATA" \
  --nonce $NONCE \
  --chain-id 1)

# HashiCorp Vault:
# Vault Transit engine signs the hash
SIGNATURE=$(vault write -format=json transit/sign/bait-bridge-operator-<N> \
  input=$(echo -n "$TX_HASH" | base64) | jq -r '.data.signature')

# 4. Output signed transaction for transfer
# Option A: QR code (preferred for air-gap)
echo "$SIGNED_TX" | qrencode -o /tmp/signed_tx.png

# Option B: USB transfer (wipe USB after use)
echo "$SIGNED_TX" > /tmp/signed_tx.hex

# Option C: Print to paper (for audit trail)
echo "$SIGNED_TX" | lp
```

### 5.4: Submit Signed Transaction

```bash
# On ONLINE system (relay node — NO private keys on this machine):

# 1. Read QR code or receive signed tx from air-gapped system
# (Use zbarcam or phone camera app to scan QR)

# 2. Validate signed transaction before broadcasting
#    - Verify to address matches BridgeLock
#    - Verify calldata matches expected confirmLockMint or confirmBurnRelease
#    - Verify nonce is current
#    - Verify from address matches your operator address

# 3. Broadcast via RPC
cast publish $SIGNED_TX --rpc-url $RPC_URL

# 4. Wait for transaction confirmation
#    - Monitor for inclusion in mempool
#    - Wait for >= 12 block confirmations (~2-3 minutes on mainnet)

# 5. Verify on-chain event
#    - Check LockConfirmed(releaseId, yourOperatorAddress) or
#      BurnConfirmed(releaseId, yourOperatorAddress) was emitted
#    - Verify confirmations count incremented
```

### 5.5: Confirmation Best Practices

1. **Never auto-confirm** — Always perform manual verification, even for small amounts
2. **Confirm promptly** — Target < 25 min from event detection to confirmation
3. **Communicate with other operators** — If you see something suspicious, notify before confirming
4. **Don't confirm your own request** — If you submitted requestLockMint, you auto-confirm; others should verify independently
5. **Log all verifications** — Keep a signed log of what you verified and when
6. **Rotate on-call** — Ensure at least 3 operators are available 24/7

---

## 6. Emergency Procedures

### 6.1: Pause Bridge

If you detect **ANY** suspicious activity, request a pause immediately:

```bash
# Only contract OWNER can pause — alert owner via emergency Signal group
# Owner executes on their workstation:
cast send $BRIDGELOCK_ADDRESS "pause()" --rpc-url $RPC_URL --private-key $OWNER_KEY

# Verify paused
cast call $BRIDGELOCK_ADDRESS "paused()(bool)" --rpc-url $RPC_URL
# Expected: true

# WBAIT should also be paused for full halt
cast send $WBAIT_ADDRESS "pause()" --rpc-url $RPC_URL --private-key $OWNER_KEY
```

**When to pause:**
- Unauthorized mint detected
- Suspicious confirmation patterns
- Smart contract vulnerability discovered
- Operator key compromise suspected
- Rate limit exploitation detected
- Any event that threatens the conservation invariant (totalSupply == totalLocked)

### 6.2: Unpause Bridge

After incident resolution and security review:

```bash
# Prerequisites:
# - Root cause analysis complete and documented
# - Vulnerability patched (if applicable)
# - External audit sign-off obtained (for security incidents)
# - All 5 operators notified and agree to resume

# Owner executes:
cast send $BRIDGELOCK_ADDRESS "unpause()" --rpc-url $RPC_URL --private-key $OWNER_KEY
cast send $WBAIT_ADDRESS "unpause()" --rpc-url $RPC_URL --private-key $OWNER_KEY

# Monitor first 10 transactions closely after unpause
```

### 6.3: Operator Key Compromise

If you suspect YOUR key is compromised:

1. **IMMEDIATELY** notify all other operators and coordinator via emergency Signal group
2. **Request contract pause** until key is rotated — this is P1 priority
3. **Disable HSM key** access: set CKA_ENABLED=false (AWS/Azure) or disable key version (Vault)
4. **DO NOT delete** the key — retain for forensic analysis
5. **Generate new key** in HSM per ceremony procedure (§2.3)
6. **Coordinate replacement** via 24h timelock + 3-of-5 confirmation from OTHER operators
7. **External audit** of compromise scope before unpausing

### 6.4: Stuck Transaction Recovery

If a lock-mint or burn-release is stuck (not reaching 3 confirmations):

1. Check which operators have confirmed (use bridge monitor or cast calls)
2. Contact missing operators via out-of-band channel (Signal/phone)
3. If operator is unavailable long-term (>24h), initiate operator replacement
4. If request appears invalid, do NOT confirm — let it remain unconfirmed (safe by design)
5. **For burn-releases**: More urgent — user's wBAIT is already burned. Prioritize getting L1 release confirmed.

### 6.5: Incident Escalation

| Severity | Response Time | Action | Who |
|----------|--------------|--------|-----|
| **P0 CRITICAL** (funds at risk) | < 5 min | Pause bridge, notify all operators + owner | Any operator |
| **P1 HIGH** (key compromise suspected) | < 15 min | Pause bridge, begin rotation | Detecting operator |
| **P2 MEDIUM** (operational issue) | < 1 hour | Investigate, coordinate fix | On-call operator |
| **P3 LOW** (monitoring alert) | < 4 hours | Review during next shift | Any operator |

### 6.6: Contact List

Maintain an **encrypted** contact list with:

- All 5 operators: Signal + phone + email (verified PGP keys)
- Contract owner: Direct phone line + Signal
- HSM provider support:
  - AWS CloudHSM: https://console.aws.amazon.com/support/
  - Azure Key Vault: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade
  - HashiCorp Vault: https://support.hashicorp.com/
- External auditor: Email (PGP-encrypted) for post-incident review
- BAIT L1 blockchain explorer: For verifying L1 lock transactions

---

## 7. Security Hygiene

### Daily Practices

- [ ] Check bridge monitor is running and healthy
- [ ] Review any pending confirmations requiring your action
- [ ] Check for OperatorUpdated events (unexpected changes)
- [ ] Verify HSM audit logs show no unauthorized access attempts
- [ ] Confirm your HSM session is active and responsive

### Weekly Practices

- [ ] Review rate limit usage patterns for anomalies
- [ ] Verify all 5 operators are responsive (ping test)
- [ ] Check HSM firmware version is current
- [ ] Review bridge monitor alert log for missed events
- [ ] Verify backup/restore procedure is functional (staging)

### Monthly Practices

- [ ] Key rotation (if it's your rotation month — see hsm-configuration.json schedule)
- [ ] Full HSM health check (connectivity, signing test, audit log review)
- [ ] Update contact list (verify all operator contact info is current)
- [ ] Review and update this onboarding guide if procedures changed
- [ ] Test emergency pause/unpause on staging

### Never Do

- **NEVER** export your private key from the HSM
- **NEVER** confirm a bridge request without full verification
- **NEVER** auto-sign or batch-confirm requests
- **NEVER** share your HSM PIN or Vault token
- **NEVER** access HSM from a network-connected workstation for signing
- **NEVER** ignore a monitoring alert without investigation
- **NEVER** deploy to mainnet without testnet validation
- **NEVER** modify bridge monitoring thresholds without coordinator approval

---

## 8. Troubleshooting

### Bridge Monitor Won't Connect to RPC

```bash
# Try each free RPC endpoint manually
for rpc in https://eth.drpc.org https://rpc.ankr.com/eth https://ethereum.publicnode.com https://1rpc.io/eth; do
  echo "Testing $rpc..."
  curl -s -X POST $rpc -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | head -c 200
  echo
done

# If all fail: Check your internet connection, firewall, and DNS
```

### HSM Signing Fails

```bash
# AWS CloudHSM: Check client is running
sudo status cloudhsm-client
# If not running: sudo start cloudhsm-client

# Verify HSM connectivity
/opt/cloudhsm/bin/listUsers

# Check if your key exists
/opt/cloudhsm/bin/pkcs11-tool --login --pin=$CLOUDHSM_PIN \
  --list-objects --type pubkey --label "bait-bridge-operator-<N>"

# Vault: Check Vault is unsealed
vault status
# If sealed: You need unseal keys (Shamir) or wait for auto-unseal

# Azure: Check HSM provisioning state
az keyvault show --hsm-name <HSM_NAME> --query properties.provisioningState
```

### Transaction Stuck in Mempool

```bash
# Check if transaction is pending
cast tx $TX_HASH --rpc-url $RPC_URL

# If stuck due to low gas: Speed bump with higher gas
# (requires re-signing with higher gas on air-gapped workstation)

# If nonce is stuck: Check current nonce
cast nonce $YOUR_OPERATOR_ADDRESS --rpc-url $RPC_URL

# Replace with higher-gas transaction (same nonce)
```

### Bridge Monitor Shows Stale Data

```bash
# Check state file for last processed block
python3 -c "import json; print(json.load(open('bridge-monitor-state.json'))['last_block'])"

# If stale: Delete state file to re-process from current block
rm bridge-monitor-state.json

# Or manually set last block
python3 -c "
import json
state = json.load(open('bridge-monitor-state.json'))
state['last_block'] = <DESIRED_BLOCK>
json.dump(state, open('bridge-monitor-state.json', 'w'), indent=2)
"
```

### You Can't Confirm (Transaction Reverts)

```bash
# Common revert reasons:
# "BridgeLock: not operator" — Your address is not in the operator set
#   → Verify: cast call $BRIDGELOCK "isOperator(address)(bool)" $YOUR_ADDR --rpc-url $RPC_URL
#   → If false: Your operator key may have been rotated; contact coordinator

# "BridgeLock: already confirmed" — You already confirmed this request
#   → No action needed; check if other operators need to confirm

# "BridgeLock: already executed" — Request already reached 3 confirmations
#   → No action needed; bridge already executed

# "BridgeLock: not requested" — Invalid requestId
#   → Check the requestId you're using matches the on-chain request

# "Pausable: paused" — Bridge is paused
#   → Contact coordinator; check if emergency pause is in effect
```

---

## 9. Pre-Flight Checklist

Before going live on mainnet, verify ALL of the following:

### Contract Deployment
- [ ] WBAIT deployed and verified on Etherscan
- [ ] BridgeLock deployed and verified on Etherscan
- [ ] WBAIT.bridgeLock == BridgeLock address (conservation invariant)
- [ ] All 5 operators registered and verified (isOperator returns true)
- [ ] REQUIRED_CONFIRMATIONS == 3
- [ ] RATE_LIMIT == 100,000 wBAIT (100,000,000,000,000 s'AI'toshi)
- [ ] TIMELOCK_DURATION == 24 hours (86400 seconds)

### HSM Configuration
- [ ] All 5 operator keys generated in HSM (per ceremony procedure)
- [ ] All keys are non-exportable (verified)
- [ ] All keys are non-derivable (verified)
- [ ] HSM audit logging enabled for all operators
- [ ] HSM backup/restore tested (staging)
- [ ] Key labels follow convention: `bait-bridge-operator-{0-4}`

### Monitoring
- [ ] bridge-monitoring.py running for all operators
- [ ] Prometheus metrics endpoint accessible (if configured)
- [ ] Alert webhook configured and tested (Slack/Discord)
- [ ] Stalled request alerting tested ( Stall threshold configured)
- [ ] Rate limit monitoring active
- [ ] Systemd service configured with auto-restart (Linux)

### Operations
- [ ] Emergency contact list distributed to all operators (encrypted)
- [ ] Signal group created with all 5 operators + owner
- [ ] On-call rotation schedule agreed (at least 3 operators available 24/7)
- [ ] Emergency pause procedure tested (testnet)
- [ ] Operator replacement procedure reviewed by all operators
- [ ] Ceremony transcript archived (PGP-signed, access-controlled)

### Security
- [ ] Air-gapped workstations verified (no network interfaces)
- [ ] Data transfer mechanism tested (QR code or data diode)
- [ ] No private keys on any online system
- [ ] HSM firmware versions match approved list
- [ ] No test/debug keys in production HSM
- [ ] BridgeLock contract source code reviewed by all operators
- [ ] External audit completed (or scheduled within 30 days of launch)

---

## Appendix A: BridgeLock Contract Interface

```solidity
// Lock-Mint Flow
function requestLockMint(bytes32 requestId, bytes32 l1TxId, address recipient, uint256 amount) external onlyOperator
function confirmLockMint(bytes32 requestId) external onlyOperator

// Burn-Release Flow
function initiateBurnRelease(string calldata l1ReleaseAddress) external
function confirmBurnRelease(bytes32 releaseId) external onlyOperator

// Emergency
function pause() external onlyOwner
function unpause() external onlyOwner

// Views
function operators(uint256) external view returns (address)
function isOperator(address) external view returns (bool)
function getLockRequestCount() external view returns (uint256)
function getBurnReleaseCount() external view returns (uint256)
function paused() external view returns (bool)
function dailyMinted(address) external view returns (uint256)
function lastMintDay(address) external view returns (uint256)
function REQUIRED_CONFIRMATIONS() external view returns (uint256)  // 3
function NUM_OPERATORS() external view returns (uint256)           // 5
function RATE_LIMIT() external view returns (uint256)              // 100K * 10^8
function TIMELOCK_DURATION() external view returns (uint256)       // 86400
```

## Appendix B: Constants Reference

| Constant | Value | Description |
|----------|-------|-------------|
| `REQUIRED_CONFIRMATIONS` | 3 | Confirmations needed to execute |
| `NUM_OPERATORS` | 5 | Total operator count |
| `RATE_LIMIT` | 100,000 wBAIT/day | Per-recipient daily mint cap |
| `RATE_LIMIT (s'AI'toshi)` | 10,000,000,000,000 | 100K × 10^8 decimals |
| `TIMELOCK_DURATION` | 24 hours | Delay on operator parameter changes |
| `WBAIT_DECIMALS` | 8 | s'AI'toshi decimal places |
| `WBAIT_MAX_SUPPLY` | 21,000,000 | Maximum wBAIT supply (matches BAIT L1) |
| `BLOCK_CONFIRMATIONS` | 12 | Ethereum blocks to wait for finality |

## Appendix C: Event Signatures (for monitoring)

```
LockRequested(bytes32,bytes32,address,uint256)
LockConfirmed(bytes32,address)
LockExecuted(bytes32,address,uint256)
BurnInitiated(bytes32,address,uint256,string)
BurnConfirmed(bytes32,address)
BurnExecuted(bytes32,uint256,string)
OperatorUpdated(uint256,address,address)
```
