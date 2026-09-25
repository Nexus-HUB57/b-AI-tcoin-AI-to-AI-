#!/usr/bin/env bash
# slither-refresh.sh — Run Slither static analysis on BAIT contracts
# Usage: ./slither-refresh.sh [contract_dir]
# Default: contracts/ in the repo root
set -euo pipefail

CONTRACT_DIR="${1:-$(dirname "$0")}"
REPORT_DIR="$(dirname "$0")/slither-reports"
mkdir -p "$REPORT_DIR"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
REPORT_FILE="$REPORT_DIR/slither-$TIMESTAMP.json"
SUMMARY_FILE="$REPORT_DIR/slither-$TIMESTAMP.txt"

echo "🔍 Slither analysis: $CONTRACT_DIR"
echo "   Report → $REPORT_FILE"

# Check slither is installed
if ! command -v slither &>/dev/null; then
    echo "⚠️  slither not found. Installing..."
    pip install slither-analyzer
fi

# Run Slither with JSON output
slither "$CONTRACT_DIR" \
    --config-file "$CONTRACT_DIR/.slither.config.json" \
    --json "$REPORT_FILE" \
    2>&1 | tee "$SUMMARY_FILE"

# Count findings
HIGH=$(python3 -c "import json; d=json.load(open('$REPORT_FILE')); print(d.get('high',0))" 2>/dev/null || echo "?")
MED=$(python3 -c "import json; d=json.load(open('$REPORT_FILE')); print(d.get('medium',0))" 2>/dev/null || echo "?")
LOW=$(python3 -c "import json; d=json.load(open('$REPORT_FILE')); print(d.get('low',0))" 2>/dev/null || echo "?")
INFO=$(python3 -c "import json; d=json.load(open('$REPORT_FILE')); print(d.get('informational',0))" 2>/dev/null || echo "?")

echo ""
echo "📊 Findings: HIGH=$HIGH  MED=$MED  LOW=$LOW  INFO=$INFO"
echo "📄 Full report: $REPORT_FILE"

# Fail CI on HIGH findings
if [ "$HIGH" != "0" ] && [ "$HIGH" != "?" ]; then
    echo "❌ HIGH severity findings detected!"
    exit 1
fi

echo "✅ No HIGH severity findings"
