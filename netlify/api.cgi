#!/usr/bin/env python3
"""
b'AI'tcoin CGI Gateway v3 — Self-Updating + Fulltime Auto-Recovery

v3 additions over v2:
  * /api/cgi/update — pulls ALL files from GitHub, restarts daemon
  * /api/cgi/status — CGI gateway health info
  * /api/cgi/restart — restart daemon only
  * Self-update: downloads its own replacement from GitHub
  * Secret-based auth for admin endpoints (UPDATE_SECRET env var)

Bootstrap: upload THIS file to ~/public_html/api.cgi via cPanel File Manager,
then visit https://www.mybait.org/api.cgi/api/cgi/update?secret=YOUR_SECRET
All other files (HTML, daemon code, modules) will be pulled automatically.
"""
import os, sys, json, time, signal, subprocess, traceback, shutil
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen, Request
from http.client import HTTPConnection

# Configuration
HOME = os.environ.get('HOME', '/home1/luca2490')
INSTALL_DIR = os.path.join(HOME, 'baitcoin-api')
VENV_DIR = os.path.join(INSTALL_DIR, 'venv')
PIDFILE = os.path.join(INSTALL_DIR, 'daemon.pid')
LOGFILE = os.path.join(INSTALL_DIR, 'daemon.log')
HEALTHFILE = os.path.join(INSTALL_DIR, 'daemon.health')
DAEMON_PORT = 18445
STARTUP_TIMEOUT = 30
MAX_PROXY_TIMEOUT = 25
LOG_MAX_BYTES = 5 * 1024 * 1024
HEALTH_CHECK_TIMEOUT = 3
PUBLIC_HTML = os.path.join(HOME, 'public_html')
REPO_RAW = 'https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main'
UPDATE_SECRET = os.environ.get('UPDATE_SECRET', 'baitcoin-update-2024')
CGI_VERSION = 'v3'

# Logging
import logging
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='[bait-cgi] %(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('bait-cgi')

# HTTP Helpers
def respond_json(data, status=200):
    body = json.dumps(data, default=str).encode('utf-8')
    sys.stdout.write(f'Status: {status}\n')
    sys.stdout.write(f'Content-Type: application/json\n')
    sys.stdout.write(f'Content-Length: {len(body)}\n')
    sys.stdout.write(f'Access-Control-Allow-Origin: *\n')
    sys.stdout.write(f'Access-Control-Allow-Methods: GET, POST, OPTIONS\n')
    sys.stdout.write(f'Access-Control-Allow-Headers: Content-Type, Authorization, X-Moltbook-Identity\n')
    sys.stdout.write(f'X-Powered-By: b-AI-tcoin-CGI-Gateway-{CGI_VERSION}\n')
    sys.stdout.write(f'X-Frame-Options: DENY\n')
    sys.stdout.write(f'Cache-Control: no-store\n')
    sys.stdout.write(f'\n')
    sys.stdout.flush()
    os.write(sys.stdout.fileno(), body)

def respond_error(msg, status=503):
    respond_json({"error": msg, "timestamp": time.time(), "gateway": CGI_VERSION}, status=status)

def check_secret():
    qs = parse_qs(os.environ.get('QUERY_STRING', ''))
    provided = qs.get('secret', [None])[0]
    if not provided or provided != UPDATE_SECRET:
        return False
    return True

# Log Rotation
def rotate_log_if_needed():
    try:
        if os.path.exists(LOGFILE) and os.path.getsize(LOGFILE) > LOG_MAX_BYTES:
            with open(LOGFILE, 'rb') as f:
                f.seek(-LOG_MAX_BYTES // 2, 2)
                tail = f.read()
            with open(LOGFILE, 'wb') as f:
                f.write(b'[log-rotated]\n')
                f.write(tail)
    except Exception:
        pass

# Daemon Manager
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
    pid = get_daemon_pid()
    if pid is None or not is_pid_alive(pid):
        return False
    return daemon_responds()

def kill_zombie_daemon():
    pid = get_daemon_pid()
    if pid is None:
        return
    if not is_pid_alive(pid):
        try: os.remove(PIDFILE)
        except OSError: pass
        return
    log.warning(f'Killing zombie PID {pid}')
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if is_pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
    except Exception as e:
        log.error(f'Kill zombie failed: {e}')
    try: os.remove(PIDFILE)
    except OSError: pass

def stop_daemon():
    pid = get_daemon_pid()
    if pid is None:
        return True
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if is_pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
        log.info(f'Daemon PID {pid} stopped')
    except Exception as e:
        log.error(f'Stop daemon: {e}')
    try:
        subprocess.run(['pkill', '-f', 'main_daemon.py'], capture_output=True, timeout=5)
    except Exception:
        pass
    try: os.remove(PIDFILE)
    except OSError: pass
    return True

def start_daemon():
    if is_daemon_healthy():
        return True
    kill_zombie_daemon()
    os.makedirs(INSTALL_DIR, exist_ok=True)
    python_bin = os.path.join(VENV_DIR, 'bin', 'python3')
    if not os.path.exists(python_bin):
        python_bin = 'python3'
    daemon_script = os.path.join(INSTALL_DIR, 'main_daemon.py')
    if not os.path.exists(daemon_script):
        log.error(f'main_daemon.py not found at {daemon_script}')
        return False
    try:
        log.info(f'Cold-start: {python_bin} {daemon_script}')
        env = os.environ.copy()
        env['PATH'] = f"{os.path.dirname(python_bin)}:{env.get('PATH', '')}"
        env['PYTHONPATH'] = INSTALL_DIR
        env['BAIT_DATA_PATH'] = os.path.join(INSTALL_DIR, 'baitcoin_data')
        rotate_log_if_needed()
        with open(LOGFILE, 'a') as log_f:
            log_f.write(f'\n COLD-START @ {time.strftime("%Y-%m-%d %H:%M:%S")} \n')
            log_f.flush()
            proc = subprocess.Popen(
                [python_bin, daemon_script, '--blocks', '0', '--api-port', str(DAEMON_PORT)],
                cwd=INSTALL_DIR, env=env,
                stdout=log_f, stderr=log_f, start_new_session=True,
            )
        with open(PIDFILE, 'w') as f:
            f.write(str(proc.pid))
        log.info(f'Daemon started PID {proc.pid}')
        return True
    except Exception as e:
        log.error(f'Start daemon failed: {e}')
        return False

def wait_for_daemon(timeout=STARTUP_TIMEOUT):
    start = time.time()
    while time.time() - start < timeout:
        if daemon_responds():
            return True
        time.sleep(0.8)
    return False

# Self-Update Engine
def download_file(url, dest):
    try:
        req = Request(url, headers={'User-Agent': 'baitcoin-updater/1.0'})
        with urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(dest, 'wb') as f:
            f.write(data)
        return len(data)
    except Exception as e:
        log.error(f'Download {url}: {e}')
        return 0

def do_update():
    results = []
    
    # 1. Static HTML — todas as paginas do frontend
    for fname in ['index.html', 'blockchain.html', 'bainkr.html', 'faucet.html', 'sdk.html', 'obscura.html', 'favicon.svg', '.htaccess']:
        url = f'{REPO_RAW}/netlify/{fname}'
        dest = os.path.join(PUBLIC_HTML, fname)
        size = download_file(url, dest)
        if size > 100:
            os.chmod(dest, 0o644)
            results.append(f'{fname}: OK ({size}b)')
        else:
            results.append(f'{fname}: FAILED')
    
    # whitepaper
    size = download_file(f'{REPO_RAW}/netlify/whitepaper.pdf', os.path.join(PUBLIC_HTML, 'whitepaper.pdf'))
    if size > 1000:
        results.append(f'whitepaper.pdf: OK ({size}b)')
    
    # 2. Daemon core
    os.makedirs(INSTALL_DIR, exist_ok=True)
    for fname in ['main_daemon.py', 'daemon_wrapper.py', 'daemon_production.py', 'requirements.txt']:
        url = f'{REPO_RAW}/{fname}'
        dest = os.path.join(INSTALL_DIR, fname)
        size = download_file(url, dest)
        if size > 100:
            results.append(f'{fname}: OK ({size}b)')
        else:
            results.append(f'{fname}: FAILED')
    
    # 3. Modules
    modules = [
        'baitcoin_core/blockchain/chain.py', 'baitcoin_core/blockchain/block.py',
        'baitcoin_core/blockchain/mempool.py', 'baitcoin_core/blockchain/fees.py',
        'baitcoin_core/blockchain/addresses.py', 'baitcoin_core/blockchain/tx_verifier.py',
        'baitcoin_core/consensus/zkml_engine.py', 'baitcoin_core/consensus/pouw.py',
        'baitcoin_core/consensus/difficulty.py', 'baitcoin_core/consensus/validator_election.py',
        'baitcoin_core/cryptography/schnorr.py',
        'baitcoin_core/network/p2p.py', 'baitcoin_core/network/gossip.py',
        'baitcoin_core/network/block_sync.py', 'baitcoin_core/network/p2p_bridge.py',
        'baitcoin_core/contracts/contract_engine.py', 'baitcoin_core/contracts/relayer.py',
        'baitcoin_core/ecosystem.py',
        'baitcoin_api/server.py', 'baitcoin_api/moltbook_auth.py',
        'baitcoin_ai/agent_protocol/registry.py', 'baitcoin_ai/agent_protocol/__init__.py',
        'baitcoin_ai/marketplace/services.py',
        'baitcoin_ai/oracle/feed.py', 'baitcoin_ai/oracle/real_feed.py',
        'baitcoin_bank/staking/pool.py', 'baitcoin_bank/lending/engine.py',
        'baitcoin_token/erc20_like/bait_token.py', 'baitcoin_token/tokenomics/schedule.py',
        'baitcoin_token/governance/governor.py',
        'baitcoin_wallet/keys/manager.py', 'baitcoin_wallet/transactions/builder.py',
        'baitcoin_wallet/storage/kv_store.py', 'baitcoin_wallet/paper_wallet.py',
        'baitcoin_faucet/faucet.py',
        'baitcoin_memory/store.py', 'baitcoin_memory/state.py',
        'baitcoin_explorer/search.py', 'baitcoin_explorer/indices.py',
        'baitcoin_explorer/docs.py', 'baitcoin_explorer/analytics.py',
        'baitcoin_explorer/rate_limiter.py',
        'baitcoin_obscura/bridge.py', 'baitcoin_obscura/config.py',
        'baitcoin_obscura/agent_capability.py', 'baitcoin_obscura/__init__.py',
        'baitcoin_bridge/pool.py', 'baitcoin_bridge/watcher.py', 'baitcoin_bridge/__init__.py',
        'baitcoin_whitelabel/config.py', 'baitcoin_whitelabel/engine.py',
        'baitcoin_whitelabel/presets.py',
    ]
    mod_ok = 0
    for mod_path in modules:
        url = f'{REPO_RAW}/{mod_path}'
        dest = os.path.join(INSTALL_DIR, mod_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        size = download_file(url, dest)
        if size > 50:
            mod_ok += 1
    results.append(f'modules: {mod_ok}/{len(modules)}')
    
    # 4. Watchdog
    size = download_file(f'{REPO_RAW}/netlify/watchdog.sh', os.path.join(INSTALL_DIR, 'watchdog.sh'))
    if size > 100:
        os.chmod(os.path.join(INSTALL_DIR, 'watchdog.sh'), 0o755)
        results.append('watchdog.sh: OK')
    
    # 5. Deps
    try:
        subprocess.run(['pip3', 'install', '-q', '-r', os.path.join(INSTALL_DIR, 'requirements.txt')],
                       capture_output=True, timeout=60)
        results.append('deps: OK')
    except Exception as e:
        results.append(f'deps: {e}')
    
    # 6. Self-update api.cgi (LAST!)
    cgi_dest = os.path.join(PUBLIC_HTML, 'api.cgi')
    size = download_file(f'{REPO_RAW}/netlify/api.cgi', cgi_dest + '.new')
    if size > 500:
        os.chmod(cgi_dest + '.new', 0o755)
        shutil.move(cgi_dest + '.new', cgi_dest)
        results.append(f'api.cgi: self-updated')
    else:
        results.append('api.cgi: self-update FAILED')
        if os.path.exists(cgi_dest + '.new'):
            os.remove(cgi_dest + '.new')
    
    # 7. Restart daemon
    stop_daemon()
    time.sleep(1)
    if start_daemon() and wait_for_daemon(timeout=20):
        results.append('daemon: restarted OK')
    else:
        results.append('daemon: will cold-start on next request')
    
    return results

# Proxy
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
        sys.stdout.write(f'X-Powered-By: b-AI-tcoin-CGI-Gateway-{CGI_VERSION}\n')
        sys.stdout.write(f'Access-Control-Allow-Origin: *\n')
        sys.stdout.write(f'\n')
        sys.stdout.flush()
        os.write(sys.stdout.fileno(), resp_body)
    except Exception as e:
        log.error(f'Proxy error: {e}')
        respond_error(f'API proxy error: {str(e)}', 502)

# Admin Endpoints
def handle_admin():
    path_info = os.environ.get('PATH_INFO', '')
    
    if path_info == '/api/cgi/status':
        respond_json({
            'gateway': CGI_VERSION,
            'daemon_pid': get_daemon_pid(),
            'daemon_healthy': is_daemon_healthy(),
            'daemon_responds': daemon_responds(),
            'install_dir': INSTALL_DIR,
            'public_html': PUBLIC_HTML,
            'home': HOME,
            'logfile_size': os.path.getsize(LOGFILE) if os.path.exists(LOGFILE) else 0,
        })
        return True
    
    if path_info == '/api/cgi/update' and os.environ.get('REQUEST_METHOD') == 'POST':
        if not check_secret():
            respond_error('Unauthorized', 401)
            return True
        log.info('Self-update triggered')
        results = do_update()
        respond_json({
            'status': 'updated',
            'gateway_version': CGI_VERSION,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            'results': results,
        })
        return True
    
    if path_info == '/api/cgi/restart' and os.environ.get('REQUEST_METHOD') == 'POST':
        if not check_secret():
            respond_error('Unauthorized', 401)
            return True
        stop_daemon()
        time.sleep(1)
        ok = start_daemon() and wait_for_daemon(timeout=20)
        respond_json({'restarted': ok, 'timestamp': time.time()})
        return True
    
    return False

# Main Entry
def main():
    try:
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

        if os.environ.get('PATH_INFO', '').startswith('/api/cgi/'):
            if handle_admin():
                return
        
        if not is_daemon_healthy():
            log.info('Daemon unhealthy -> cold-start')
            if not start_daemon():
                respond_error('Daemon failed to start.', 500)
                return
            if not wait_for_daemon():
                respond_error(f'Daemon cold-starting. Retry in {STARTUP_TIMEOUT}s.', 503)
                return
        
        proxy_request()
    
    except Exception as e:
        log.error(f'CGI error: {e}\n{traceback.format_exc()}')
        respond_error(f'Internal error: {str(e)}', 500)

if __name__ == '__main__':
    main()
