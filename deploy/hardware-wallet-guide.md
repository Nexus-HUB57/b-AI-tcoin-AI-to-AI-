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

---

## Alternativa sem Custo: Foundry Keystore

### Visão Geral

Para equipes que não possuem hardware wallets disponíveis imediatamente, o **Foundry Keystore** oferece uma alternativa **100% gratuita** que utiliza o sistema de keystore criptografado nativo do Foundry (`cast wallet`). Isso atende ao **item 9 do checklist de deployment**.

### Como Funciona

O Foundry Keystore cria arquivos JSON criptografados (Web3 Secret Storage v3) que armazenam chaves privadas protegidas por senha:

1. **Criação**: `cast wallet new <diretório> <nome> --password`
2. **Criptografia**: AES-128-CTR com chave derivada via scrypt (KDF)
3. **Verificação**: `cast wallet address --keystore <caminho> --password`
4. **Assinatura**: `cast wallet sign "mensagem" --keystore <caminho> --password`
5. **Deployment**: `forge script --keystore <caminho> --password --broadcast`

### Configuração Rápida

```bash
# Executar o script de setup automatizado
./deploy/keystore-wallet-setup.sh

# Ou criar keystores manualmente:
KEYSTORE_DIR=deploy/keystores

# Deployer
cast wallet new $KEYSTORE_DIR deployer --password

# 5 Operadores
for i in 1 2 3 4 5; do
  cast wallet new $KEYSTORE_DIR operator-$i --password
done

# Backup/Recovery
cast wallet new $KEYSTORE_DIR backup-recovery --password

# Listar todos
cast wallet list --dir $KEYSTORE_DIR
```

### Deploy com Keystore

```bash
# Deploy usando keystore em vez de hardware wallet
forge script script/DeployBAITMainnet.s.sol \
  --rpc-url $MAINNET_RPC_URL \
  --keystore deploy/keystores/deployer \
  --password \
  --broadcast \
  --verify
```

### Comparação de Segurança: Keystore vs Hardware Wallet

| Aspecto | Foundry Keystore | Hardware Wallet (Ledger/Trezor) |
|---------|-----------------|--------------------------------|
| **Custo** | $0 (gratuito) | $79-$159 por dispositivo |
| **Chave em repouso** | Criptografada (AES-128-CTR) | Nunca sai do secure element |
| **Chave durante signing** | Exposta na RAM | Nunca sai do dispositivo |
| **Verificação visual** | Não (apenas no terminal) | Sim (tela do dispositivo) |
| **Resistência a malware** | Baixa (host comprometido = chave vazada) | Alta (chave isolada no hardware) |
| **Facilidade de setup** | Alta (1 comando) | Média (requer dispositivo físico) |
| **Backup** | Arquivo JSON + senha | Seed phrase em metal |
| **Custo total (7 chaves)** | $0 | $553-$1,113 |

### Quando Usar Cada Opção

**Use Foundry Keystore (esta alternativa) quando:**
- Desenvolvimento e testing local
- Deploy em testnets (Sepolia, Goerli)
- Staging/preview environments
- Protótipos e provas de conceito
- Equipe sem orçamento para hardware wallets imediato

**Use Hardware Wallet (Ledger/Trezor) quando:**
- **Production mainnet deployment**
- Gerenciamento de fundos > $10,000
- Contratos com ownership de tokens listados em exchanges
- Qualquer operação na mainnet com valor real
- Compliance e auditoria requerem HSM

### Migração de Keystore para Hardware Wallet

O processo de migração é simples porque apenas os **endereços** importam no contexto do Gnosis Safe:

1. Gere o mesmo número de chaves nos hardware wallets
2. Transfira ownership do Gnosis Safe para incluir os novos endereços (swapOwner)
3. Fund os novos endereços com ETH para gas
4. Teste assinatura com hardware wallets
5. Remova os antigos endereços do keystore do Gnosis Safe
6. **Destrua** os arquivos keystore com segurança: `shred -u deploy/keystores/*.json`

### Arquivos de Configuração

- **Script de setup**: `deploy/keystore-wallet-setup.sh`
- **Configuração**: `deploy/keystore-config.json`
- **Diretório de keystores**: `deploy/keystores/`
- **Verificação**: `deploy/keystore-verification.json`

### Avisos de Segurança

> ⚠️ **Keystore passwords são o único fator de proteção.** Se a senha for fraca ou vazada, a chave é comprometida.

> ⚠️ **Malware no host pode capturar chaves durante signing.** Keystores protegen chaves em repouso, mas não durante uso ativo na memória.

> ⚠️ **Para mainnet com valor real, USE HARDWARE WALLETS.** Esta alternativa é para desenvolvimento e staging apenas.
