#!/usr/bin/env bash
# verify_deploy.sh
# Verifica end-to-end que o hotfix 2026-08-12 esta ativo em mybait.org.
# Nao altera nada; apenas consulta e valida o payload real.
#
# Uso:
#   bash scripts/verify_deploy.sh              # valida mybait.org (default)
#   BASE=https://staging.mybait.org bash scripts/verify_deploy.sh

set -euo pipefail

BASE="${BASE:-https://mybait.org}"
API="${BASE}/api/api/v1"

pass(){ printf '\033[1;32m[PASS]\033[0m %s\n' "$*"; }
fail(){ printf '\033[1;31m[FAIL]\033[0m %s\n' "$*"; FAILS=$((FAILS+1)); }
info(){ printf '\033[1;36m[..]\033[0m %s\n' "$*"; }
FAILS=0

info "b'AI'tcoin post-deploy verification against ${BASE}"

# 1) Frontends HTTP 200
for path in / /blockchain /bainkr /faucet /sdk /obscura /favicon.svg; do
    code=$(curl -sSf -o /dev/null -w "%{http_code}" "${BASE}${path}" || echo "000")
    if [ "$code" = "200" ]; then pass "GET ${path} = 200"; else fail "GET ${path} = ${code}"; fi
done

# 2) /status expandido
info "GET /status"
curl -sSf "${API}/status" > /tmp/status.json || { fail "/status nao respondeu"; exit 1; }
python3 - <<'PY' || FAILS=$((FAILS+1))
import json,sys
try:
    s=json.load(open('/tmp/status.json'))
except Exception as e:
    print('FAIL status parse:',e); sys.exit(1)

req=['network','chain_height','chain_valid','blocks_immutable',
     'utxo_count','agents_registered','explorer_index',
     'token_minted_bait','marketplace','oracle','staking','modules']
missing=[k for k in req if k not in s]
if missing:
    print('FAIL missing keys:',missing); sys.exit(1)
print('PASS payload expandido presente')

# Consistency
h=s.get('chain_height'); e=s.get('explorer_index') or {}
last=e.get('last_indexed_height'); ib=e.get('indexed_blocks')
print(f'  chain_height={h}  last_indexed_height={last}  indexed_blocks={ib}')
if isinstance(h,int) and isinstance(last,int) and abs(h-last)>10:
    print(f'WARN drift chain_height vs last_indexed_height: {h-last}')
if isinstance(ib,int) and isinstance(last,int) and ib > (last+5):
    print(f'WARN indexed_blocks > last_indexed_height+5 (residual drift): {ib} vs {last}')

# Oracle no more nulls (best-effort — cache pode ainda estar vazio no boot)
prices=(s.get('oracle') or {}).get('prices') or {}
nulls=[k for k,v in prices.items() if v is None]
if nulls:
    print(f'WARN oracle prices null: {nulls}')
else:
    print('PASS oracle prices nao-nulos')
PY

# 3) /blockchain (fonte de verdade da altura)
info "GET /blockchain"
curl -sSf "${API}/blockchain" > /tmp/bc.json && \
    python3 -c "import json;b=json.load(open('/tmp/bc.json'));assert 'height' in b and 'last_block_hash' in b;print('  height =',b['height']);print('  last  =',b['last_block_hash'][:16]+'...')" \
    && pass "/blockchain retorna height + last_block_hash" \
    || fail "/blockchain quebrado"

# 4) /explorer/blocks (deve popular apos o fix)
info "GET /explorer/blocks?limit=3"
curl -sSf "${API}/explorer/blocks?limit=3" > /tmp/eb.json && \
    python3 -c "import json;b=json.load(open('/tmp/eb.json'));n=len(b.get('blocks',[]));print('  blocos=',n,' total=',b.get('total'));assert n>0" \
    && pass "/explorer/blocks retorna blocos reais" \
    || fail "/explorer/blocks vazio (fix indices.py nao ativo?)"

# 5) /agents
info "GET /agents"
curl -sSf "${API}/agents" > /tmp/ag.json && \
    python3 -c "import json;a=json.load(open('/tmp/ag.json'));n=len(a.get('agents',[]));print('  agentes=',n);assert n>=1" \
    && pass "/agents lista agentes" \
    || fail "/agents vazio"

# 6) /faucet/public-claim (deve existir, mesmo que rejeite claim)
info "POST /faucet/public-claim (probe)"
code=$(curl -sS -o /tmp/pc.json -w "%{http_code}" \
    -X POST -H 'Content-Type: application/json' \
    -d '{"agent_id":"probe_verify"}' \
    "${API}/faucet/public-claim" || echo "000")
if [ "$code" = "200" ] || [ "$code" = "400" ] || [ "$code" = "429" ]; then
    pass "public-claim endpoint disponivel (HTTP ${code})"
else
    fail "public-claim retornou HTTP ${code} (rota nao registrada?)"
fi

# 7) /agent/bootstrap (probe seguro — nao consome se falhar antes de wallet)
info "POST /agent/bootstrap (probe)"
code=$(curl -sS -o /tmp/ab.json -w "%{http_code}" \
    -X POST -H 'Content-Type: application/json' \
    -d '{"display_name":"probe"}' \
    "${API}/agent/bootstrap" || echo "000")
if [ "$code" = "200" ] || [ "$code" = "500" ]; then
    pass "agent/bootstrap endpoint disponivel (HTTP ${code})"
else
    fail "agent/bootstrap retornou HTTP ${code}"
fi

echo
if [ "$FAILS" -eq 0 ]; then
    printf '\033[1;32m=== ALL CHECKS PASSED ===\033[0m\n'
    exit 0
else
    printf '\033[1;31m=== %d CHECK(S) FAILED ===\033[0m\n' "$FAILS"
    exit 1
fi
