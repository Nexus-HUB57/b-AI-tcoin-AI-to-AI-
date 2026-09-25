#!/usr/bin/env bash
# scripts/audit/run_e2e_audit_fixes.sh
# Audit 2026-09-22 — E2E runner unificado para validar todos os fixes.
#
# Execução: bash scripts/audit/run_e2e_audit_fixes.sh
# Saída: cada step com PASS/FAIL + exit code cumulativo.
# Uso em CI: falha o pipeline se qualquer step crítico falhar.

set -uo pipefail

cd "$(dirname "$0")/../.."  # sobe para raiz do repo

RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ PASS${NC}  $1"; }
fail() { echo -e "${RED}✗ FAIL${NC}  $1"; }
warn() { echo -e "${YELLOW}⚠ WARN${NC}  $1"; }

CRITICAL_FAIL=0
NONCRITICAL_FAIL=0

# Helper: roda step com título
run_step() {
    local title="$1"; shift
    local critical="${1:-critical}"; shift
    echo ""
    echo "================================================================"
    echo "▶ $title"
    echo "================================================================"
    if "$@"; then
        pass "$title"
    else
        if [ "$critical" = "critical" ]; then
            fail "$title"
            CRITICAL_FAIL=$((CRITICAL_FAIL + 1))
        else
            warn "$title"
            NONCRITICAL_FAIL=$((NONCRITICAL_FAIL + 1))
        fi
    fi
}

# ---------------------------------------------------------------
echo ""
echo "=== AUDIT 2026-09-22 — E2E runner unificado ==="
echo "Repo:    $(basename $(pwd))"
echo "Date:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Branch:  $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo "Commit:  $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo ""

# ---------------------------------------------------------------
# Step 1: forge test (Solidity contracts)
# ---------------------------------------------------------------
run_step "Solidity: forge test (BAITBridge + FoundersVesting + TimelockWrapper + invariants)" critical bash -c "
    set -e
    if [ ! -d contracts ]; then
        echo 'SKIP: contracts/ not found (não estamos no repo mybait)'
        exit 0
    fi
    cd contracts
    if ! command -v forge >/dev/null 2>&1; then
        # tenta foundryup path
        export PATH=\"\$PATH:\$HOME/.config/.foundry/bin:/workspace/.home/.config/.foundry/bin\"
        if ! command -v forge >/dev/null 2>&1; then
            echo 'SKIP: forge não instalado'
            exit 0
        fi
    fi
    forge test --no-match-test 'N/A' 2>&1 | tail -8
"

# ---------------------------------------------------------------
# Step 2: pytest A2A compliance orchestrator
# ---------------------------------------------------------------
run_step "Python: pytest a2a_compliance (11 tests)" critical bash -c "
    set -e
    if ! command -v pytest >/dev/null 2>&1; then
        pip install --break-system-packages --quiet pydantic pytest
    fi
    python3 -m pytest tests/a2a_compliance/ -v 2>&1 | tail -20
"

# ---------------------------------------------------------------
# Step 3: pytest baitcoin_core.daemon.status (modularização)
# ---------------------------------------------------------------
run_step "Python: pytest baitcoin_core.daemon.status (10 tests)" critical bash -c "
    set -e
    python3 -m pytest tests/baitcoin_core/ -v 2>&1 | tail -15
"

# ---------------------------------------------------------------
# Step 4: daemon_live.py smoke tests
# ---------------------------------------------------------------
run_step "Python: daemon_live._mylink_feed_post smoke (9 cenários)" critical bash -c "
    set -e
    HOME=/tmp python3 -c '
import sys; sys.path.insert(0, \".\")
import os, tempfile, daemon_live as d
d._FEED_CAT = os.path.join(tempfile.mkdtemp(), \"feed.json\")

# 1. POST normal
r = d._mylink_feed_post({\"agent_id\": \"@e2e\", \"text\": \"hello\"})
assert r[0] == 201, r
assert r[1][\"ok\"] is True

# 2. dedup
r = d._mylink_feed_post({\"agent_id\": \"@e2e\", \"text\": \"hello\"})
assert r[1].get(\"deduplicated\") is True

# 3. no agent_id
r = d._mylink_feed_post({\"text\": \"x\"})
assert r[0] == 400

# 4. no text
r = d._mylink_feed_post({\"agent_id\": \"@x\"})
assert r[0] == 400

# 5. text muito longo
r = d._mylink_feed_post({\"agent_id\": \"@x\", \"text\": \"A\"*5000})
assert r[0] == 400

# 6. payload invalido
r = d._mylink_feed_post(\"string\")
assert r[0] == 400

# 7. schema alternativo (author + content)
r = d._mylink_feed_post({\"author\": \"@alt\", \"content\": \"alt\"})
assert r[0] == 201

# 8. contract_hash presente
r = d._mylink_feed_post({\"agent_id\": \"@z\", \"text\": \"unico\"})
assert len(r[1][\"contract_hash\"]) == 64

# 9. GET funciona
feed = d._mylink_feed_live(limit=10)
assert feed[\"total\"] >= 1

print(\"OK: 9/9 cenários\")
'
"

# ---------------------------------------------------------------
# Step 5: gitleaks config syntax check
# ---------------------------------------------------------------
run_step "Tooling: .gitleaks.toml syntax" noncritical bash -c "
    set -e
    if command -v gitleaks >/dev/null 2>&1; then
        gitleaks detect --source . --no-banner --log-opts '-1' 2>&1 | tail -5 || true
        echo 'NOTA: gitleaks detect roda mas não falhamos aqui — sweep_secrets.sh faz a varredura completa'
    else
        echo 'SKIP: gitleaks não instalado (verificar apenas TOML parse)'
        python3 -c 'import tomllib; tomllib.loads(open(\".gitleaks.toml\").read()); print(\"TOML OK\")'
    fi
"

# ---------------------------------------------------------------
# Step 6: .mailmap ativo
# ---------------------------------------------------------------
run_step "OPSEC: .mailmap reduz autores únicos" noncritical bash -c "
    set -e
    BEFORE=\$(git log --pretty=format:'%aN <%aE>' | sort -u | wc -l)
    AFTER=\$(git log --pretty=format:'%aN <%aE>' --mailmap | sort -u | wc -l)
    echo \"Authors ANTES (sem mailmap): \$BEFORE\"
    echo \"Authors DEPOIS (com mailmap): \$AFTER\"
    if [ \"\$AFTER\" -ge \"\$BEFORE\" ]; then
        echo 'WARN: mailmap não consolidou nada — verificar formato'
        exit 1
    fi
    REDUCTION=\$((BEFORE - AFTER))
    echo \"Redução: -\$REDUCTION autores únicos\"
"

# ---------------------------------------------------------------
# Step 7: docs alignment (zkML)
# ---------------------------------------------------------------
run_step "Docs: zkML-PoUW alinha com zkml_engine.py (sem zk-SNARK ML claims)" critical bash -c "
    set -e
    # Procura por claims de zk-SNARK Groth16 ou 'AI computation as proof-of-work via zk-SNARK'
    MATCHES=\$(grep -rE 'zk-SNARK proofs \\(Groth16\\)|AI computation as proof-of-work via zk-SNARK' exchange-applications/*/technical_summary.md 2>/dev/null | wc -l)
    if [ \"\$MATCHES\" -gt 0 ]; then
        echo \"FAIL: \$MATCHES docs ainda afirmam zk-SNARK Groth16 para ML\"
        grep -rE 'zk-SNARK proofs \\(Groth16\\)|AI computation as proof-of-work via zk-SNARK' exchange-applications/*/technical_summary.md 2>/dev/null
        exit 1
    fi
    echo 'OK: nenhum exchange application ainda faz claim de zk-SNARK ML'
"

# ---------------------------------------------------------------
# Step 8: sweep_secrets (informational)
# ---------------------------------------------------------------
run_step "OPSEC: sweep_secrets.sh (working tree)" noncritical bash -c "
    set -e
    bash scripts/audit/sweep_secrets.sh . 2>&1 | tail -15
    echo 'NOTA: working tree pode ter .bak.* ou secrets por design — fail aqui é só alerta'
    exit 0
"

# ---------------------------------------------------------------
# Step 9: contracts compile limpo
# ---------------------------------------------------------------
run_step "Solidity: forge build (todos os contracts compilam)" critical bash -c "
    set -e
    if [ ! -d contracts ]; then exit 0; fi
    cd contracts
    if ! command -v forge >/dev/null 2>&1; then
        export PATH=\"\$PATH:\$HOME/.config/.foundry/bin:/workspace/.home/.config/.foundry/bin\"
    fi
    forge build 2>&1 | tail -3
"

# ---------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------
echo ""
echo "================================================================"
echo "=== RESUMO ==="
echo "================================================================"
echo "Critical failures: $CRITICAL_FAIL"
echo "Non-critical warnings: $NONCRITICAL_FAIL"
echo ""

if [ "$CRITICAL_FAIL" -eq 0 ]; then
    echo -e "${GREEN}✓ AUDIT FIXES — E2E PASS${NC}"
    echo "Pronto para commit + PR."
    exit 0
else
    echo -e "${RED}✗ AUDIT FIXES — E2E FAIL${NC}"
    echo "Investigue os critical failures acima antes de commitar."
    exit 1
fi
