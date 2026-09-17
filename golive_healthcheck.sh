#!/usr/bin/env bash
# ============================================================
# golive_healthcheck.sh — Monitoramento contínuo do Go-Live b'AI'tcoin
# (SUBSTITUTO MANUAL do workflow de plataforma, que falhou no servidor)
# Roda verify_golive.sh contra https://mybait.org a cada INTERVALO segundos
# e registra cada execução com timestamp em /var/log/golive_healthcheck.log
#
# Instalação (1 comando, no servidor OU numa máquina com internet):
#   nohup bash golive_healthcheck.sh > /dev/null 2>&1 &
# Ou como cron (a cada hora):
#   0 * * * * bash /caminho/golive_healthcheck.sh --once >> /var/log/golive_healthcheck.log 2>&1
# ============================================================
set -u
INTERVAL="${GOLIVE_INTERVAL:-3600}"          # padrão: 1 hora
BASE="${GOLIVE_BASE:-https://mybait.org}"
VERIFY_URL="https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/verify_golive.sh"
LOG="/var/log/golive_healthcheck.log"
WORKDIR="${TMPDIR:-/tmp}"
[ -w "$(dirname "$LOG")" ] || LOG="$HOME/golive_healthcheck.log"

fetch_verify() {
    curl -fsSL -m 30 "$VERIFY_URL" -o "$WORKDIR/verify_golive.sh" 2>/dev/null \
      || { echo "$(date -u +%FT%TZ) ERRO: nao consegui baixar verify_golive.sh" >> "$LOG"; return 1; }
    chmod +x "$WORKDIR/verify_golive.sh"
}

run_once() {
    fetch_verify || return 1
    echo "===== $(date -u +%FT%TZ) =====" >> "$LOG"
    bash "$WORKDIR/verify_golive.sh" "$BASE" >> "$LOG" 2>&1 || true
    echo "" >> "$LOG"
}

# Modo --once: executa uma única verificação (para cron/manual)
if [ "${1:-}" = "--once" ]; then
    run_once
    exit 0
fi

# Modo loop (nohup): verificação contínua a cada INTERVAL segundos
echo "$(date -u +%FT%TZ) golive_healthcheck iniciado (intervalo=${INTERVAL}s, base=${BASE})" >> "$LOG"
run_once
while true; do
    sleep "$INTERVAL"
    run_once
done
