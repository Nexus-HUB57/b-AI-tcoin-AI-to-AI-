#!/usr/bin/env bash
#
# Free RPC Endpoint Validation Script for BAIT (b'AI'tcoin) Project
# Tests each free RPC endpoint with eth_blockNumber, measures latency, outputs JSON results
#
# Usage: bash deploy/validate-free-rpc.sh
# Output: deploy/free-rpc-validation-results.json
#

set -euo pipefail

# Output file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="${SCRIPT_DIR}/free-rpc-validation-results.json"

# RPC endpoints to test
declare -a MAINNET_ENDPOINTS=(
  "LlamaRPC|https://eth.llamarpc.com"
  "Ankr|https://rpc.ankr.com/eth"
  "Cloudflare|https://cloudflare-eth.com"
)

declare -a SEPOLIA_ENDPOINTS=(
  "LlamaRPC|https://sepolia.llamarpc.com"
  "Ankr|https://rpc.ankr.com/eth_sepolia"
)

# JSON-RPC payload
RPC_PAYLOAD='{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Temp files for results
MAINNET_RESULTS=""
SEPOLIA_RESULTS=""

# Function to test an RPC endpoint
test_rpc() {
  local name="$1"
  local url="$2"
  local start_time end_time latency_ms response block_number success

  start_time=$(date +%s%N 2>/dev/null || python3 -c "import time; print(int(time.time()*1e9))")

  # Attempt the RPC call with a 10-second timeout
  response=$(curl -s -m 10 -X POST -H "Content-Type: application/json" --data "$RPC_PAYLOAD" "$url" 2>&1) || true

  end_time=$(date +%s%N 2>/dev/null || python3 -c "import time; print(int(time.time()*1e9))")

  # Calculate latency
  latency_ms=$(( (end_time - start_time) / 1000000 ))

  # Check if response contains a valid result
  if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'result' in d; print(d['result'])" 2>/dev/null; then
    success="true"
    block_number=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])")
  else
    success="false"
    block_number="null"
  fi

  # Output JSON fragment for this endpoint
  cat <<EOF
    {
      "name": "${name}",
      "url": "${url}",
      "success": ${success},
      "latencyMs": ${latency_ms},
      "blockNumber": "${block_number}",
      "error": $([ "${success}" = "true" ] && echo "null" || echo "\"$(echo "${response}" | head -c 200 | sed 's/"/\\"/g')\"")
    }
EOF
}

echo "🔍 Validating Free RPC Endpoints for BAIT Project..."
echo ""

# Test Mainnet endpoints
echo "📡 Testing Mainnet RPC endpoints..."
MAINNET_JSON="["
FIRST=true
for entry in "${MAINNET_ENDPOINTS[@]}"; do
  IFS='|' read -r name url <<< "$entry"
  echo "  Testing ${name} (${url})..."

  result=$(test_rpc "$name" "$url")

  if [ "$FIRST" = true ]; then
    MAINNET_JSON="${MAINNET_JSON}
${result}"
    FIRST=false
  else
    MAINNET_JSON="${MAINNET_JSON},
${result}"
  fi
done
MAINNET_JSON="${MAINNET_JSON}
  ]"

echo ""

# Test Sepolia endpoints
echo "📡 Testing Sepolia RPC endpoints..."
SEPOLIA_JSON="["
FIRST=true
for entry in "${SEPOLIA_ENDPOINTS[@]}"; do
  IFS='|' read -r name url <<< "$entry"
  echo "  Testing ${name} (${url})..."

  result=$(test_rpc "$name" "$url")

  if [ "$FIRST" = true ]; then
    SEPOLIA_JSON="${SEPOLIA_JSON}
${result}"
    FIRST=false
  else
    SEPOLIA_JSON="${SEPOLIA_JSON},
${result}"
  fi
done
SEPOLIA_JSON="${SEPOLIA_JSON}
  ]"

echo ""

# Get timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Write final JSON output
cat > "$OUTPUT_FILE" <<FINALJSON
{
  "description": "Free RPC endpoint validation results for BAIT (b'AI'tcoin) project",
  "timestamp": "${TIMESTAMP}",
  "method": "eth_blockNumber",
  "mainnet": ${MAINNET_JSON},
  "sepolia": ${SEPOLIA_JSON},
  "anvil": {
    "name": "Anvil Local",
    "url": "http://127.0.0.1:8545",
    "note": "Anvil must be running locally to test. Start with: anvil"
  },
  "summary": "See individual endpoint results for availability and latency",
  "generatedBy": "deploy/validate-free-rpc.sh"
}
FINALJSON

echo "✅ Validation complete! Results written to: ${OUTPUT_FILE}"
echo ""
echo "📊 Quick Summary:"
python3 -c "
import json, sys
try:
    with open('${OUTPUT_FILE}') as f:
        data = json.load(f)
    for network in ['mainnet', 'sepolia']:
        print(f'  {network.upper()}:')
        for ep in data.get(network, []):
            status = '✅ OK' if ep['success'] else '❌ FAIL'
            latency = f'{ep[\"latencyMs\"]}ms' if ep['success'] else 'N/A'
            block = ep.get('blockNumber', 'N/A')
            print(f'    {ep[\"name\"]}: {status} ({latency}) Block: {block}')
except Exception as e:
    print(f'  Error reading results: {e}')
" 2>/dev/null || echo "  (Install python3 for summary display)"
