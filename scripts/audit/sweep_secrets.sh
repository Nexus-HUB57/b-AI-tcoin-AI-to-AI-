#!/usr/bin/env bash
# scripts/audit/sweep_secrets.sh
# Audit 2026-09-22 — P0 item 2 (Sweep de Ativos & Rotação):
#   Varredura de credenciais expostas no histórico + working tree.
#
# Uso:  bash scripts/audit/sweep_secrets.sh [TARGET_DIR]
# Saída: relatório em stdout + exit code 1 se encontrar algo crítico.

set -uo pipefail

TARGET="${1:-.}"
SEVERITY="CRITICAL"
FAIL=0

red() { printf '\033[31m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }

echo "=== BAIT/MyBait Secret Sweep ==="
echo "Target: $TARGET"
echo "Date:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# 1. Arquivos .bak.* (117 conhecidos — devem ser apagados do histórico)
echo "[1/6] Buscando .bak.* files..."
BAK_COUNT=$(find "$TARGET" -type f -name "*.bak.*" 2>/dev/null | wc -l)
if [ "$BAK_COUNT" -gt 0 ]; then
  red "  CRITICAL: $BAK_COUNT .bak.* files encontrados (devem ser apagados do histórico via git filter-repo)"
  find "$TARGET" -type f -name "*.bak.*" 2>/dev/null | head -5 | sed 's/^/    /'
  FAIL=1
else
  green "  OK: nenhum .bak.* file"
fi
echo ""

# 2. Keystores em deploy/
echo "[2/6] Buscando keystores em deploy/..."
KEYSTORE_COUNT=$(find "$TARGET/deploy" -type f \( -name "*.json" -o -name "*.txt" -o -name "*.key" \) 2>/dev/null | wc -l)
if [ "$KEYSTORE_COUNT" -gt 0 ]; then
  red "  CRITICAL: $KEYSTORE_COUNT keystores em deploy/ (rotacionar imediatamente)"
  find "$TARGET/deploy" -type f \( -name "*.json" -o -name "*.txt" -o -name "*.key" \) 2>/dev/null | head -5 | sed 's/^/    /'
  FAIL=1
else
  green "  OK: nenhum keystore em deploy/"
fi
echo ""

# 3. Senhas específicas (Benjamin2020*1981$ do audit)
echo "[3/6] Buscando senha mestra documentada (Benjamin2020*1981\$)..."
MASTER_PASSWORD_HITS=$(grep -r "Benjamin2020" "$TARGET" 2>/dev/null | grep -v ".git/" | wc -l)
if [ "$MASTER_PASSWORD_HITS" -gt 0 ]; then
  red "  CRITICAL: $MASTER_PASSWORD_HITS ocorrências da senha mestra (rotate ALL credentials!)"
  grep -r "Benjamin2020" "$TARGET" 2>/dev/null | grep -v ".git/" | head -3 | sed 's/^/    /'
  FAIL=1
else
  green "  OK: senha mestra não encontrada"
fi
echo ""

# 4. Chaves privadas em código (regex)
echo "[4/6] Buscando padrões de chave privada (0x + 64 hex)..."
PRIVKEY_HITS=$(grep -rE "0x[0-9a-fA-F]{64}" "$TARGET" --include="*.py" --include="*.sol" --include="*.js" --include="*.ts" --include="*.sh" --include="*.env" 2>/dev/null | grep -v ".git/" | grep -v test_ | wc -l)
if [ "$PRIVKEY_HITS" -gt 0 ]; then
  yellow "  HIGH: $PRIVKEY_HITS padrões 0x+64hex em código (revisar — podem ser chaves reais)"
  grep -rE "0x[0-9a-fA-F]{64}" "$TARGET" --include="*.py" --include="*.sol" --include="*.js" --include="*.ts" --include="*.sh" --include="*.env" 2>/dev/null | grep -v ".git/" | grep -v test_ | head -3 | sed 's/^/    /'
else
  green "  OK: nenhum padrão 0x+64hex em código"
fi
echo ""

# 5. reference_blockchain_com.json (208KB scrape do Blockchain.com com tags GA/Ads)
echo "[5/6] Buscando reference_blockchain_com.json (scrape de terceiro)..."
if [ -f "$TARGET/reference_blockchain_com.json" ]; then
  red "  CRITICAL: reference_blockchain_com.json presente (remover do histórico!)"
  FAIL=1
else
  green "  OK: não encontrado"
fi
echo ""

# 6. Alchemy/Infura/QuickNode tokens
echo "[6/6] Buscando tokens de RPC providers..."
RPC_HITS=$(grep -rE "https?://[a-z0-9.-]+\.(alchemy|infura|quicknode|ankr\.com)/v2/[a-zA-Z0-9_-]{20,}" "$TARGET" --include="*.py" --include="*.env" --include="*.json" --include="*.ts" --include="*.js" 2>/dev/null | grep -v ".git/" | wc -l)
if [ "$RPC_HITS" -gt 0 ]; then
  yellow "  HIGH: $RPC_HITS URLs com tokens de RPC (mover para GitHub Secrets)"
  grep -rE "https?://[a-z0-9.-]+\.(alchemy|infura|quicknode|ankr\.com)/v2/[a-zA-Z0-9_-]{20,}" "$TARGET" --include="*.py" --include="*.env" --include="*.json" --include="*.ts" --include="*.js" 2>/dev/null | grep -v ".git/" | head -3 | sed 's/^/    /'
else
  green "  OK: nenhuma URL tokenizada"
fi
echo ""

echo "=== RESULTADO ==="
if [ "$FAIL" -eq 1 ]; then
  red "  Status: $SEVERITY — sweep encontrou items que precisam de ação imediata"
  echo "  Próximos passos:"
  echo "    1. Rotacionar todas as credenciais afetadas (cold storage)"
  echo "    2. git filter-repo --invert-paths (apaga .bak.*, keystores, etc.)"
  echo "    3. Mover tokens p/ GitHub Actions Secrets"
  echo "    4. Re-rodar este sweep até retornar 0"
  exit 1
else
  green "  Status: CLEAN — nenhum item crítico encontrado no working tree"
  echo "  ATENÇÃO: working tree limpo NÃO garante histórico limpo. Rode:"
  echo "    gitleaks detect --no-banner --source . --verbose"
  echo "    trufflehog git file://. --since-commit HEAD~100"
  exit 0
fi
