# Hardware Wallet Deployment Guide — b'AI'tcoin (BAIT)

## Overview

This guide documents the secure deployment procedure using hardware wallets for all key material. No private key should ever exist on a network-connected machine without hardware wallet protection.

## Required Equipment

- 1 × Ledger Nano S Plus or Trezor Model T (Deployer)
- 5 × Hardware wallets for Operator keys (1 per operator)
- 1 × Hardware wallet for Backup/Recovery key

## Deployer Wallet Setup

### 1. Initialize Deployer Wallet

```bash
# Connect Ledger/Trezor
# Generate new seed phrase on device (NEVER use a seed from software)
# Record seed phrase on metal backup plate (fire/water resistant)

# Verify device connection
cast wallet address --ledger  # or --trezor
# Expected: shows deployer address
```

### 2. Fund Deployer

```bash
# Send 0.5 ETH (deployment) + 12.5 ETH (liquidity) + 0.5 ETH (buffer) = 13.5 ETH
# Verify balance
cast balance $DEPLOYER_ADDR --rpc-url $MAINNET_RPC_URL
```

## Operator Key Generation (HSM)

### Ceremony Procedure

1. **Each operator** generates a new key on their hardware wallet:
   - New seed phrase on device (NEVER exported)
   - Derive address: `m/44'/60'/0'/0/0`
   - Record address on ceremony document
   - Sign ceremony attestation message

2. **Verification**:
   ```bash
   # Each operator signs a test message
   cast wallet sign --ledger "BAIT Operator Ceremony 2026-09-14"
   ```

3. **Registration**:
   - All 5 operator addresses are recorded in `deploy/create2-addresses.json`
   - Cross-verified by at least 2 other operators
   - Ceremony document signed by all participants

4. **Gnosis Safe Setup**:
   - Deploy Gnosis Safe with 5 operator addresses as owners
   - Set threshold to 3 (3-of-5 multisig)
   - Verify on Etherscan

## Deployment Execution

### Using Hardware Wallet with Forge

```bash
# Forge supports Ledger/Trezor via --ledger or --trezor flags
forge script script/DeployBAITMainnet.s.sol \
  --rpc-url $MAINNET_RPC_URL \
  --ledger \
  --broadcast \
  --verify
```

### Post-Deployment Ownership Transfer

```bash
# Transfer ownership to Gnosis Safe (two-step)
cast send $WBAIT_ADDR 'transferOwnership(address)' $GNOSIS_SAFE_ADDR \
  --rpc-url $MAINNET_RPC_URL --ledger

# Gnosis Safe executes acceptOwnership (3-of-5 signers)
# Use Gnosis Safe Web UI or CLI:
# safe-cli exec $WBAIT_ADDR 'acceptOwnership()'
```

## Key Security Rules

1. **NEVER** export private keys from hardware wallets
2. **NEVER** store private keys in .env files on disk
3. **ALWAYS** verify addresses on device screen before signing
4. **ALWAYS** use separate hardware wallets for deployer vs operators
5. **ALWAYS** keep firmware updated on all devices
6. **NEVER** reuse seed phrases across environments (Sepolia vs Mainnet)

## Emergency Recovery

If the deployer hardware wallet is lost/damaged:
1. Use metal seed backup to restore on new device
2. If ownership already transferred to Gnosis Safe, deployer key is no longer needed
3. Operators can propose emergency actions via 3-of-5 multisig
