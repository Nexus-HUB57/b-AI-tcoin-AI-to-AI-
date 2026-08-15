#!/usr/bin/env bash
# ============================================================
# live_updater.sh — Auto-update do daemon_live.py a partir do GitHub main
# Roda via cron (ver apply_golive_v5.sh): compara sha256 com o raw do main;
# se mudou: backup, py_compile e systemctl restart baitcoin-live.
# ============================================================
set -euo pipefail
APP=/home/baitcoin/app
RAW=https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/daemon_live.py
TMP=/tmp/daemon_live.next
LOG=/var/log/live_updater.log
curl -fsSL -m 20 "$RAW" -o "$TMP" 2>/dev/null || exit 0
[ -f "$APP/daemon_live.py" ] && cmp -s "$TMP" "$APP/daemon_live.py" && { rm -f "$TMP"; exit 0; }
TS=$(date +%Y%m%d-%H%M%S)
cp -a "$APP/daemon_live.py" "$APP/daemon_live.py.bak.$TS"
if python3 -m py_compile "$TMP"; then
  mv -f "$TMP" "$APP/daemon_live.py"
  systemctl restart baitcoin-live 2>/dev/null || systemctl start baitcoin-live || true
  echo "$TS: daemon_live atualizado e reiniciado" >> "$LOG"
else
  echo "$TS: compile FALHOU — mantendo versão atual" >> "$LOG"
  rm -f "$TMP"
fi
