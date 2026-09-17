#!/usr/bin/env bash
# ============================================================
# rotate_wal.sh — Rotação segura do WAL b'AI'tcoin (semanal, via cron)
# - WAL > 500MB e inativos (>120min) vão para .archive/ (quarentena)
# - Itens do .archive com >30 dias são expurgados
# - NUNCA apaga WAL ativo; gera log em /var/log/rotate_wal.log
# ============================================================
set -euo pipefail
WAL=/home/baitcoin/.baitcoin/memory/blockchain/wal
ARCH="$WAL/.archive"
TS=$(date +%Y%m%d-%H%M%S)
LOG=/var/log/rotate_wal.log
mkdir -p "$ARCH"
{
  echo "== rotate_wal $TS =="
  df -h /home/baitcoin | tail -1
  moved=$(find "$WAL" -maxdepth 1 -name '*.log' -size +500M -mmin +120 | wc -l)
  find "$WAL" -maxdepth 1 -name '*.log' -size +500M -mmin +120 -exec mv {} "$ARCH/" \;
  purged=$(find "$ARCH" -maxdepth 1 -name '*.log' -mtime +30 | wc -l)
  find "$ARCH" -maxdepth 1 -name '*.log' -mtime +30 -delete
  echo "movidos_quarentena=$moved  expurgados_30d=$purged"
  df -h /home/baitcoin | tail -1
} >> "$LOG" 2>&1
