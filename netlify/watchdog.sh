#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  b'AI'tcoin Watchdog — Fulltime Daemon Recovery para HostGator
#
#  Roda a cada minuto via cron:
#    * * * * * /home1/luca2490/baitcoin-api/watchdog.sh >> /home1/luca2490/baitcoin-api/watchdog.log 2>&1
#
#  Responsabilidades:
#    1. Verifica se o daemon PID existe e está vivo
#    2. Verifica se a porta 18445 responde HTTP 200
#    3. Se qualquer falha → mata zumbi e re-inicia
#    4. Loga eventos em watchdog.log com rotação a 2MB
# ═══════════════════════════════════════════════════════════════════

INSTALL_DIR="/home1/luca2490/baitcoin-api"
DAEMON_SCRIPT="$INSTALL_DIR/main_daemon.py"
PIDFILE="$INSTALL_DIR/daemon.pid"
LOGFILE="$INSTALL_DIR/daemon.log"
WATCHLOG="$INSTALL_DIR/watchdog.log"
DAEMON_PORT=18445
PYTHON_BIN="$INSTALL_DIR/venv/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(which python3 || echo /usr/bin/python3)"
fi

TS=$(date '+%Y-%m-%d %H:%M:%S')

# Rotação do watchlog se >2MB
if [ -f "$WATCHLOG" ]; then
  SIZE=$(stat -c%s "$WATCHLOG" 2>/dev/null || echo 0)
  if [ "$SIZE" -gt 2097152 ]; then
    tail -c 1048576 "$WATCHLOG" > "$WATCHLOG.tmp" && mv "$WATCHLOG.tmp" "$WATCHLOG"
    echo "[$TS] [watchdog] Log rotated ($SIZE bytes → 1MB tail)" >> "$WATCHLOG"
  fi
fi

# Função: iniciar daemon
start_daemon() {
  echo "[$TS] [watchdog] Iniciando daemon..." >> "$WATCHLOG"
  cd "$INSTALL_DIR" || {
    echo "[$TS] [watchdog] ERRO: $INSTALL_DIR não existe" >> "$WATCHLOG"
    exit 1
  }
  export PYTHONPATH="$INSTALL_DIR"
  export BAIT_DATA_PATH="$INSTALL_DIR/baitcoin_data"

  nohup "$PYTHON_BIN" "$DAEMON_SCRIPT" \
        --blocks 0 \
        --api-port "$DAEMON_PORT" \
        >> "$LOGFILE" 2>&1 &
  NEW_PID=$!
  echo "$NEW_PID" > "$PIDFILE"
  disown "$NEW_PID" 2>/dev/null || true
  sleep 2
  if kill -0 "$NEW_PID" 2>/dev/null; then
    echo "[$TS] [watchdog] Daemon iniciado com PID=$NEW_PID" >> "$WATCHLOG"
    return 0
  else
    echo "[$TS] [watchdog] ERRO: PID $NEW_PID morreu após start" >> "$WATCHLOG"
    return 1
  fi
}

# Verificação 1: PID vivo
DAEMON_DOWN=0
if [ ! -f "$PIDFILE" ]; then
  echo "[$TS] [watchdog] PIDfile ausente" >> "$WATCHLOG"
  DAEMON_DOWN=1
else
  PID=$(cat "$PIDFILE" 2>/dev/null)
  if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
    echo "[$TS] [watchdog] PID $PID não está vivo" >> "$WATCHLOG"
    DAEMON_DOWN=1
  fi
fi

# Verificação 2: HTTP responde?
if [ "$DAEMON_DOWN" -eq 0 ]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 4 \
              "http://127.0.0.1:$DAEMON_PORT/api/v1/status" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" != "200" ]; then
    echo "[$TS] [watchdog] PID vivo mas HTTP=$HTTP_CODE (zumbi)" >> "$WATCHLOG"
    if [ -n "$PID" ]; then
      kill -TERM "$PID" 2>/dev/null; sleep 2
      kill -0 "$PID" 2>/dev/null && kill -KILL "$PID" 2>/dev/null
    fi
    rm -f "$PIDFILE"
    DAEMON_DOWN=1
  fi
fi

# Recovery
if [ "$DAEMON_DOWN" -eq 1 ]; then
  start_daemon
  # Aguarda até 10s para responder
  for i in $(seq 1 10); do
    sleep 1
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 3 \
           "http://127.0.0.1:$DAEMON_PORT/api/v1/status" 2>/dev/null || echo "000")
    if [ "$CODE" = "200" ]; then
      echo "[$TS] [watchdog] Recovery OK após ${i}s (HTTP 200)" >> "$WATCHLOG"
      exit 0
    fi
  done
  echo "[$TS] [watchdog] AVISO: daemon iniciado mas não respondeu em 10s" >> "$WATCHLOG"
  exit 2
fi

# Tudo OK — log silencioso apenas se última entrada foi diferente
LAST_STATUS=$(tail -1 "$WATCHLOG" 2>/dev/null | grep -oE "OK|iniciado|Recovery" | head -1)
if [ -z "$LAST_STATUS" ] || [ "$LAST_STATUS" != "OK" ]; then
  echo "[$TS] [watchdog] OK — daemon PID=$PID responsivo" >> "$WATCHLOG"
fi
exit 0
