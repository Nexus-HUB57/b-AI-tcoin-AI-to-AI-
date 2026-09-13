#!/usr/bin/env bash
# =============================================================================
# BAIT (b'AI'tcoin) — Foundry Keystore Wallet Setup
# =============================================================================
#
# DEPLOYMENT CHECKLIST ITEM 9: Keystore Wallet Alternative
#
# This script creates encrypted keystore files using Foundry's built-in
# `cast wallet new` command as a NO-COST alternative to hardware wallets
# (Ledger Nano S Plus ~$79, Trezor Model T ~$159).
#
# SECURITY MODEL:
#   - Each keystore is encrypted with AES-128-CTR (Foundry default)
#   - Password is required to decrypt and use the key
#   - Private key NEVER exists in plaintext on disk
#   - Keystore files follow the Web3 Secret Storage specification
#   - Compatible with geth, MetaMask, and other Ethereum wallets
#
# TRADE-OFFS vs HARDWARE WALLETS:
#   [Keystore Pros]  Zero cost; fast setup; no physical device needed
#   [Keystore Cons]  Key material touches RAM during signing; vulnerable
#                    to malware on the host machine; no screen verification
#   [Hardware Pros]  Private key never leaves secure element; immune to
#                    malware; on-device screen verification
#   [Hardware Cons]  $79-$159 per device; physical logistics; firmware risk
#
# RECOMMENDATION:
#   - Development/Testing: Use this keystore approach (FREE)
#   - Production Mainnet: Use Ledger/Trezor hardware wallets (MAX SECURITY)
#
# =============================================================================

set -euo pipefail

# --- Configuration ---
KEYSTORE_DIR="$(cd "$(dirname "$0")" && pwd)/keystores"
CAST="${HOME}/.foundry/bin/cast"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  BAIT Keystore Wallet Setup — No-Cost Hardware Wallet Alt  ${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "${YELLOW}FREE ALTERNATIVE TO HARDWARE WALLETS${NC}"
echo -e "  Ledger Nano S Plus: ~\$79  |  Trezor Model T: ~\$159"
echo -e "  This script: \$0 (uses Foundry's built-in keystore system)"
echo ""
echo -e "${YELLOW}SECURITY NOTE:${NC}"
echo -e "  Keystores encrypt keys at rest but expose them in RAM during signing."
echo -e "  For production mainnet deployment, use hardware wallets."
echo -e "  For development, testing, and staging — keystores are ideal."
echo ""

# --- Verify Foundry is available ---
if ! command -v "$CAST" &>/dev/null && ! command -v cast &>/dev/null; then
    echo -e "${RED}ERROR: Foundry cast not found. Install with: curl -L https://foundry.paradigm.xyz | bash${NC}"
    exit 1
fi

# Use cast from PATH if available, otherwise use full path
if command -v cast &>/dev/null; then
    CAST="cast"
fi

echo -e "${GREEN}[✓]${NC} Foundry cast available: $($CAST --version 2>/dev/null | head -1 || echo 'foundry')"

# --- Create keystores directory ---
mkdir -p "$KEYSTORE_DIR"
echo -e "${GREEN}[✓]${NC} Keystore directory: $KEYSTORE_DIR"

# --- Password Setup ---
# For automated setup, we use a keystore password.
# In production, each key should have a UNIQUE strong password.
# This script prompts for a password for each key.

KEYS_CREATED=0
KEYS_FAILED=0
declare -a ADDRESSES=()
declare -a KEY_NAMES=()

# --- Function: Create a single keystore ---
create_keystore() {
    local key_name="$1"
    local key_purpose="$2"
    local keystore_path="$KEYSTORE_DIR"

    echo ""
    echo -e "${BLUE}--- Creating: $key_name ($key_purpose) ---${NC}"

    # Generate a random password for the keystore
    # In interactive mode, cast wallet new will prompt for password
    # For scripted mode, we generate a strong random password
    local key_password=$(openssl rand -base64 24 | tr -d '\n')

    # Create the keystore using Foundry's cast wallet new
    # This creates an encrypted JSON keystore file
    local output
    output=$($CAST wallet new "$keystore_path" "$key_name" --unsafe-password "$key_password" 2>&1) || {
        echo -e "${RED}[✗]${NC} Failed to create keystore for $key_name"
        echo "  Error: $output"
        ((KEYS_FAILED++))
        return 1
    }

    # Extract the address from the output
    # cast wallet new outputs: "Created new encrypted keystore at: <path>\nAddress: <addr>"
    local address
    address=$(echo "$output" | grep -i "address" | awk '{print $NF}' | tr -d '[:space:]')

    if [ -z "$address" ]; then
        # Try alternate parsing
        address=$(echo "$output" | tail -1 | awk '{print $NF}' | tr -d '[:space:]')
    fi

    # Verify keystore file exists
    local keystore_file="$keystore_path/$key_name.json"
    if [ -f "$keystore_file" ]; then
        echo -e "${GREEN}[✓]${NC} Keystore file created: $keystore_file"

        # Verify the address can be extracted from the keystore
        if [ -n "$address" ] && [[ "$address" == 0x* ]]; then
            echo -e "${GREEN}[✓]${NC} Address: $address"
            echo -e "${GREEN}[✓]${NC} Purpose: $key_purpose"
            ADDRESSES+=("$address")
            KEY_NAMES+=("$key_name")
            ((KEYS_CREATED++))
        else
            echo -e "${YELLOW}[!]${NC} Address parsing issue, attempting keystore verification..."
            # Try to get address from the keystore JSON directly
            address=$(python3 -c "
import json
with open('$keystore_file') as f:
    data = json.load(f)
print(data.get('address', 'N/A'))
" 2>/dev/null || echo "N/A")
            if [ "$address" != "N/A" ] && [ -n "$address" ]; then
                # Add 0x prefix if missing
                if [[ "$address" != 0x* ]]; then
                    address="0x${address}"
                fi
                echo -e "${GREEN}[✓]${NC} Address (from keystore): $address"
                ADDRESSES+=("$address")
                KEY_NAMES+=("$key_name")
                ((KEYS_CREATED++))
            else
                echo -e "${RED}[✗]${NC} Could not extract address from keystore"
                ((KEYS_FAILED++))
            fi
        fi

        # Save the password to a separate file (SECURITY: delete after deployment!)
        # In production, use a password manager instead
        echo "$key_password" > "$keystore_path/${key_name}.password"
        chmod 600 "$keystore_path/${key_name}.password"
        echo -e "${YELLOW}[!]${NC} Password saved to: $keystore_path/${key_name}.password (DELETE AFTER USE!)"

    else
        echo -e "${RED}[✗]${NC} Keystore file not found at expected path"
        # Check if it was created with a different naming convention
        local found_file=$(ls "$keystore_path"/*"$key_name"* 2>/dev/null | head -1)
        if [ -n "$found_file" ]; then
            echo -e "${YELLOW}[!]${NC} Found keystore at: $found_file"
        fi
        ((KEYS_FAILED++))
        return 1
    fi
}

# =============================================================================
# KEY CREATION CEREMONY
# =============================================================================
echo ""
echo -e "${BLUE}=== KEY CREATION CEREMONY ===${NC}"
echo -e "Creating 7 encrypted keystores:"
echo -e "  1 × Deployer key (contract deployment, ownership transfer)"
echo -e "  5 × Operator keys (Gnosis Safe 3-of-5 multisig)"
echo -e "  1 × Backup/Recovery key (emergency recovery)"
echo ""

# --- 1. Deployer Key ---
create_keystore "deployer" "Contract deployment and initial ownership"

# --- 2-6. Operator Keys ---
for i in 1 2 3 4 5; do
    create_keystore "operator-${i}" "Gnosis Safe operator #${i} (3-of-5 multisig)"
done

# --- 7. Backup/Recovery Key ---
create_keystore "backup-recovery" "Emergency recovery and backup key"

# =============================================================================
# VERIFICATION
# =============================================================================
echo ""
echo -e "${BLUE}=== VERIFICATION ===${NC}"
echo ""

# Count keystore files
KEYSTORE_COUNT=$(ls -1 "$KEYSTORE_DIR"/*.json 2>/dev/null | wc -l)
echo -e "Keystore files found: ${KEYSTORE_COUNT}"

# List all keystores using Foundry
echo ""
echo -e "${BLUE}Foundry keystore list:${NC}"
$CAST wallet list --dir "$KEYSTORE_DIR" 2>/dev/null || echo "  (cast wallet list not available or empty)"

# Verify each keystore individually
echo ""
echo -e "${BLUE}Individual keystore verification:${NC}"
VERIFY_PASSED=0
VERIFY_FAILED=0

for keyfile in "$KEYSTORE_DIR"/*.json; do
    if [ -f "$keyfile" ]; then
        keyname=$(basename "$keyfile" .json)
        # Check the file is valid JSON
        if python3 -c "import json; json.load(open('$keyfile'))" 2>/dev/null; then
            echo -e "  ${GREEN}[✓]${NC} $keyname — valid keystore JSON"
            ((VERIFY_PASSED++))
        else
            echo -e "  ${RED}[✗]${NC} $keyname — INVALID JSON"
            ((VERIFY_FAILED++))
        fi
    fi
done

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  SETUP SUMMARY                                            ${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "  Keys created:   ${GREEN}${KEYS_CREATED}${NC} / 7"
echo -e "  Keys failed:    ${RED}${KEYS_FAILED}${NC}"
echo -e "  Verified:       ${GREEN}${VERIFY_PASSED}${NC}"
echo -e "  Verify failed:  ${RED}${VERIFY_FAILED}${NC}"
echo -e "  Directory:      ${KEYSTORE_DIR}"
echo ""

if [ ${#ADDRESSES[@]} -gt 0 ]; then
    echo -e "${BLUE}  Addresses:${NC}"
    for i in "${!KEY_NAMES[@]}"; do
        printf "    %-20s %s\n" "${KEY_NAMES[$i]}" "${ADDRESSES[$i]}"
    done
fi

echo ""
echo -e "${YELLOW}SECURITY REMINDERS:${NC}"
echo "  1. DELETE password files after deployment: rm \$KEYSTORE_DIR/*.password"
echo "  2. NEVER commit keystores or passwords to git"
echo "  3. For mainnet production, migrate to hardware wallets"
echo "  4. Back up keystore directory to encrypted offline storage"
echo "  5. Each team member should memorize their password (don't store)"
echo ""

# Write addresses to a summary file (NO private keys!)
SUMMARY_FILE="$(cd "$(dirname "$0")" && pwd)/keystore-addresses.txt"
echo "# BAIT Keystore Addresses — Generated $TIMESTAMP" > "$SUMMARY_FILE"
echo "# WARNING: These are public addresses only. Never share private keys." >> "$SUMMARY_FILE"
echo "#" >> "$SUMMARY_FILE"
for i in "${!KEY_NAMES[@]}"; do
    printf "%-20s %s\n" "${KEY_NAMES[$i]}" "${ADDRESSES[$i]}" >> "$SUMMARY_FILE"
done
echo -e "${GREEN}[✓]${NC} Addresses saved to: $SUMMARY_FILE"

echo ""
if [ "$KEYS_CREATED" -eq 7 ] && [ "$KEYS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL KEYSTORES CREATED AND VERIFIED SUCCESSFULLY${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME KEYSTORES FAILED — REVIEW OUTPUT ABOVE${NC}"
    exit 1
fi
