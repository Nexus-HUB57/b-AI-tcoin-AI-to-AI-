#!/usr/bin/env bash
# ============================================================
# verify_golive.sh v3 — Validação End-to-End pública (rigorosa)
# Uso: bash verify_golive.sh [BASE_URL]   (default https://mybait.org)
# C01–C11 públicos; C12–C14 requerem acesso local/VPS (SKIP).
# v3 fix: hasE corrigido, C11 com captura robusta do código HTTP.
# ============================================================
set -u
BASE="${1:-https://mybait.org}"
API="$BASE/api/api/v1"
PASS=0; FAIL=0; SKIP=0
code(){ curl -s -m 12 -o "$2" -w '%{http_code}' "$1" 2>/dev/null || echo 000; }
has(){ grep -qE "$1" "$2" 2>/dev/null; }
row(){ printf '  %-5s %-4s %s\n' "$1" "$2" "$3"; }
echo "== verify_golive.sh v3 @ $(date -u +%Y-%m-%dT%H:%M:%SZ) | base=$BASE =="

c=$(code "$API/status" /tmp/v01.json)
if [ "$c" = 200 ] && has '"chain_valid": *true' /tmp/v01.json && has '"chain_height": *[0-9]{3,}' /tmp/v01.json; then
  PASS=$((PASS+1)); row C01 PASS "status 200 $(grep -oE '"chain_height": *[0-9]+' /tmp/v01.json)"
else FAIL=$((FAIL+1)); row C01 FAIL "status=$c"; fi

c=$(code "$API/blockchain" /tmp/v02.json)
if [ "$c" = 200 ] && has '"persistent": *true' /tmp/v02.json && has '"height": *[0-9]{3,}' /tmp/v02.json; then
  PASS=$((PASS+1)); row C02 PASS "blockchain 200 $(grep -oE '"height": *[0-9]+' /tmp/v02.json)"
else FAIL=$((FAIL+1)); row C02 FAIL "blockchain=$c"; fi

c=$(code "$API/oracle/prices" /tmp/v03.json)
if [ "$c" = 200 ] && has '"BTC": *[1-9]' /tmp/v03.json && has '"ETH": *[1-9]' /tmp/v03.json; then
  PASS=$((PASS+1)); row C03 PASS "oracle $(grep -oE '"BTC": *[0-9.]+' /tmp/v03.json)"
else FAIL=$((FAIL+1)); row C03 FAIL "oracle=$c ou nulos"; fi

c=$(code "$API/explorer/blocks?limit=2" /tmp/v04.json)
if [ "$c" = 200 ] && has '"blocks"' /tmp/v04.json; then
  PASS=$((PASS+1)); row C04 PASS "explorer/blocks 200"
else FAIL=$((FAIL+1)); row C04 FAIL "explorer/blocks=$c"; fi

c=$(code "$API/explorer/blocks/height/7081" /tmp/v05.json)
if [ "$c" = 200 ] && ! has '"blocks": *\[' /tmp/v05.json && has '"validator"' /tmp/v05.json; then
  PASS=$((PASS+1)); row C05 PASS "block/height 200 (v5.1 implantado)"
else FAIL=$((FAIL+1)); row C05 FAIL "block/height=$c (v5.1 NAO no VPS)"; fi

c=$(code "$API/block/7081" /tmp/v06.json)
if [ "$c" = 200 ] && ! has '"blocks": *\[' /tmp/v06.json && has '"validator"' /tmp/v06.json; then
  PASS=$((PASS+1)); row C06 PASS "block/7081 200 (v5.1 implantado)"
else FAIL=$((FAIL+1)); row C06 FAIL "block/7081=$c (v5.1 NAO no VPS)"; fi

c=$(code "$BASE/api/v1/moltbook/feed" /tmp/v07.json)
if [ "$c" = 200 ]; then PASS=$((PASS+1)); row C07 PASS "moltbook/feed 200"
else FAIL=$((FAIL+1)); row C07 FAIL "moltbook/feed=$c"; fi

c=$(code "$BASE/blockchain" /tmp/v08.txt)
if [ "$c" = 200 ] && has '<html' /tmp/v08.txt; then PASS=$((PASS+1)); row C08 PASS "/blockchain HTML 200"
else FAIL=$((FAIL+1)); row C08 FAIL "/blockchain=$c"; fi

LOC=$(curl -s -m 10 -o /tmp/v09.txt -w '%{http_code}|%{redirect_url}' "$BASE/aistore/" 2>/dev/null || echo '000|')
c9=${LOC%%|*}; RED=${LOC#*|}
if [ "$c9" = 200 ] && has '<html' /tmp/v09.txt; then PASS=$((PASS+1)); row C09 PASS "/aistore/ 200 sem loop"
else FAIL=$((FAIL+1)); row C09 FAIL "/aistore/ -> $c9 redirect=$RED (B2 pendente)"; fi

c=$(code "$BASE/aistore/api/stats" /tmp/v10.json)
if [ "$c" = 200 ] && has '"total"' /tmp/v10.json; then
  PASS=$((PASS+1)); row C10 PASS "aistore/stats 200 $(grep -oE '"total": *[0-9]+' /tmp/v10.json)"
else FAIL=$((FAIL+1)); row C10 FAIL "aistore/stats=$c"; fi

PAYLOAD='{"target":"all","ref":"main","sha":"verify-golive"}'
SIG=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac 'baitcoin-deploy-2024' 2>/dev/null | awk '{print $NF}')
HTTP_CODE=$(curl -s -m 20 -o /tmp/v11.txt -w '%{http_code}' -X POST "$BASE/deploy-webhook.php" \
  -H 'Content-Type: application/json' -H "X-Deploy-Signature: $SIG" -d "$PAYLOAD" 2>/dev/null || echo 000)
if [ "$HTTP_CODE" = 200 ] && has '"' /tmp/v11.txt && ! has 'Page cannot be displayed' /tmp/v11.txt && ! has '<html' /tmp/v11.txt; then
  PASS=$((PASS+1)); row C11 PASS "webhook 200 JSON (PHP ok)"
else FAIL=$((FAIL+1)); row C11 FAIL "webhook=$HTTP_CODE (PHP nao executa - B3)"; fi

SKIP=$((SKIP+3)); row C12 SKIP "disco <90%% (df -h local)"; row C13 SKIP "watchdog <=2min (systemctl)"; row C14 SKIP "SSH root (ssh -p 22022)"
echo "--------------------------------------------------------------"
echo "  RESULTADO: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
[ "$FAIL" -eq 0 ] && echo "  OK: todos os criterios publicos atendidos." || echo "  PENDENTE: $FAIL publicos - ver runbook Go-Live."
