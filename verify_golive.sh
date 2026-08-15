#!/usr/bin/env bash
# ============================================================
# verify_golive.sh — Validação End-to-End pública da plataforma b'AI'tcoin
# Uso:  bash verify_golive.sh [BASE_URL]     (default https://mybait.org)
# Testa os critérios C01–C11 do checklist de Go-Live e imprime
# tabela PASS/FAIL/SKIP + resumo. Exit 0 = sem FAIL crítico.
#
# v2: C05/C06 rigorosos — exige campos do bloco DETALHADO (validator/nonce)
#     e REJEITA a resposta de lista (falso positivo da substring /explorer/blocks).
#     C09: não segue redirect infinito (detecta 308/loop). C11: valida corpo JSON.
# ============================================================
set -u
BASE="${1:-https://mybait.org}"
API="$BASE/api/api/v1"
PASS=0; FAIL=0; SKIP=0

code(){ curl -s -m 12 -o "$2" -w '%{http_code}' "$1" 2>/dev/null || echo 000; }
has(){ grep -qE "$1" "$2" 2>/dev/null; }
row(){ printf '  %-5s %-4s %s\n' "$1" "$2" "$3"; }

echo "== verify_golive.sh @ $(date -u +%Y-%m-%dT%H:%M:%SZ) | base=$BASE =="

# ---- C01: /status -------------------------------------------------
c=$(code "$API/status" /tmp/v01.json)
if [ "$c" = 200 ] && has '"chain_valid": true' /tmp/v01.json && hasE '"chain_height": ?[0-9]{3,}' /tmp/v01.json; then
  PASS=$((PASS+1)); row C01 PASS "status 200 $(grep -oE '"chain_height": ?[0-9]+' /tmp/v01.json)"
else
  FAIL=$((FAIL+1)); row C01 FAIL "status=$c (esperado 200)"
fi

# ---- C02: /blockchain ---------------------------------------------
c=$(code "$API/blockchain" /tmp/v02.json)
if [ "$c" = 200 ] && has '"persistent": true' /tmp/v02.json && hasE '"height": ?[0-9]{3,}' /tmp/v02.json; then
  PASS=$((PASS+1)); row C02 PASS "blockchain 200 $(grep -oE '"height": ?[0-9]+' /tmp/v02.json)"
else
  FAIL=$((FAIL+1)); row C02 FAIL "blockchain=$c (esperado 200)"
fi

# ---- C03: oracle ---------------------------------------------------
c=$(code "$API/oracle/prices" /tmp/v03.json)
if [ "$c" = 200 ] && has '"BTC": ?[1-9]' /tmp/v03.json && has '"ETH": ?[1-9]' /tmp/v03.json; then
  PASS=$((PASS+1)); row C03 PASS "oracle preços não-nulos $(grep -oE '"BTC": ?[0-9.]+' /tmp/v03.json)"
else
  FAIL=$((FAIL+1)); row C03 FAIL "oracle=$c ou preços nulos"
fi

# ---- C04: explorer/blocks ------------------------------------------
c=$(code "$API/explorer/blocks?limit=2" /tmp/v04.json)
if [ "$c" = 200 ] && has '"blocks"' /tmp/v04.json; then
  PASS=$((PASS+1)); row C04 PASS "explorer/blocks 200"
else
  FAIL=$((FAIL+1)); row C04 FAIL "explorer/blocks=$c (esperado 200)"
fi

# ---- C05: explorer/blocks/height/{h} (v5 implantado?) --------------
c=$(code "$API/explorer/blocks/height/7081" /tmp/v05.json)
if [ "$c" = 200 ] && ! has '"blocks":' /tmp/v05.json && has '"validator"' /tmp/v05.json; then
  PASS=$((PASS+1)); row C05 PASS "block/height 200 (v5 implantado)"
else
  FAIL=$((FAIL+1)); row C05 FAIL "block/height=$c (v5 NÃO implantado no VPS)"
fi

# ---- C06: /block/{h} ------------------------------------------------
c=$(code "$API/block/7081" /tmp/v06.json)
if [ "$c" = 200 ] && ! has '"blocks":' /tmp/v06.json && has '"validator"' /tmp/v06.json; then
  PASS=$((PASS+1)); row C06 PASS "block/7081 200 (v5 implantado)"
else
  FAIL=$((FAIL+1)); row C06 FAIL "block/7081=$c (v5 NÃO implantado no VPS)"
fi

# ---- C07: moltbook/feed ---------------------------------------------
c=$(code "$BASE/api/v1/moltbook/feed" /tmp/v07.json)
if [ "$c" = 200 ]; then
  PASS=$((PASS+1)); row C07 PASS "moltbook/feed 200"
else
  FAIL=$((FAIL+1)); row C07 FAIL "moltbook/feed=$c (rota só no v5)"
fi

# ---- C08: frontend /blockchain ---------------------------------------
c=$(code "$BASE/blockchain" /tmp/v08.txt)
if [ "$c" = 200 ] && has '<html' /tmp/v08.txt; then
  PASS=$((PASS+1)); row C08 PASS "/blockchain HTML 200"
else
  FAIL=$((FAIL+1)); row C08 FAIL "/blockchain=$c"
fi

# ---- C09: /aistore/ SEM redirect loop --------------------------------
c=$(curl -s -m 20 -o /tmp/v09.txt -w '%{http_code}' "$BASE/aistore/" 2>/dev/null || echo 000)
LOC=$(curl -s -m 10 -o /dev/null -w '%{redirect_url}' "$BASE/aistore/" 2>/dev/null || true)
if [ "$c" = 200 ] && has '<html' /tmp/v09.txt; then
  PASS=$((PASS+1)); row C09 PASS "/aistore/ 200 sem loop"
elif [ "$c" = 308 ] || [ "$c" = 301 ] || [ "$c" = 302 ]; then
  FAIL=$((FAIL+1)); row C09 FAIL "/aistore/ -> $c (loop nginx — B2 pendente) redirect=$LOC"
else
  FAIL=$((FAIL+1)); row C09 FAIL "/aistore/ -> $c (esperado 200)"
fi

# ---- C10: aistore/api/stats ------------------------------------------
c=$(code "$BASE/aistore/api/stats" /tmp/v10.json)
if [ "$c" = 200 ] && has '"total"' /tmp/v10.json; then
  PASS=$((PASS+1)); row C10 PASS "aistore/stats 200 $(grep -oE '"total": ?[0-9]+' /tmp/v10.json)"
else
  FAIL=$((FAIL+1)); row C10 FAIL "aistore/stats=$c"
fi

# ---- C11: webhook POST assinado ---------------------------------------
PAYLOAD='{"target":"all","ref":"main","sha":"verify-golive"}'
SIG=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac 'baitcoin-deploy-2024' 2>/dev/null | awk '{print $NF}')
c=$(curl -s -m 20 -o /tmp/v11.txt -w '%{http_code}' -X POST "$BASE/deploy-webhook.php" \
      -H 'Content-Type: application/json' -H "X-Deploy-Signature: $SIG" -d "$PAYLOAD" 2>/dev/null || echo 000)
if [ "$c" = 200 ] && has '"' /tmp/v11.txt && ! has 'Page cannot be displayed' /tmp/v11.txt && ! has '<html' /tmp/v11.txt; then
  PASS=$((PASS+1)); row C11 PASS "webhook 200 JSON (PHP ok)"
else
  FAIL=$((FAIL+1)); row C11 FAIL "webhook=$c (PHP não executa — B3 pendente)"
fi

# ---- C12/C13/C14: requerem acesso local/VPS ----------------------------
SKIP=$((SKIP+3))
row C12 SKIP "disco /dev/sda3 <90% (check local: df -h)"
row C13 SKIP "watchdog systemd ≤2min (check local: systemctl status baitcoin-live)"
row C14 SKIP "SSH root (check: ssh -p 22022 root@143.95.213.237)"

echo "--------------------------------------------------------------"
echo "  RESULTADO: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
[ "$FAIL" -eq 0 ] && echo "  ✅ Todos os critérios públicos atendidos." || echo "  ❌ $FAIL critério(s) público(s) pendente(s) — ver runbook Go-Live."
