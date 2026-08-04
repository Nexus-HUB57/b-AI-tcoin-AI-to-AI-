#!/usr/bin/env python3
"""
b'AI'tcoin CGI Gateway — HostGator Compatible

Pure Python CGI that bootstraps the ecosystem, starts the daemon,
and proxies API requests. No framework dependencies required.

Trigger: https://www.mybait.org/api.cgi/api/v1/status
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
DAEMON_PORT = 18445
STARTUP_TIMEOUT = 15
MAX_PROXY_TIMEOUT = 25

# ═══════════════════════════════════════════════════════
# Logging to stderr (appears in HostGator error_log)
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
    """Send a JSON HTTP response."""
    body = json.dumps(data, default=str).encode('utf-8')
    sys.stdout.write(f'Status: {status}\n')
    sys.stdout.write(f'Content-Type: application/json\n')
    sys.stdout.write(f'Content-Length: {len(body)}\n')
    sys.stdout.write(f'Access-Control-Allow-Origin: *\n')
    sys.stdout.write(f'Access-Control-Allow-Methods: GET, POST, OPTIONS\n')
    sys.stdout.write(f'Access-Control-Allow-Headers: Content-Type, Authorization, X-Moltbook-Identity\n')
    sys.stdout.write(f'X-Powered-By: b-AI-tcoin-CGI-Gateway\n')
    sys.stdout.write(f'X-Frame-Options: DENY\n')
    sys.stdout.write(f'\n')
    sys.stdout.flush()
    os.write(sys.stdout.fileno(), body)

def respond_error(msg, status=503):
    respond_json({"error": msg, "timestamp": time.time()}, status=status)

# ═══════════════════════════════════════════════════════
# Daemon Manager
# ═══════════════════════════════════════════════════════
def is_daemon_running():
    """Check if the daemon process is alive."""
    if not os.path.exists(PIDFILE):
        return False
    try:
        with open(PIDFILE, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # Signal 0 = check if alive
        return True
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        return False

def start_daemon():
    """Start the b'AI'tcoin daemon in background."""
    if is_daemon_running():
        log.info(f'Daemon already running (PID from {PIDFILE})')
        return True

    # Ensure directories exist
    os.makedirs(INSTALL_DIR, exist_ok=True)

    # Check for venv
    python_bin = os.path.join(VENV_DIR, 'bin', 'python3')
    if not os.path.exists(python_bin):
        log.warning(f'Venv not found at {VENV_DIR}')
        # Try system python
        python_bin = 'python3'

    daemon_script = os.path.join(INSTALL_DIR, 'main_daemon.py')
    if not os.path.exists(daemon_script):
        log.error(f'main_daemon.py not found at {daemon_script}')
        return False

    try:
        log.info(f'Starting daemon: {python_bin} {daemon_script} --blocks 0 --api-port {DAEMON_PORT}')
        env = os.environ.copy()
        env['PATH'] = f"{os.path.dirname(python_bin)}:{env.get('PATH', '')}"
        env['PYTHONPATH'] = INSTALL_DIR
        env['BAIT_DATA_PATH'] = os.path.join(INSTALL_DIR, 'baitcoin_data')

        with open(LOGFILE, 'a') as log_f:
            proc = subprocess.Popen(
                [python_bin, daemon_script, '--blocks', '0', '--api-port', str(DAEMON_PORT)],
                cwd=INSTALL_DIR,
                env=env,
                stdout=log_f,
                stderr=log_f,
                start_new_session=True,
            )
        with open(PIDFILE, 'w') as f:
            f.write(str(proc.pid))
        log.info(f'Daemon started with PID {proc.pid}')
        return True
    except Exception as e:
        log.error(f'Failed to start daemon: {e}')
        return False

def wait_for_daemon(timeout=STARTUP_TIMEOUT):
    """Wait until the daemon API is responding."""
    log.info(f'Waiting for daemon on port {DAEMON_PORT} (timeout {timeout}s)...')
    start = time.time()
    while time.time() - start < timeout:
        try:
            conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=3)
            conn.request('GET', '/api/v1/status')
            resp = conn.getresponse()
            body = resp.read().decode('utf-8')
            conn.close()
            if resp.status == 200:
                log.info(f'Daemon is responding ({len(body)} bytes)')
                return True
        except (ConnectionRefusedError, OSError):
            pass
        time.sleep(1)
    log.warning(f'Daemon not responding after {timeout}s')
    return False

# ═══════════════════════════════════════════════════════
# Request Proxy
# ═══════════════════════════════════════════════════════
def proxy_request():
    """Forward the CGI request to the local daemon."""
    request_method = os.environ.get('REQUEST_METHOD', 'GET')
    path_info = os.environ.get('PATH_INFO', '/api/v1/status')
    query_string = os.environ.get('QUERY_STRING', '')
    content_type = os.environ.get('CONTENT_TYPE', 'application/json')
    content_length = int(os.environ.get('CONTENT_LENGTH', 0))

    # Read request body if present
    body = sys.stdin.read(content_length) if content_length > 0 else ''

    # Build target URL
    target_path = path_info
    if query_string:
        target_path += '?' + query_string

    log.info(f'Proxying {request_method} {target_path}')

    try:
        conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=MAX_PROXY_TIMEOUT)
        headers = {'Content-Type': content_type}
        # Forward Moltbook identity header if present
        moltbook_id = os.environ.get('HTTP_X_MOLTBOOK_IDENTITY', '')
        if moltbook_id:
            headers['X-Moltbook-Identity'] = moltbook_id

        conn.request(request_method, target_path, body=body, headers=headers)
        resp = conn.getresponse()
        resp_body = resp.read()
        resp_headers = resp.getheaders()
        conn.close()

        # Forward response
        sys.stdout.write(f'Status: {resp.status}\n')
        for name, value in resp_headers:
            if name.lower() not in ('transfer-encoding', 'connection', 'server'):
                sys.stdout.write(f'{name}: {value}\n')
        sys.stdout.write(f'X-Powered-By: b-AI-tcoin-CGI-Gateway\n')
        sys.stdout.write(f'Access-Control-Allow-Origin: *\n')
        sys.stdout.write(f'\n')
        sys.stdout.flush()
        os.write(sys.stdout.fileno(), resp_body)

    except Exception as e:
        log.error(f'Proxy error: {e}')
        respond_error(f'API proxy error: {str(e)}', 502)

# ═══════════════════════════════════════════════════════
# Main CGI Entry
# ═══════════════════════════════════════════════════════
def main():
    try:
        # Handle CORS preflight
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

        # Ensure daemon is running
        if not is_daemon_running():
            if not start_daemon():
                respond_error('Daemon failed to start. Check server logs.', 500)
                return
            if not wait_for_daemon():
                respond_error(f'Daemon starting up. Retry in {STARTUP_TIMEOUT}s. Check daemon.log for progress.', 503)
                return

        # Proxy the request
        proxy_request()

    except Exception as e:
        log.error(f'CGI error: {e}\n{traceback.format_exc()}')
        respond_error(f'Internal error: {str(e)}', 500)

if __name__ == '__main__':
    main()
