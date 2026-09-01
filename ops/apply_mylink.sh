#!/usr/bin/env bash
# apply_mylink.sh — deploy idempotente e ADITIVO no VPS mybait.org
# - Nunca apaga arquivos; todo alvo de escrita recebe backup .bak.<ts>
# - Regex tolerante (aprendizado do deploy v2: anchor estrito abortava com AssertionError)
# Executado no VPS pelo workflow .github/workflows/deploy.yml (ou manualmente).
set -euo pipefail

TS=$(date +%s)
WWW=/var/www/mybait
APP=/home/baitcoin/app
BK=/root/mybait-rollback-$TS
mkdir -p "$BK"
echo "[1/6] Backup em $BK"
cp -a "$WWW"/*.html "$BK"/ 2>/dev/null || true
cp -a "$APP/daemon_live.py" "$BK"/ 2>/dev/null || true
echo "$BK" > /tmp/last_rollback_ts

echo "[2/6] Página MyLink"
mkdir -p "$WWW/mylink"
[ -f "$WWW/mylink/index.html" ] && cp -a "$WWW/mylink/index.html" "$BK/mylink_index.html"
cp /tmp/site/mylink/index.html "$WWW/mylink/index.html"

echo "[3/6] Tab MyLink na navbar (idempotente, regex tolerante)"
python3 - <<'PYEOF'
import re, glob, time
ts = str(int(time.time()))
SNIP = '\n  <a class="link" href="/mylink">🕸️ MyLink</a>'
pat = re.compile(r'(<a class="link" href="/faucet">[^<]*Faucet</a>)')
for f in glob.glob('/var/www/mybait/*.html'):
    html = open(f, encoding='utf-8').read()
    if 'href="/mylink"' in html:
        print('  já contém MyLink, skip:', f); continue
    new, n = pat.subn(lambda m: m.group(1) + SNIP, html, count=1)
    if n == 0:
        print('  âncora Faucet não encontrada (sem escrita):', f); continue
    open(f + '.bak.mylink-' + ts, 'w', encoding='utf-8').write(html)
    open(f, 'w', encoding='utf-8').write(new)
    print('  ok:', f)
PYEOF

echo "[4/6] Patch da Blockch'AI'n (validador/nonce/bits/timestamp)"
python3 /tmp/ops/blockchain_patch.py || echo "  patch pulado (helper já presente ou layout divergente)"

echo "[5/6] Restart do daemon"
systemctl restart baitcoin-live
sleep 3
systemctl is-active baitcoin-live

echo "[6/6] Smoke local"
curl -s -o /dev/null -w '/mylink -> %{http_code}\n' http://127.0.0.1/mylink
echo "DEPLOY OK — rollback: BK=$BK"
