#!/usr/bin/env python3
"""
b'AI'tcoin CGI Gateway v2 — HostGator Compatible + Fulltime Auto-Recovery

Pure Python CGI que:
  1. Bootstrapa o ecossistema b'AI'tcoin
  2. Inicia o daemon se estiver caído (cold-start automático)
  3. Faz proxy das requisições REST
  4. Auto-recovery: detecta PID morto e re-inicia sem intervenção

Trigger: https://www.mybait.org/api.cgi/api/v1/status

Novo em v2:
  * Watchdog: se PID existe mas processo não responde, mata e reinicia
  * Cold-start timeout reduzido para 12s
  * Health-check antes do proxy (evita 502 quando daemon está travado)
  * Log rotativo (>5MB → truncate)
"""
import os
import sys
import json
import time
import signal
import subprocess
import traceback
from urllib.parse import urlparse, parse_qs
from http.client import HTTPConnection

# ═══════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════
HOME = os.environ.get('HOME', '/home1/luca2490')
INSTALL_DIR = os.path.join(HOME, 'baitcoin-api')
VENV_DIR = os.path.join(INSTALL_DIR, 'venv')
PIDFILE = os.path.join(INSTALL_DIR, 'daemon.pid')
LOGFILE = os.path.join(INSTALL_DIR, 'daemon.log')
HEALTHFILE = os.path.join(INSTALL_DIR, 'daemon.health')
DAEMON_PORT = 18445
STARTUP_TIMEOUT = 12
MAX_PROXY_TIMEOUT = 25
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
HEALTH_CHECK_TIMEOUT = 3

# ═══════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════
import logging
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='[bait-cgi] %(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('bait-cgi')

# ═══════════════════════════════════════════════════════
# HTTP Response Helpers
# ═══════════════════════════════════════════════════════
def respond_json(data, status=200):
    body = json.dumps(data, default=str).encode('utf-8')
    sys.stdout.write(f'Status: {status}\n')
    sys.stdout.write(f'Content-Type: application/json\n')
    sys.stdout.write(f'Content-Length: {len(body)}\n')
    sys.stdout.write(f'Access-Control-Allow-Origin: *\n')
    sys.stdout.write(f'Access-Control-Allow-Methods: GET, POST, OPTIONS\n')
    sys.stdout.write(f'Access-Control-Allow-Headers: Content-Type, Authorization, X-Moltbook-Identity\n')
    sys.stdout.write(f'X-Powered-By: b-AI-tcoin-CGI-Gateway-v2\n')
    sys.stdout.write(f'X-Frame-Options: DENY\n')
    sys.stdout.write(f'Cache-Control: no-store\n')
    sys.stdout.write(f'\n')
    sys.stdout.flush()
    os.write(sys.stdout.fileno(), body)

def respond_error(msg, status=503):
    respond_json({"error": msg, "timestamp": time.time(), "gateway": "v2"}, status=status)

# ═══════════════════════════════════════════════════════
# Log Rotation
# ═══════════════════════════════════════════════════════
def rotate_log_if_needed():
    try:
        if os.path.exists(LOGFILE) and os.path.getsize(LOGFILE) > LOG_MAX_BYTES:
            with open(LOGFILE, 'rb') as f:
                f.seek(-LOG_MAX_BYTES // 2, 2)
                tail = f.read()
            with open(LOGFILE, 'wb') as f:
                f.write(b'[log-rotated at ' + str(time.time()).encode() + b']\n')
                f.write(tail)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════
# Daemon Watchdog & Manager
# ═══════════════════════════════════════════════════════
def is_pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False

def get_daemon_pid():
    if not os.path.exists(PIDFILE):
        return None
    try:
        with open(PIDFILE, 'r') as f:
            return int(f.read().strip())
    except (ValueError, OSError):
        return None

def daemon_responds():
    """HTTP health-check no daemon local — mais confiável que PID."""
    try:
        conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=HEALTH_CHECK_TIMEOUT)
        conn.request('GET', '/api/v1/status')
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return resp.status == 200
    except Exception:
        return False

def is_daemon_healthy():
    """Duas condições: PID vivo E API responde."""
    pid = get_daemon_pid()
    if pid is None or not is_pid_alive(pid):
        return False
    return daemon_responds()

def kill_zombie_daemon():
    """Se PID existe mas API não responde, mata o zumbi."""
    pid = get_daemon_pid()
    if pid is None:
        return
    if not is_pid_alive(pid):
        try: os.remove(PIDFILE)
        except OSError: pass
        return
    log.warning(f'Killing zombie daemon PID {pid} (não responde na porta {DAEMON_PORT})')
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if is_pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
    except Exception as e:
        log.error(f'Falha ao matar zombie: {e}')
    try: os.remove(PIDFILE)
    except OSError: pass

def start_daemon():
    """Inicia daemon em background — modo perpétuo (--blocks 0 = infinito)."""
    if is_daemon_healthy():
        return True

    kill_zombie_daemon()
    os.makedirs(INSTALL_DIR, exist_ok=True)

    python_bin = os.path.join(VENV_DIR, 'bin', 'python3')
    if not os.path.exists(python_bin):
        python_bin = 'python3'

    daemon_script = os.path.join(INSTALL_DIR, 'main_daemon.py')
    if not os.path.exists(daemon_script):
        log.error(f'main_daemon.py não encontrado em {daemon_script}')
        return False

    try:
        log.info(f'Cold-start: {python_bin} {daemon_script} --blocks 0 --api-port {DAEMON_PORT}')
        env = os.environ.copy()
        env['PATH'] = f"{os.path.dirname(python_bin)}:{env.get('PATH', '')}"
        env['PYTHONPATH'] = INSTALL_DIR
        env['BAIT_DATA_PATH'] = os.path.join(INSTALL_DIR, 'baitcoin_data')

        rotate_log_if_needed()
        with open(LOGFILE, 'a') as log_f:
            log_f.write(f'\n\n════ COLD-START @ {time.strftime("%Y-%m-%d %H:%M:%S")} ════\n')
            log_f.flush()
            proc = subprocess.Popen(
                [python_bin, daemon_script, '--blocks', '0', '--api-port', str(DAEMON_PORT)],
                cwd=INSTALL_DIR,
                env=env,
                stdout=log_f,
                stderr=log_f,
                start_new_session=True,  # Sobrevive ao término do CGI
            )
        with open(PIDFILE, 'w') as f:
            f.write(str(proc.pid))
        with open(HEALTHFILE, 'w') as f:
            f.write(json.dumps({"started_at": time.time(), "pid": proc.pid}))
        log.info(f'Daemon iniciado PID {proc.pid}')
        return True
    except Exception as e:
        log.error(f'Falha ao iniciar daemon: {e}')
        return False

def wait_for_daemon(timeout=STARTUP_TIMEOUT):
    log.info(f'Aguardando daemon na porta {DAEMON_PORT} (timeout {timeout}s)...')
    start = time.time()
    while time.time() - start < timeout:
        if daemon_responds():
            elapsed = time.time() - start
            log.info(f'Daemon respondendo após {elapsed:.1f}s')
            return True
        time.sleep(0.8)
    log.warning(f'Daemon não respondeu em {timeout}s')
    return False

# ═══════════════════════════════════════════════════════
# Request Proxy
# ═══════════════════════════════════════════════════════
def proxy_request():
    request_method = os.environ.get('REQUEST_METHOD', 'GET')
    path_info = os.environ.get('PATH_INFO', '/api/v1/status')
    query_string = os.environ.get('QUERY_STRING', '')
    content_type = os.environ.get('CONTENT_TYPE', 'application/json')
    content_length = int(os.environ.get('CONTENT_LENGTH', 0))

    body = sys.stdin.read(content_length) if content_length > 0 else ''

    target_path = path_info
    if query_string:
        target_path += '?' + query_string

    log.info(f'Proxy {request_method} {target_path}')

    try:
        conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=MAX_PROXY_TIMEOUT)
        headers = {'Content-Type': content_type}
        moltbook_id = os.environ.get('HTTP_X_MOLTBOOK_IDENTITY', '')
        if moltbook_id:
            headers['X-Moltbook-Identity'] = moltbook_id

        conn.request(request_method, target_path, body=body, headers=headers)
        resp = conn.getresponse()
        resp_body = resp.read()
        resp_headers = resp.getheaders()
        conn.close()

        sys.stdout.write(f'Status: {resp.status}\n')
        for name, value in resp_headers:
            if name.lower() not in ('transfer-encoding', 'connection', 'server'):
                sys.stdout.write(f'{name}: {value}\n')
        sys.stdout.write(f'X-Powered-By: b-AI-tcoin-CGI-Gateway-v2\n')
        sys.stdout.write(f'Access-Control-Allow-Origin: *\n')
        sys.stdout.write(f'\n')
        sys.stdout.flush()
        os.write(sys.stdout.fileno(), resp_body)

    except Exception as e:
        log.error(f'Proxy error: {e}')
        # Se proxy falhou, o daemon pode ter morrido MID-request — tenta re-cold-start
        respond_error(f'API proxy error: {str(e)}. Cold-start será tentado na próxima requisição.', 502)

# ═══════════════════════════════════════════════════════
# Main CGI Entry
# ═══════════════════════════════════════════════════════
def main():
    try:
        # CORS preflight
        if os.environ.get('REQUEST_METHOD') == 'OPTIONS':
            sys.stdout.write('Status: 204\n')
            sys.stdout.write('Content-Type: text/plain\n')
            sys.stdout.write('Access-Control-Allow-Origin: *\n')
            sys.stdout.write('Access-Control-Allow-Methods: GET, POST, OPTIONS\n')
            sys.stdout.write('Access-Control-Allow-Headers: Content-Type, Authorization, X-Moltbook-Identity\n')
            sys.stdout.write('Access-Control-Max-Age: 86400\n')
            sys.stdout.write('\n')
            sys.stdout.flush()
            return

        # Watchdog: se daemon não está saudável, cold-start
        if not is_daemon_healthy():
            log.info('Daemon não-saudável → cold-start')
            if not start_daemon():
                respond_error('Daemon falhou ao iniciar. Verifique daemon.log no servidor.', 500)
                return
            if not wait_for_daemon():
                respond_error(f'Daemon em cold-start. Recarregue em {STARTUP_TIMEOUT}s.', 503)
                return

        proxy_request()

    except Exception as e:
        log.error(f'CGI error: {e}\n{traceback.format_exc()}')
        respond_error(f'Internal error: {str(e)}', 500)

if __name__ == '__main__':
    main()
