#!/usr/bin/env bash
# ============================================================================
# b'AI'tcoin — rotação/purga SEGURA de backups e snapshots antigos em .baitcoin
#
# Medição real (2026-08-18): /home/baitcoin/.baitcoin = 54 GB, sendo:
#   - backups/memory.*            = 43 GB (snapshots automáticos 10-15/08)
#   - memory.bak.20260809-205807  = 12 GB (cópia antiga inteira)
#   - memory/ (cadeia viva)        = 26 MB  -> NUNCA é tocado
#   - wal/                         = 3,2 MB -> NUNCA é tocado
#
# Uso:
#   bash baitcoin_prune.sh            # DRY-RUN (padrão, nada é apagado)
#   DRY_RUN=0 bash baitcoin_prune.sh  # executa a purga
#   cron/systemd: DRY_RUN=0 (unit baitcoin-prune.service + .timer semanais)
# ============================================================================
set -euo pipefail

BAIT_HOME="/home/baitcoin/.baitcoin"   # caminho real do daemon (User=baitcoin, HOME=/home/baitcoin)
KEEP_NEWEST_BACKUPS=2                  # quantos backups/memory.* manter
LOG_RETENTION_DAYS=30                  # *.log antigos fora do WAL (0 = desliga)
DRY_RUN="${DRY_RUN:-1}"

TS="$(date -u +%Y%m%d-%H%M%S)"
LOG="/var/log/baitcoin_prune.log"
START_BYTES=0; END_BYTES=0

log(){ printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"; }

# ---- Salvaguarda 1: o script só opera neste caminho absoluto ----
REAL_HOME="$(readlink -f "$BAIT_HOME" 2>/dev/null || echo "$BAIT_HOME")"
case "$REAL_HOME" in
  /home/baitcoin/.baitcoin) : ;;
  *) log "ABORT: caminho inesperado ($REAL_HOME). Nada foi feito."; exit 1 ;;
esac
[ -d "$REAL_HOME" ] || { log "ABORT: $REAL_HOME nao existe."; exit 1; }

# ---- Salvaguarda 2: cadeia viva precisa existir (nunca purgar sem ela) ----
[ -d "$REAL_HOME/memory/blockchain" ] || { log "ABORT: cadeia viva ausente ($REAL_HOME/memory/blockchain). Nada foi feito."; exit 1; }

purge(){
  # purge <path> <descricao>  -> remove (ou registra em dry-run)
  local path="$1" desc="$2" sz
  sz="$(du -sb "$path" 2>/dev/null | awk '{print $1}')"; sz="${sz:-0}"
  if [ "$DRY_RUN" = "1" ]; then
    log "DRY  : [$(( sz / 1024 / 1024 )) MB] $desc $path  (seria removido)"
  else
    log "EXEC : [$(( sz / 1024 / 1024 )) MB] $desc $path"
    rm -rf -- "$path"
  fi
}

calc_bytes(){ du -sb "$1" 2>/dev/null | awk '{print $1}'; }

START_BYTES="$(calc_bytes "$REAL_HOME")"
log "== inicio: $START_BYTES bytes ($(du -sh "$REAL_HOME" | cut -f1)) | DRY_RUN=$DRY_RUN | $(date -u +%FT%TZ) =="

# ---- 1) backups/memory.* : mantém os KEEP_NEWEST_BACKUPS mais novos ----
if [ -d "$REAL_HOME/backups" ]; then
  mapfile -t BKS < <(find "$REAL_HOME/backups" -maxdepth 1 -type d -name 'memory.*' 2>/dev/null | sort)
  if [ "${#BKS[@]}" -gt "$KEEP_NEWEST_BACKUPS" ]; then
    n=$(( ${#BKS[@]} - KEEP_NEWEST_BACKUPS ))
    for b in "${BKS[@]:0:$n}"; do
      purge "$b" "backup antigo"
    done
  else
    log "INFO : backups <= $KEEP_NEWEST_BACKUPS — nada a purgar (${#BKS[@]} encontrados)"
  fi
else
  log "INFO : diretorio backups/ inexistente"
fi

# ---- 2) memory.bak.* : cópias antigas inteiras (fora da cadeia viva) ----
found_bak=0
while IFS= read -r -d '' mb; do
  found_bak=1
  purge "$mb" "memory.bak antigo"
done < <(find "$REAL_HOME" -maxdepth 1 -type d -name 'memory.bak.*' -print0 2>/dev/null)
[ "$found_bak" = "1" ] || log "INFO : nenhum memory.bak.* encontrado"

# ---- 3) logs rotacionáveis: *.log com mtime antigo FORA do WAL ----
if [ "$LOG_RETENTION_DAYS" -gt 0 ]; then
  while IFS= read -r -d '' lf; do
    case "$lf" in
      */memory/blockchain/wal/*) continue ;;   # NUNCA toca WAL
      *) : ;;
    esac
    sz="$(stat -c%s "$lf" 2>/dev/null || echo 0)"
    purge "$lf" "log antigo"
  done < <(find "$REAL_HOME" -type f -name '*.log' -mtime +"$LOG_RETENTION_DAYS" -not -path '*/memory/blockchain/wal/*' -print0 2>/dev/null)
fi

# ---- Resumo ----
END_BYTES="$(calc_bytes "$REAL_HOME")"
FREED_MB=$(( (START_BYTES - END_BYTES) / 1024 / 1024 ))
log "== fim: $END_BYTES bytes ($(du -sh "$REAL_HOME" | cut -f1)) | ~${FREED_MB} MB libertados =="
log "== df / : $(df -h / | awk 'NR==2{print $3" usado / "$4" livres ("$5")"}') =="
if [ "$DRY_RUN" = "1" ]; then
  log "== MODO DRY-RUN: nada foi apagado. Para executar: DRY_RUN=0 $(basename "$0") =="
fi
exit 0
