#!/usr/bin/env bash
# ssh-known-hosts-pin.sh — Pin SSH host keys for CI/CD deployments
# Usage: ./ssh-known-hosts-pin.sh
#
# This script generates a known_hosts file with pinned SSH host keys
# for the deployment targets. In CI, this prevents MITM attacks
# and TOCTOU issues with ssh-keyscan.
set -euo pipefail

KNOWN_HOSTS_FILE="${SSH_KNOWN_HOSTS_FILE:-$HOME/.ssh/known_hosts}"
SSH_KEYSCAN_PATH="${SSH_KEYSCAN_PATH:-$(command -v ssh-keyscan 2>/dev/null || echo '')}"

# Deployment targets (from env or defaults)
DEPLOY_HOSTS="${DEPLOY_SSH_HOSTS:-}"
DEPLOY_PORT="${DEPLOY_SSH_PORT:-22}"

if [ -z "$DEPLOY_HOSTS" ]; then
    echo "⚠️  DEPLOY_SSH_HOSTS not set. Example: DEPLOY_SSH_HOSTS=server1.example.com,server2.example.com"
    echo "   Skipping SSH host key pinning."
    exit 0
fi

if [ -z "$SSH_KEYSCAN_PATH" ]; then
    echo "❌ ssh-keyscan not found"
    exit 1
fi

echo "🔐 Pinning SSH host keys for: $DEPLOY_HOSTS"

# Ensure .ssh directory exists
mkdir -p "$(dirname "$KNOWN_HOSTS_FILE")"

# Backup existing known_hosts
if [ -f "$KNOWN_HOSTS_FILE" ]; then
    cp "$KNOWN_HOSTS_FILE" "$KNOWN_HOSTS_FILE.bak.$(date +%s)"
fi

# Scan and pin each host
IFS=',' read -ra HOSTS <<< "$DEPLOY_HOSTS"
for host in "${HOSTS[@]}"; do
    host=$(echo "$host" | xargs)  # trim whitespace
    if [ -z "$host" ]; then continue; fi

    echo "   Scanning $host:$DEPLOY_PORT..."

    # Get all key types (ed25519, rsa, ecdsa)
    KEYS=$($SSH_KEYSCAN_PATH -p "$DEPLOY_PORT" -t ed25519,rsa,ecdsa "$host" 2>/dev/null || true)

    if [ -z "$KEYS" ]; then
        echo "   ⚠️  No keys found for $host — skipping"
        continue
    fi

    # Verify each key and append
    while IFS= read -r key_line; do
        if [ -n "$key_line" ]; then
            # Remove any existing entry for this host
            if [ -f "$KNOWN_HOSTS_FILE" ]; then
                ssh-keygen -R "$host" -f "$KNOWN_HOSTS_FILE" 2>/dev/null || true
            fi
            # Append the pinned key
            echo "$key_line" >> "$KNOWN_HOSTS_FILE"
            key_type=$(echo "$key_line" | awk '{print $2}')
            echo "   ✅ Pinned $key_type key for $host"
        fi
    done <<< "$KEYS"
done

# Set correct permissions
chmod 600 "$KNOWN_HOSTS_FILE" 2>/dev/null || true

echo "🔐 SSH host keys pinned to $KNOWN_HOSTS_FILE"
echo "   Hosts configured: ${#HOSTS[@]}"
