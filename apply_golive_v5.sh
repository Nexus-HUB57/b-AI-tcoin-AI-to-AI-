#!/usr/bin/env bash
# ============================================================
# apply_golive_v5.sh — Aplica o Go-Live v5 no VPS (IDEMPOTENTE)
# Executar COMO ROOT no VPS (console/VNC ou SSH):
#     bash /path/to/apply_golive_v5.sh [--full-backup]
#
# Etapas:
#   [1/5] Deploy do daemon_live.py v5 (download raw GitHub + sha256 + compile + restart)
#   [2/5] nginx: remove .corrompido, corrige location /aistore/ (try_files), nginx -t + reload
#   [3/5] Disco: quarentena de WAL >500MB (mover p/ .archive — NUNCA apagar imediato)
#   [4/5] Instala live_updater.sh (auto-update 15min) + rotate_wal.sh (semanal)
#   [5/5] Verificação local (block/7081 + status) e df -h
#
# Não destrutivo: backups com sufixo .bak.<ts> antes de cada alteração;
# nginx -t falhou => restaura backup e não aplica.
# ============================================================
set -euo pipefail
TS=$(date +%Y%m%d-%H%M%S)
APP=/home/baitcoin/app
RAW=https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/daemon_live.py
EXPECTED_SHA="ee0febb5e14b3104e7d6af6e51b39d166a15da9bbb51f1b0be28f8208495d61d"
MEM=/home/baitcoin/.baitcoin/memory
LOG=/tmp/golive-apply-$TS.log
exec > >(tee -a "$LOG") 2>&1
echo "== Go-Live v5 apply @ $TS (host: $(hostname)) =="

# ---- [1/5] daemon_live v5 -------------------------------------------
echo "--- [1/5] daemon_live v5 ---"
mkdir -p "$APP"
if [ -f "$APP/daemon_live.py" ]; then cp -a "$APP/daemon_live.py" "$APP/daemon_live.py.bak.$TS"; fi
curl -fsSL -m 30 "$RAW" -o "$APP/daemon_live.py.new"
echo "$EXPECTED_SHA  $APP/daemon_live.py.new" | sha256sum -c - || { echo "FALHA: sha256 não confere — deploy abortado"; exit 3; }
python3 -m py_compile "$APP/daemon_live.py.new"
mv -f "$APP/daemon_live.py.new" "$APP/daemon_live.py"
systemctl restart baitcoin-live 2>/dev/null || { systemctl start baitcoin-live || true; }
sleep 6
echo "local block/7081 -> $(curl -s -m 5 http://127.0.0.1:18445/api/v1/block/7081 | head -c 160)"
echo "daemon_live v5 instalado (sha256 OK)"

# ---- [2/5] nginx ------------------------------------------------------
echo "--- [2/5] nginx ---"
NG=/etc/nginx/sites-enabled/mybait.org.conf
if [ -f "$NG" ]; then cp -a "$NG" "$NG.bak.$TS"; fi
find /etc/nginx/sites-enabled/ -name '*corrompido*' -maxdepth 1 -exec rm -v {} \;
python3 - "$NG" <<'PY'
import re, pathlib, sys
p = pathlib.Path(sys.argv[1])
if not p.exists():
    print('AVISO: CONF AUSENTE — criar /etc/nginx/sites-enabled/mybait.org.conf a partir da referência (runbook B2)')
    raise SystemExit(0)
s = p.read_text()
needle = 'location /aistore/'
fix = 'try_files $uri $uri/ /aistore/index.html;'
if needle in s and fix not in s:
    m = re.search(re.escape(needle) + r'\s*\{', s)
    if m:
        s = s[:m.end()] + '\n        ' + fix + '\n' + s[m.end():]
        p.write_text(s)
        print('nginx: try_files inserido em /aistore/')
    else:
        print('AVISO: local /aistore/ sem chave detectável')
else:
    print('nginx: /aistore/ já ok ou bloco ausente')
PY
if nginx -t 2>/tmp/ng.err; then
  systemctl reload nginx && echo "NGINX_RELOAD_OK"
else
  echo "NGINX_TEST_FAIL — restaurando backup e revalidando"
  [ -f "$NG.bak.$TS" ] && cp -a "$NG.bak.$TS" "$NG"
  nginx -t 2>/dev/null && systemctl reload nginx
  cat /tmp/ng.err
fi

# ---- [3/5] disco -------------------------------------------------------
echo "--- [3/5] disco (quarentena WAL) ---"
if [ "${1:-}" = "--full-backup" ]; then
  FREE=$(df -Pk /home/baitcoin | awk 'NR==2{print $4}')
  if [ "$FREE" -gt 15000000 ]; then
    mkdir -p "$APP/backups"
    tar czf "$APP/backups/memory-$TS.tar.gz" -C "$(dirname "$MEM")" "$(basename "$MEM")" 2>/dev/null && echo "backup memory OK"
  else
    echo "AVISO: espaço insuficiente p/ backup completo (${FREE}KB). Sem tar."
  fi
fi
df -h /home/baitcoin | tee /tmp/df.before.$TS
WAL="$MEM/blockchain/wal"
mkdir -p "$WAL/.archive"
find "$WAL" -maxdepth 1 -name '*.log' -size +500M -mmin +60 -exec mv -v {} "$WAL/.archive/" \;
df -h /home/baitcoin | tee /tmp/df.after.$TS

# ---- [4/5] auto-update + rotação --------------------------------------
echo "--- [4/5] scripts auxiliares + crons ---"
for f in live_updater.sh rotate_wal.sh; do
  curl -fsSL -m 20 "https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/$f" -o "/usr/local/sbin/$f"
done
chmod +x /usr/local/sbin/live_updater.sh /usr/local/sbin/rotate_wal.sh
( crontab -l 2>/dev/null | grep -vE 'live_updater|rotate_wal' || true
  echo "*/15 * * * * /usr/local/sbin/live_updater.sh >> /var/log/live_updater.log 2>&1"
  echo "30 4 * * 0  /usr/local/sbin/rotate_wal.sh  >> /var/log/rotate_wal.log 2>&1"
) | crontab -
echo "crons instalados (updater */15, rotate semanal)"

# ---- [5/5] verificação --------------------------------------------------
echo "--- [5/5] verificação local ---"
curl -s -m 5 http://127.0.0.1:18445/api/v1/status | head -c 220; echo
curl -s -m 5 -o /dev/null -w "aistore -> %{http_code}\n" http://127.0.0.1/aistore/ || true
echo "FIM (log completo: $LOG)"
