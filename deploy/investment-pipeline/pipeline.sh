#!/bin/bash
#
# BAIT Investment Pipeline — Shell Wrapper
# ========================================
# Wrapper script for the Python pipeline CLI.
# Handles environment setup and validation.
#
# Usage:
#   ./pipeline.sh preflight     # Pre-flight check
#   ./pipeline.sh balances      # Check balances
#   ./pipeline.sh phase1        # Execute Phase 1
#   ./pipeline.sh phase2        # Execute Phase 2
#   ./pipeline.sh full          # Full pipeline
#   ./pipeline.sh simulate      # Testnet simulation
#   ./pipeline.sh status        # Pipeline status
#   ./pipeline.sh stop reason   # Emergency stop
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="${SCRIPT_DIR}"
LOG_DIR="${SCRIPT_DIR}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  BAIT Investment Pipeline — API Synchronized         ║"
    echo "║  BTC Custody → Binance Swap → ETH → Mainnet Deploy  ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_env() {
    local missing=0
    
    if [ -z "${BINANCE_API_KEY:-}" ]; then
        echo -e "${RED}ERROR: BINANCE_API_KEY not set${NC}"
        missing=1
    fi
    
    if [ -z "${BINANCE_API_SECRET:-}" ]; then
        echo -e "${RED}ERROR: BINANCE_API_SECRET not set${NC}"
        missing=1
    fi
    
    if [ "$missing" -eq 1 ]; then
        echo ""
        echo "Set environment variables:"
        echo "  export BINANCE_API_KEY='your_key'"
        echo "  export BINANCE_API_SECRET='your_secret'"
        echo "  export BINANCE_USE_TESTNET='true'  # Use testnet for safety"
        echo ""
        return 1
    fi
    
    return 0
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: python3 not found${NC}"
        return 1
    fi
    
    # Check required packages
    python3 -c "import requests" 2>/dev/null || {
        echo -e "${YELLOW}Installing required package: requests${NC}"
        pip3 install requests --quiet
    }
    
    return 0
}

# ─── Main ────────────────────────────────────────────────────────────

banner

COMMAND="${1:-}"
shift || true

case "$COMMAND" in
    preflight|balances|status|stop)
        # These commands don't require API keys
        check_python
        cd "$PIPELINE_DIR"
        python3 pipeline_cli.py "$COMMAND" "$@"
        ;;
    
    phase1|phase2|full)
        # These commands require API keys
        check_env
        check_python
        cd "$PIPELINE_DIR"
        echo -e "${YELLOW}⚠️  This will execute REAL trades on Binance!${NC}"
        echo -e "${YELLOW}   Testnet: ${BINANCE_USE_TESTNET:-true}${NC}"
        read -p "Continue? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 pipeline_cli.py "$COMMAND" "$@"
        else
            echo "Aborted."
            exit 0
        fi
        ;;
    
    simulate)
        # Testnet simulation — safe
        export BINANCE_USE_TESTNET="true"
        check_env
        check_python
        cd "$PIPELINE_DIR"
        echo -e "${GREEN}Running in TESTNET mode — no real funds${NC}"
        python3 pipeline_cli.py simulate "$@"
        ;;
    
    *)
        echo "Usage: $0 {preflight|balances|phase1|phase2|full|simulate|status|stop}"
        echo ""
        echo "Commands:"
        echo "  preflight  — Pre-flight check (dry run)"
        echo "  balances   — Check all balances"
        echo "  phase1     — Execute Phase 1 (0.01 BTC → deploy gas)"
        echo "  phase2     — Execute Phase 2 (0.20 BTC → liquidity)"
        echo "  full       — Execute full pipeline (Phase 1+2)"
        echo "  simulate   — Testnet simulation (safe)"
        echo "  status     — Pipeline status"
        echo "  stop       — Emergency stop"
        exit 1
        ;;
esac
