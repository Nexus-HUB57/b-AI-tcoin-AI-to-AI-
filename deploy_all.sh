#!/usr/bin/env bash
# ============================================================
# deploy_all.sh — GO-LIVE COMPLETO b'AI'tcoin (frontend + backend + verify)
# Idempotente. Uso (como root no VPS):
#   curl -fsSL https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/deploy_all.sh | bash
#
# Etapas:
#   [1] Frontend: baixa netlify/* para TODOS os docroots encontrados
#       (/var/www/mybait e/ou public_html sob /home) — idempotente
#   [2] Backend: apply_golive_v5.sh --full-backup (v5.1 + nginx + WAL + crons)
#   [3] PHP-FPM: restart (webhook/C11)
#   [4] live_updater v2 (pull-based: daemon+frontend a cada 15min)
#   [5] Verify: verify_golive.sh contra https://mybait.org
# ============================================================
set -euo pipefail
RAW='https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main'
TS=$(date +%Y%m%d-%H%M%S)
echo "===== deploy_all @ $(date -u +%FT%TZ) ====="

# ---- [1/5] Frontend ----
echo "--- [1/5] Frontend ---"
DOCROOTS=()
[ -d /var/www/mybait ] && DOCROOTS+=(/var/www/mybait)
while IFS= read -r d; do DOCROOTS+=("$d"); done < <(find /home -maxdepth 3 -name public_html -type d 2>/dev/null)
if [ "${#DOCROOTS[@]}" -eq 0 ]; then
  echo "  ERRO: nenhum docroot encontrado. Localize: find / -maxdepth 4 -name 'blockchain.html' 2>/dev/null"
else
  for PUB in "${DOCROOTS[@]}"; do
    echo "  Docroot: $PUB"
    for f in index.html blockchain.html bainkr.html faucet.html sdk.html obscura.html favicon.svg api.cgi .htaccess; do
      curl -fsSL -m 20 "$RAW/netlify/$f" -o "$PUB/$f" && echo "    OK $f" || echo "    WARN $f"
    done
    chmod 0755 "$PUB/api.cgi" 2>/dev/null || true
  done
fi

# ---- [2/5] Backend v5.1 ----
echo "--- [2/5] Backend (apply_golive_v5 --full-backup) ---"
curl -fsSL -m 30 "$RAW/apply_golive_v5.sh" -o /tmp/apply_golive_v5.sh
bash /tmp/apply_golive_v5.sh --full-backup

# ---- [3/5] PHP-FPM ----
echo "--- [3/5] PHP-FPM ---"
systemctl restart php-fpm 2>/dev/null || systemctl restart php8.1-fpm 2>/dev/null || echo "  PHP restart skip"

# ---- [4/5] live_updater v2 (pull-based) ----
echo "--- [4/5] live_updater v2 ---"
curl -fsSL -m 20 "$RAW/live_updater.sh" -o /usr/local/sbin/live_updater.sh
chmod +x /usr/local/sbin/live_updater.sh
( crontab -l 2>/dev/null | grep -v 'live_updater' || true
  echo "*/15 * * * * /usr/local/sbin/live_updater.sh >> /var/log/live_updater.log 2>&1"
) | crontab -
echo "  cron instalado (*/15)"

# ---- [5/5] Verify ----
echo "--- [5/5] Verificacao publica ---"
curl -fsSL -m 30 "$RAW/verify_golive.sh" -o /tmp/verify_golive.sh
bash /tmp/verify_golive.sh https://mybait.org
echo "===== FIM deploy_all ====="
