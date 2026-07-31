#!/usr/bin/env bash
# ==============================================================
# b'AI'tcoin + Obscura — Sandbox Entrypoint
# ==============================================================
# Starts Obscura CDP server + b'AI'tcoin daemon
# ==============================================================

set -euo pipefail

OBSCURA_PORT=${OBSCURA_PORT:-9222}
OBSCURA_HOST=${OBSCURA_HOST:-127.0.0.1}
BAITCOIN_API_PORT=${BAITCOIN_API_PORT:-18445}
BAITCOIN_P2P_PORT=${BAITCOIN_P2P_PORT:-18444}

LOG_DIR="/home/baitcoin/logs"
mkdir -p "$LOG_DIR"

echo "==========================================="
echo " b'AI'tcoin + Obscura Sandbox"
echo " Version: 0.2.1"
echo " Obscura CDP: ${OBSCURA_HOST}:${OBSCURA_PORT}"
echo " b'AI'tcoin API: :${BAITCOIN_API_PORT}"
echo " b'AI'tcoin P2P: :${BAITCOIN_P2P_PORT}"
echo "==========================================="

# --- 1. Start Obscura CDP Server ---
echo "[obscura] Starting CDP server on port ${OBSCURA_PORT}..."
if command -v obscura &> /dev/null; then
    obscura serve \
        --port "$OBSCURA_PORT" \
        --host "$OBSCURA_HOST" \
        ${OBSCURA_STEALTH:+--stealth} \
        > "$LOG_DIR/obscura.log" 2>&1 &
    OBSCURA_PID=$!
    echo "[obscura] PID: $OBSCURA_PID"
    
    # Wait for Obscura to be ready
    for i in $(seq 1 30); do
        if curl -sf "http://${OBSCURA_HOST}:${OBSCURA_PORT}/json/version" &> /dev/null; then
            echo "[obscura] Ready (took ${i}s)"
            break
        fi
        sleep 1
    done
else
    echo "[obscura] Binary not found — running without browser"
fi

# --- 2. Start b'AI'tcoin Daemon ---
echo "[baitcoin] Starting daemon..."
cd /home/baitcoin/ecosystem
python main_daemon.py \
    --api-port "$BAITCOIN_API_PORT" \
    --p2p-port "$BAITCOIN_P2P_PORT" \
    > "$LOG_DIR/baitcoin.log" 2>&1 &
BAITCOIN_PID=$!
echo "[baitcoin] PID: $BAITCOIN_PID"

# --- 3. Wait for readiness ---
echo "[health] Waiting for b'AI'tcoin API..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${BAITCOIN_API_PORT}/status" &> /dev/null; then
        echo "[health] b'AI'tcoin API ready (took ${i}s)"
        break
    fi
    sleep 1
done

echo "==========================================="
echo " Sandbox ready"
echo " Obscura CDP: ws://${OBSCURA_HOST}:${OBSCURA_PORT}"
echo " b'AI'tcoin API: http://localhost:${BAITCOIN_API_PORT}"
echo " P2P: :${BAITCOIN_P2P_PORT}"
echo "==========================================="

# --- 4. Keep container alive ---
trap "echo 'Shutting down...'; kill $OBSCURA_PID 2>/dev/null; kill $BAITCOIN_PID 2>/dev/null; wait" SIGTERM SIGINT
wait