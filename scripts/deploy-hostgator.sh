#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  b'AI'tcoin — Auto-Deploy HostGator v1.0
#  Execute via cPanel Terminal:
#    bash <(curl -sL https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/scripts/deploy-hostgator.sh)
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

HOME_DIR="${HOME:-/home1/luca2490}"
PUBLIC_HTML="$HOME_DIR/public_html"
BAIT_DIR="$HOME_DIR/baitcoin-api"
REPO_RAW="https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main"
DAEMON_PIDFILE="$BAIT_DIR/daemon.pid"
DAEMON_PORT=18445
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

banner() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║  b'AI'tcoin — Auto-Deploy HostGator v1.0                   ║"
  echo "║  $(date -u '+%Y-%m-%d %H:%M:%S UTC')                            ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
}

download_file() {
  local src="$1" dst="$2" desc="$3"
  log_info "Downloading $desc..."
  curl -sL "$src" -o "$dst" 2>/dev/null
  if [ -f "$dst" ] && [ $(wc -c < "$dst") -gt 100 ]; then
    log_ok "$desc ($(du -sh "$dst" | cut -f1))"
    return 0
  else
    log_error "Failed to download $desc"
    return 1
  fi
}

stop_daemon() {
  log_info "Stopping daemon..."
  if [ -f "$DAEMON_PIDFILE" ]; then
    local pid=$(cat "$DAEMON_PIDFILE" 2>/dev/null || echo "")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 2
      kill -9 "$pid" 2>/dev/null || true
      log_ok "Daemon PID $pid stopped"
    fi
    rm -f "$DAEMON_PIDFILE"
  fi
  # Also kill anything on our port
  if command -v fuser &>/dev/null; then
    fuser -k ${DAEMON_PORT}/tcp 2>/dev/null || true
  fi
  # Kill orphan python processes running main_daemon
  pkill -f "main_daemon.py" 2>/dev/null || true
  sleep 1
  log_ok "All daemon processes cleaned"
}

# ═══════════════════════════════════════════════════════════════════════
#  MAIN DEPLOY SEQUENCE
# ═══════════════════════════════════════════════════════════════════════

banner

# ── Step 0: Stop daemon ──
stop_daemon

# ── Step 1: Update static HTML files ──
log_info "[1/5] Updating static files..."
mkdir -p "$PUBLIC_HTML"

for file in index.html bainkr.html api.cgi .htaccess whitepaper.pdf; do
  if download_file "$REPO_RAW/netlify/$file" "$PUBLIC_HTML/$file" "$file"; then
    if [[ "$file" == *.cgi ]]; then
      chmod +x "$PUBLIC_HTML/$file"
    else
      chmod 644 "$PUBLIC_HTML/$file"
    fi
  else
    log_warn "Could not update $file — keeping existing"
  fi
done

log_ok "Static files updated"

# ── Step 2: Update daemon code ──
log_info "[2/5] Updating daemon code..."
mkdir -p "$BAIT_DIR"

# Core daemon
for file in main_daemon.py daemon_wrapper.py daemon_production.py requirements.txt; do
  if download_file "$REPO_RAW/$file" "$BAIT_DIR/$file" "$file"; then
    log_ok "Updated $file"
  fi
done

# Module directories
for mod in baitcoin_core baitcoin_ai baitcoin_api baitcoin_bank baitcoin_token \
           baitcoin_wallet baitcoin_faucet baitcoin_sdk baitcoin_memory \
           baitcoin_explorer baitcoin_obscura baitcoin_bridge baitcoin_mainnet \
           baitcoin_whitelabel config; do
  mkdir -p "$BAIT_DIR/$mod"
  # Download all .py files in the module
  for pyfile in $(curl -sL "https://api.github.com/repos/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/contents/$mod" 2>/dev/null \
    | python3 -c "import sys,json; [print(f['name']) for f in json.load(sys.stdin) if f['name'].endswith('.py')]" 2>/dev/null); do
    download_file "$REPO_RAW/$mod/$pyfile" "$BAIT_DIR/$mod/$pyfile" "$mod/$pyfile" 2>/dev/null || true
  done
done

# Watchdog
if download_file "$REPO_RAW/netlify/watchdog.sh" "$BAIT_DIR/watchdog.sh" "watchdog.sh"; then
  chmod +x "$BAIT_DIR/watchdog.sh"
fi

# Install dependencies
if [ -f "$BAIT_DIR/requirements.txt" ]; then
  log_info "Installing Python dependencies..."
  pip3 install -q -r "$BAIT_DIR/requirements.txt" 2>/dev/null || true
  log_ok "Dependencies installed"
fi

log_ok "Daemon code updated"

# ── Step 3: Setup virtual env if needed ──
if [ ! -d "$BAIT_DIR/venv" ]; then
  log_info "[3/5] Creating Python venv..."
  python3 -m venv "$BAIT_DIR/venv" 2>/dev/null || true
  if [ -f "$BAIT_DIR/venv/bin/pip" ]; then
    "$BAIT_DIR/venv/bin/pip" install -q -r "$BAIT_DIR/requirements.txt" 2>/dev/null || true
  fi
  log_ok "Venv ready"
else
  log_info "[3/5] Venv exists — updating deps..."
  if [ -f "$BAIT_DIR/venv/bin/pip" ]; then
    "$BAIT_DIR/venv/bin/pip" install -q -r "$BAIT_DIR/requirements.txt" 2>/dev/null || true
  fi
  log_ok "Venv updated"
fi

# ── Step 4: Set permissions ──
log_info "[4/5] Setting permissions..."
chmod +x "$PUBLIC_HTML/api.cgi" 2>/dev/null || true
chmod +x "$BAIT_DIR/watchdog.sh" 2>/dev/null || true
chmod 644 "$PUBLIC_HTML/index.html" "$PUBLIC_HTML/bainkr.html" 2>/dev/null || true
chmod 644 "$PUBLIC_HTML/.htaccess" 2>/dev/null || true
log_ok "Permissions set"

# ── Step 5: Health check ──
log_info "[5/5] Running health check..."
# The watchdog cron or CGI auto-start will handle daemon startup
# We just verify the files are in place

ERRORS=0
if [ ! -f "$PUBLIC_HTML/index.html" ]; then log_error "index.html missing"; ERRORS=$((ERRORS+1)); fi
if [ ! -f "$PUBLIC_HTML/api.cgi" ]; then log_error "api.cgi missing"; ERRORS=$((ERRORS+1)); fi
if [ ! -f "$BAIT_DIR/main_daemon.py" ]; then log_error "main_daemon.py missing"; ERRORS=$((ERRORS+1)); fi
if [ ! -f "$BAIT_DIR/venv/bin/python3" ] && [ ! -f "$BAIT_DIR/venv/bin/python" ]; then
  log_warn "Venv python not found — system python will be used"
fi

# ═══════════════════════════════════════════════════════════════════════
#  RESULT
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
if [ $ERRORS -eq 0 ]; then
  echo -e "║  ${GREEN}DEPLOY SUCCESSFUL${NC}                                           ║"
else
  echo -e "║  ${YELLOW}DEPLOY COMPLETED WITH ${ERRORS} WARNINGS${NC}                          ║"
fi
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Files updated in ~/public_html/                          ║"
echo "║  Daemon code updated in ~/baitcoin-api/                    ║"
echo "║                                                              ║"
echo "║  Next:                                                       ║"
echo "║  1. Verify: curl http://127.0.0.1:18445/api/v1/status       ║"
echo "║  2. Visit: https://www.mybait.org/                          ║"
echo "║  3. Cron:  * * * * * ~/baitcoin-api/watchdog.sh             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
