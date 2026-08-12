#!/usr/bin/env bash
# deploy_surgical_patch.sh
# Aplica o hotfix cirurgico 2026-08-12 no servidor de producao mybait.org.
# Idempotente: pode rodar N vezes. Faz snapshot antes de qualquer alteracao.
#
# Uso local (no servidor):
#   sudo bash scripts/deploy_surgical_patch.sh
#
# Uso remoto (via SSH):
#   scp -P 22022 -r . baitcoin@143.95.213.237:/tmp/patch/
#   ssh -p 22022 baitcoin@143.95.213.237 "sudo bash /tmp/patch/scripts/deploy_surgical_patch.sh"
#
# Variaveis opcionais:
#   APP_DIR       destino do backend (default /home/baitcoin/app)
#   WEB_DIR       destino do frontend (default /var/www/mybait)
#   SERVICE       nome do systemd unit (default baitcoin.service)
#   NO_RESTART=1  pular restart do daemon
#   NO_FRONTEND=1 pular sync do /var/www/mybait

set -euo pipefail

APP_DIR="${APP_DIR:-/home/baitcoin/app}"
WEB_DIR="${WEB_DIR:-/var/www/mybait}"
SERVICE="${SERVICE:-baitcoin.service}"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/home/baitcoin/backups/deploy-${TS}"

log(){ printf '\033[1;36m[%s]\033[0m %s\n' "$(date -u +%H:%M:%S)" "$*"; }
fail(){ printf '\033[1;31m[FAIL]\033[0m %s\n' "$*" >&2; exit 1; }

log "b'AI'tcoin surgical patch deploy — ${TS}"
log "SRC_DIR=${SRC_DIR}"
log "APP_DIR=${APP_DIR}  WEB_DIR=${WEB_DIR}  SERVICE=${SERVICE}"

# 0) Sanity checks
[ -d "${SRC_DIR}/baitcoin_api" ]        || fail "SRC_DIR nao contem baitcoin_api/"
[ -d "${SRC_DIR}/frontend"    ]         || fail "SRC_DIR nao contem frontend/"
command -v rsync >/dev/null             || fail "rsync ausente"
command -v python3 >/dev/null           || fail "python3 ausente"

# 1) Snapshot WAL (se disponivel)
log "1/6 snapshot WAL"
if [ -x /home/baitcoin/scripts/snapshot_verify.sh ]; then
    /home/baitcoin/scripts/snapshot_verify.sh || log "snapshot_verify retornou !=0 (nao bloqueia)"
else
    log "snapshot_verify ausente — pulando"
fi

# 2) Backup dos alvos
log "2/6 backup em ${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"
for f in \
    "${APP_DIR}/baitcoin_api/server.py" \
    "${APP_DIR}/baitcoin_explorer/indices.py" \
    "${APP_DIR}/baitcoin_ai/oracle/feed.py"
do
    [ -f "${f}" ] && cp -a "${f}" "${BACKUP_DIR}/" && log "  backup: ${f}"
done
[ -d "${WEB_DIR}" ] && rsync -a --include='*.html' --include='favicon.svg' --exclude='*' \
    "${WEB_DIR}/" "${BACKUP_DIR}/www/" 2>/dev/null || true

# 3) Syntax check dos arquivos do patch
log "3/6 python -m py_compile"
python3 -m py_compile \
    "${SRC_DIR}/baitcoin_api/server.py" \
    "${SRC_DIR}/baitcoin_explorer/indices.py" \
    "${SRC_DIR}/baitcoin_ai/oracle/feed.py"
log "  OK"

# 4) Sync backend
log "4/6 sync backend -> ${APP_DIR}"
rsync -a --delete \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.bak.*' \
    "${SRC_DIR}/baitcoin_api"        "${APP_DIR}/"
rsync -a --delete \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.bak.*' \
    "${SRC_DIR}/baitcoin_explorer"   "${APP_DIR}/"
rsync -a --delete \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.bak.*' \
    "${SRC_DIR}/baitcoin_ai"         "${APP_DIR}/"
for mod in baitcoin_faucet baitcoin_bank baitcoin_wallet baitcoin_token baitcoin_core \
           baitcoin_memory baitcoin_obscura baitcoin_whitelabel baitcoin_sdk \
           baitcoin_bridge baitcoin_mainnet; do
    [ -d "${SRC_DIR}/${mod}" ] && rsync -a --delete \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.bak.*' \
        "${SRC_DIR}/${mod}" "${APP_DIR}/" || true
done
for f in daemon_production.py daemon_wrapper.py; do
    [ -f "${SRC_DIR}/${f}" ] && cp -a "${SRC_DIR}/${f}" "${APP_DIR}/${f}" || true
done
log "  OK"

# 5) Sync frontend
if [ "${NO_FRONTEND:-0}" != "1" ]; then
    log "5/6 sync frontend -> ${WEB_DIR}"
    install -d -o www-data -g www-data "${WEB_DIR}" 2>/dev/null || mkdir -p "${WEB_DIR}"
    rsync -a --chown=www-data:www-data \
        --include='*.html' --include='favicon.svg' --exclude='*' \
        "${SRC_DIR}/frontend/" "${WEB_DIR}/"
    systemctl reload nginx 2>/dev/null || service nginx reload 2>/dev/null || log "  nginx reload falhou (verifique manualmente)"
    log "  OK"
else
    log "5/6 frontend pulado (NO_FRONTEND=1)"
fi

# 6) Restart daemon
if [ "${NO_RESTART:-0}" != "1" ]; then
    log "6/6 systemctl restart ${SERVICE}"
    systemctl restart "${SERVICE}"
    sleep 3
    systemctl is-active "${SERVICE}" || fail "${SERVICE} nao subiu"
    log "  ${SERVICE} active"
else
    log "6/6 restart pulado (NO_RESTART=1)"
fi

log "DEPLOY OK — backup em ${BACKUP_DIR}"
log "rode: bash ${SRC_DIR}/scripts/verify_deploy.sh"
