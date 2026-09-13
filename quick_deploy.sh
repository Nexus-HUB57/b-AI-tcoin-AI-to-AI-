#!/usr/bin/env bash
# b'AI'tcoin Quick Deploy — run as root on VPS
# Usage: bash <(curl -sL https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/quick_deploy.sh)
set -euo pipefail
RAW='https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/netlify'
PUB=$(find /home -maxdepth 3 -name public_html -type d 2>/dev/null | head -1)
[ -z "$PUB" ] && { echo 'ERRO: public_html nao encontrado'; exit 1; }
echo "[1/4] Public HTML: $PUB"

# 2. Download files
echo '[2/4] Baixando arquivos...'
for f in index.html blockchain.html bainkr.html faucet.html sdk.html obscura.html favicon.svg api.cgi .htaccess; do
  echo "  $f..."
  curl -fsSL -m 20 "$RAW/$f" -o "$PUB/$f" || echo "  WARN: falhou $f"
done

# 3. Permissions
echo '[3/4] Permissoes...'
chmod 0755 "$PUB/api.cgi" 2>/dev/null || true

# 4. Fix PHP-FPM if needed
echo '[4/4] PHP-FPM check...'
if command -v php-fpm &>/dev/null; then
  php-fpm -t 2>/dev/null && systemctl restart php*-fpm 2>/dev/null && echo '  PHP-FPM restarted' || echo '  PHP-FPM skip'
elif command -v systemctl &>/dev/null; then
  systemctl restart php-fpm 2>/dev/null || systemctl restart php8.1-fpm 2>/dev/null || echo '  PHP restart skip'
fi

# Verify
echo ''
echo '=== Verificacao ==='
curl -s -m 5 http://127.0.0.1:18445/api/v1/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Daemon: chain_height={d.get(\"chain_height\")}, valid={d.get(\"chain_valid\")}')" 2>/dev/null || echo '  Daemon: N/A'
DIFF=$(diff <(curl -s "$RAW/api.cgi" | md5sum) <(md5sum "$PUB/api.cgi" 2>/dev/null || echo 'miss') | head -1)
[ -z "$DIFF" ] && echo '  api.cgi: UPDATED' || echo '  api.cgi: verify manual'
DIFF2=$(diff <(curl -s "$RAW/index.html" | md5sum) <(md5sum "$PUB/index.html" 2>/dev/null || echo 'miss') | head -1)
[ -z "$DIFF2" ] && echo '  index.html: UPDATED' || echo '  index.html: verify manual'
echo ''
echo 'Deploy concluido. Acesse https://www.mybait.org'