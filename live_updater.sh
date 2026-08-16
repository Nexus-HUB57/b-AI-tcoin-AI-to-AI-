#!/usr/bin/env bash
# ============================================================
# live_updater.sh v2 — PULL-BASED auto-deploy b'AI'tcoin
# (daemon + frontend) — roda via cron a cada 15 min.
# Se algo mudou no main do GitHub, aplica automaticamente.
# Instalado por deploy_all.sh. Nao toca nginx (fixado por apply_golive_v5.sh).
# ============================================================
set -euo pipefail
RAW='https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main'
APP=/home/baitcoin/app
LOG=/var/log/live_updater.log
TS=$(date +%Y%m%d-%H%M%S)

# ---- 1. Daemon ----
TMP=/tmp/daemon_live.next
if curl -fsSL -m 20 "$RAW/daemon_live.py" -o "$TMP" 2>/dev/null; then
  if [ -f "$APP/daemon_live.py" ] && cmp -s "$TMP" "$APP/daemon_live.py"; then
    rm -f "$TMP"
  else
    cp -a "$APP/daemon_live.py" "$APP/daemon_live.py.bak.$TS" 2>/dev/null || true
    if python3 -m py_compile "$TMP"; then
      mv -f "$TMP" "$APP/daemon_live.py"
      systemctl restart baitcoin-live 2>/dev/null || systemctl start baitcoin-live || true
      echo "$TS: daemon_live atualizado" >> "$LOG"
    else
      echo "$TS: daemon compile FALHOU" >> "$LOG"; rm -f "$TMP"
    fi
  fi
fi

# ---- 2. Frontend ----
DOCROOTS=()
[ -d /var/www/mybait ] && DOCROOTS+=(/var/www/mybait)
while IFS= read -r d; do DOCROOTS+=("$d"); done < <(find /home -maxdepth 3 -name public_html -type d 2>/dev/null)
for PUB in "${DOCROOTS[@]}"; do
  for f in index.html blockchain.html bainkr.html faucet.html sdk.html obscura.html favicon.svg api.cgi .htaccess; do
    curl -fsSL -m 20 "$RAW/netlify/$f" -o "$PUB/$f.new" 2>/dev/null || continue
    if ! cmp -s "$PUB/$f.new" "$PUB/$f" 2>/dev/null; then
      mv -f "$PUB/$f.new" "$PUB/$f"
      echo "$TS: frontend $f ($PUB) atualizado" >> "$LOG"
    else
      rm -f "$PUB/$f.new"
    fi
  done
  chmod 0755 "$PUB/api.cgi" 2>/dev/null || true
done

echo "$TS: updater v2 ok" >> "$LOG"
