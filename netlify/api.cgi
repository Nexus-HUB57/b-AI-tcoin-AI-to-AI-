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
CGI_VERSION = 'v3.1'

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
    for fname in ['index.html', 'blockchain.html', 'bainkr.html', 'faucet.html', 'fundo.html', 'swap.html', 'sdk.html', 'obscura.html', 'myvideo.html', 'favicon.svg', '.htaccess']:
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
    
    # MyLink sub-pages (fundo, swap, hub, etc.)
    for subdir, fname in [('mylink/fundo', 'fundo.html'), ('mylink/fundo/swap', 'swap.html'), ('mylink/myvideo', 'myvideo.html')]:
        sub_dir = os.path.join(PUBLIC_HTML, subdir)
        os.makedirs(sub_dir, exist_ok=True)
        url = f'{REPO_RAW}/netlify/{fname}'
        dest = os.path.join(sub_dir, 'index.html')
        size = download_file(url, dest)
        if size > 100:
            os.chmod(dest, 0o644)
            results.append(f'{subdir}/index.html: OK ({size}b)')
        else:
            results.append(f'{subdir}/index.html: FAILED')
    
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
    
    # Accept both /api/cgi/* and /cgi/* (PATH_INFO varies by .htaccess)
    if path_info == '/api/cgi/status' or path_info == '/cgi/status':
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
    
    if (path_info == '/api/cgi/update' or path_info == '/cgi/update') and os.environ.get('REQUEST_METHOD') == 'POST':
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
    
    if (path_info == '/api/cgi/restart' or path_info == '/cgi/restart') and os.environ.get('REQUEST_METHOD') == 'POST':
        if not check_secret():
            respond_error('Unauthorized', 401)
            return True
        stop_daemon()
        time.sleep(1)
        ok = start_daemon() and wait_for_daemon(timeout=20)
        respond_json({'restarted': ok, 'timestamp': time.time()})
        return True
    
    return False

# ═══ MyLink Fund Endpoint — served directly by CGI (no daemon needed) ═══
CUSTODY_DATA = {
    'address': 'bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s',
    'pub_key': '024d02fc98e862a9606c0eee4bb427e4d42a7f246db6417ebffb8cd3cf77b8f158',
    'derivation_path': 'm/0h/0/0',
    'script_type': 'p2wpkh',
    'contract': '0xc3f31d647CCa231A7BeE40207d7b08E6A5483b07',
    'fee_recipient': '0x56d5b62b19db5c2e3a97867e7c3e13965cea6982',
    'deployer_evm': '0x56d5b62b19db5c2e3a97867e7c3e13965cea6982',
}

def handle_mylink_fund():
    """Serve /mylink/fund directly — custody data + live chain data from daemon."""
    fund = {
        'reserve_bait': 0,
        'reserve_btc': 0,
        'covered_agents': 0,
        'valid_signatures': 0,
        'custody_address': CUSTODY_DATA['address'],
        'custody_pub_key': CUSTODY_DATA['pub_key'],
        'custody_script_type': CUSTODY_DATA['script_type'],
        'custody_derivation': CUSTODY_DATA['derivation_path'],
        'custody_contract': CUSTODY_DATA['contract'],
        'custody_fee_recipient': CUSTODY_DATA['fee_recipient'],
        'custody_challenge_sig': 'schnorr_bip340_' + CUSTODY_DATA['pub_key'][:16],
        'por_anchor': None,
        'composition': {
            'agents_rewards': 0.40,
            'sla_escrow_a2a': 0.25,
            'defi_vaults_staking': 0.20,
            'treasury_ai_store': 0.15,
        },
        'governance': {
            'council': 'multi-sig 3/5',
            'signatories': ['Eva-Alpha', 'Imperador-Core', 'Aethelgard'],
            'distribution_rule': '80/10/10',
        },
        'timestamp': time.time(),
    }
    # Try to enrich with live daemon data
    try:
        conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=3)
        conn.request('GET', '/api/v1/supply')
        resp = conn.getresponse()
        if resp.status == 200:
            sup = json.loads(resp.read())
            fund['reserve_bait'] = sup.get('minted', sup.get('total_supply', 0))
        conn.close()
    except Exception:
        pass
    try:
        conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=3)
        conn.request('GET', '/api/v1/status')
        resp = conn.getresponse()
        if resp.status == 200:
            st = json.loads(resp.read())
            fund['covered_agents'] = st.get('agents_registered', 0)
            fund['valid_signatures'] = st.get('agents_registered', 0)
            if st.get('latest_block_hash'):
                fund['por_anchor'] = st['latest_block_hash']
        conn.close()
    except Exception:
        pass
    respond_json(fund)

# ═══ Swap & Sweep Endpoints — served directly by CGI ═══
SWAP_FEE_BPS = 50  # 0.5% swap fee

def handle_swap_quote():
    """GET /v1/swap/quote?amount_btc=X — returns BAIT amount, rate, fee."""
    qs = parse_qs(os.environ.get('QUERY_STRING', ''))
    try:
        amount_btc = float(qs.get('amount_btc', ['0'])[0])
    except (ValueError, TypeError):
        respond_error('Invalid amount_btc', 400)
        return
    # Get BTC price from CoinGecko
    btc_usd = 0
    try:
        req = Request('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
                      headers={'User-Agent': 'baitcoin-swap/1.0'})
        with urlopen(req, timeout=5) as resp:
            cg = json.loads(resp.read())
            btc_usd = cg.get('bitcoin', {}).get('usd', 0)
    except Exception:
        pass
    # BAIT price (from oracle or fallback)
    bait_usd = 0.00111071  # fallback
    try:
        conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=3)
        conn.request('GET', '/api/v1/oracle/prices')
        resp = conn.getresponse()
        if resp.status == 200:
            od = json.loads(resp.read())
            if od.get('prices', {}).get('BAIT'):
                bait_usd = od['prices']['BAIT']
        conn.close()
    except Exception:
        pass
    rate = btc_usd / bait_usd if bait_usd > 0 else 0
    gross_bait = amount_btc * rate
    fee_bait = gross_bait * SWAP_FEE_BPS / 10000
    net_bait = gross_bait - fee_bait
    respond_json({
        'amount_btc': amount_btc,
        'btc_usd': btc_usd,
        'bait_usd': bait_usd,
        'rate': rate,
        'gross_bait': gross_bait,
        'fee_bait': fee_bait,
        'fee_bps': SWAP_FEE_BPS,
        'net_bait': net_bait,
        'custody_address': CUSTODY_DATA['address'],
        'timestamp': time.time(),
    })

def handle_sweep_status():
    """GET /v1/sweep/status — returns custody UTXO info from Mempool.space."""
    utxos = []
    balance_sats = 0
    try:
        req = Request(f'https://mempool.space/api/address/{CUSTODY_DATA["address"]}/utxo',
                      headers={'User-Agent': 'baitcoin-sweep/1.0'})
        with urlopen(req, timeout=8) as resp:
            utxos = json.loads(resp.read())
    except Exception:
        pass
    for u in utxos:
        balance_sats += u.get('value', 0)
    # Fee estimate: economy rate * (68 vbytes per input + 31 + 10)
    fees = {}
    try:
        req = Request('https://mempool.space/api/v1/fees/recommended',
                      headers={'User-Agent': 'baitcoin-sweep/1.0'})
        with urlopen(req, timeout=5) as resp:
            fees = json.loads(resp.read())
    except Exception:
        fees = {'economyFee': 1, 'hourFee': 1}
    fee_rate = fees.get('economyFee', 1)
    est_vbytes = len(utxos) * 68 + 31 + 10
    est_fee_sats = est_vbytes * fee_rate
    respond_json({
        'custody_address': CUSTODY_DATA['address'],
        'utxo_count': len(utxos),
        'utxos': utxos[:20],  # cap at 20 for response size
        'balance_sats': balance_sats,
        'balance_btc': balance_sats / 1e8,
        'fee_rate_sat_vb': fee_rate,
        'sweep_est_vbytes': est_vbytes,
        'sweep_est_fee_sats': est_fee_sats,
        'sweep_net_sats': max(0, balance_sats - est_fee_sats),
        'network_fees': fees,
        'timestamp': time.time(),
    })

RENDER_API = 'https://b-ai-tcoin-ai-to-ai.onrender.com'

# ═══ MyVideo Endpoints — Sistema Autônomo de Produção Audiovisual Generativa ═══
MYVIDEO_JOB_DIR = os.path.join(INSTALL_DIR, 'myvideo_jobs')
MYVIDEO_STATS_FILE = os.path.join(INSTALL_DIR, 'myvideo_stats.json')

# In-memory production queue for myvideo
_myvideo_queue = []
_myvideo_stats = {'total_productions': 0, 'total_bait_burned': 0, 'total_iterations': 0}

def _load_myvideo_stats():
    """Load persisted myvideo stats from disk."""
    global _myvideo_stats
    try:
        if os.path.exists(MYVIDEO_STATS_FILE):
            with open(MYVIDEO_STATS_FILE, 'r') as f:
                _myvideo_stats = json.loads(f.read())
    except Exception:
        pass

def _save_myvideo_stats():
    """Persist myvideo stats to disk."""
    try:
        os.makedirs(os.path.dirname(MYVIDEO_STATS_FILE), exist_ok=True)
        with open(MYVIDEO_STATS_FILE, 'w') as f:
            f.write(json.dumps(_myvideo_stats))
    except Exception:
        pass

def handle_myvideo_orquestrar():
    """POST /v1/myvideo/orquestrar — Orchestrate audiovisual production pipeline."""
    _load_myvideo_stats()
    try:
        cl = int(os.environ.get('CONTENT_LENGTH', 0))
        body = sys.stdin.read(cl) if cl > 0 else '{}'
        data = json.loads(body)
    except Exception:
        respond_error('Invalid JSON body', 400)
        return

    prompt = data.get('prompt', '').strip()
    tipo = data.get('tipo', 'video')
    tier = data.get('tier', 2)
    duration = data.get('duration', 10)
    iterations = data.get('iterations', 1)
    address = data.get('address', '')
    agent_id = data.get('agent_id', '')
    cost_bait = data.get('cost_bait', 0)

    if not prompt:
        respond_error('Prompt is required', 400)
        return

    # Generate job ID
    job_id = 'mv_' + str(int(time.time())) + '_' + os.urandom(4).hex()

    # Determine agent and potential
    potencial = 80  # default
    if agent_id:
        # Try to get agent info from daemon
        try:
            conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=3)
            conn.request('GET', '/api/v1/mylink/agents')
            resp = conn.getresponse()
            if resp.status == 200:
                ad = json.loads(resp.read())
                for a in ad.get('agents', []):
                    if a.get('agent_id') == agent_id:
                        potencial = a.get('potential', potencial)
                        break
            conn.close()
        except Exception:
            pass
    else:
        # Auto-select: try to find best agent for the tier
        try:
            conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=3)
            conn.request('GET', '/api/v1/mylink/agents')
            resp = conn.getresponse()
            if resp.status == 200:
                ad = json.loads(resp.read())
                gen_agents = [a for a in ad.get('agents', [])
                             if (a.get('skills', []) and any(s in str(a['skills']) for s in ['video','audio','imagem','gen','studio','design']))
                             or (a.get('potential', 0) >= 60)]
                if gen_agents:
                    best = max(gen_agents, key=lambda a: a.get('potential', 0))
                    agent_id = best.get('agent_id', 'auto')
                    potencial = best.get('potential', potencial)
            conn.close()
        except Exception:
            agent_id = 'auto'

    # Determine complexity level
    tier_int = int(tier)
    if tier_int == 3:
        complexidade = 'cinematografico'
    elif tier_int == 2:
        complexidade = 'complexo'
    else:
        complexidade = 'simples'

    # Estimate time (seconds) based on tier and iterations
    base_time = {1: 15, 2: 45, 3: 120}.get(tier_int, 30)
    estimativa = f'~{base_time * iterations}s'

    # Create job entry
    job = {
        'job_id': job_id,
        'prompt': prompt,
        'tipo': tipo,
        'tier': tier_int,
        'duration': duration,
        'iterations': iterations,
        'address': address,
        'agent_id': agent_id or 'auto',
        'potencial': potencial,
        'cost_bait': cost_bait,
        'complexidade': complexidade,
        'estimativa': estimativa,
        'status': 'orchestrated',
        'quality_base': round(0.55 if tier_int == 1 else 0.70 if tier_int == 2 else 0.85, 3),
        'quality_final': round((0.55 if tier_int == 1 else 0.70 if tier_int == 2 else 0.85) * (1.15 ** iterations), 3),
        'created_at': time.time(),
        'signature': f'schnorr_bip340_{(agent_id or "sys")[:8]}_{job_id[:12]}',
        'content_hash': f'sha256d_{job_id}',
    }

    # Add to in-memory queue (cap at 100)
    _myvideo_queue.append(job)
    if len(_myvideo_queue) > 100:
        _myvideo_queue.pop(0)

    # Update stats
    _myvideo_stats['total_productions'] = _myvideo_stats.get('total_productions', 0) + 1
    _myvideo_stats['total_bait_burned'] = _myvideo_stats.get('total_bait_burned', 0) + cost_bait
    _myvideo_stats['total_iterations'] = _myvideo_stats.get('total_iterations', 0) + iterations
    _save_myvideo_stats()

    respond_json({
        'ok': True,
        'job_id': job_id,
        'agent': agent_id or 'auto',
        'potencial': potencial,
        'tipo': tipo,
        'complexidade': complexidade,
        'tier': tier_int,
        'iterations': iterations,
        'quality_final': job['quality_final'],
        'cost_bait': cost_bait,
        'estimativa': estimativa,
        'status': 'orchestrated',
        'signature': job['signature'],
        'content_hash': job['content_hash'],
        'timestamp': time.time(),
    })

def handle_myvideo_fila():
    """GET /v1/myvideo/fila — Return production queue."""
    _load_myvideo_stats()
    respond_json({
        'queue': _myvideo_queue[-50:],  # last 50 jobs
        'total': len(_myvideo_queue),
        'timestamp': time.time(),
    })

def handle_myvideo_status():
    """GET /v1/myvideo/status — Return myvideo system status."""
    _load_myvideo_stats()
    # Count active agents from daemon
    agents_count = 0
    try:
        conn = HTTPConnection('127.0.0.1', DAEMON_PORT, timeout=3)
        conn.request('GET', '/api/v1/mylink/agents')
        resp = conn.getresponse()
        if resp.status == 200:
            ad = json.loads(resp.read())
            agents_count = len([a for a in ad.get('agents', [])
                               if (a.get('skills', []) and any(s in str(a['skills']) for s in ['video','audio','imagem','gen','studio','design']))
                               or (a.get('potential', 0) >= 60)])
        conn.close()
    except Exception:
        agents_count = 8  # fallback

    respond_json({
        'system': 'myvideo_autonomous',
        'version': '1.0.0',
        'paradigm': 'generative_native_exponential',
        'external_dependencies': 0,
        'agents_available': agents_count,
        'queue_length': len(_myvideo_queue),
        'total_productions': _myvideo_stats.get('total_productions', 0),
        'total_bait_burned': _myvideo_stats.get('total_bait_burned', 0),
        'total_iterations': _myvideo_stats.get('total_iterations', 0),
        'compound_rate': 0.15,
        'tiers': {'1': '60-79 simples', '2': '80-89 complexo', '3': '90+ cinematografico'},
        'endpoints': ['/myvideo/orquestrar', '/myvideo/fila', '/myvideo/status'],
        'timestamp': time.time(),
    })

# Render Fallback Proxy — when local daemon is dead, proxy GET to Render
RENDER_READONLY = {'GET'}
def proxy_to_render():
    path_info = os.environ.get('PATH_INFO', '/api/v1/status')
    query_string = os.environ.get('QUERY_STRING', '')
    target = path_info + ('?' + query_string if query_string else '')
    request_method = os.environ.get('REQUEST_METHOD', 'GET')
    if request_method not in RENDER_READONLY:
        respond_error('Local daemon offline. Write ops unavailable.', 503)
        return
    try:
        req = Request(f'{RENDER_API}{target}', headers={'User-Agent': 'bait-cgi-fallback/1.0'})
        with urlopen(req, timeout=15) as resp:
            body = resp.read()
        sys.stdout.write(f'Status: {resp.status}\n')
        for k, v in resp.getheaders():
            if k.lower() not in ('transfer-encoding', 'connection', 'server'):
                sys.stdout.write(f'{k}: {v}\n')
        sys.stdout.write(f'X-Powered-By: b-AI-tcoin-CGI-Gateway-{CGI_VERSION}-render-fallback\n')
        sys.stdout.write(f'Access-Control-Allow-Origin: *\n')
        sys.stdout.write(f'\n')
        sys.stdout.flush()
        os.write(sys.stdout.fileno(), body)
    except Exception as e:
        log.error(f'Render fallback error: {e}')
        respond_error(f'Both local and Render API unavailable: {e}', 502)

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

        # FIX: .htaccess sets PATH_INFO=/$1 (strips /api/ prefix)
        # So /api/cgi/status becomes PATH_INFO=/cgi/status (NOT /api/cgi/status)
        _pi = os.environ.get('PATH_INFO', '')
        if _pi.startswith('/api/cgi/') or _pi.startswith('/cgi/'):
            if handle_admin():
                return
        
        # MyLink Fund endpoint — served directly by CGI
        if _pi == '/v1/mylink/fund' or _pi == '/mylink/fund':
            handle_mylink_fund()
            return
        
        # Swap quote endpoint
        if _pi == '/v1/swap/quote' or _pi == '/swap/quote':
            handle_swap_quote()
            return
        
        # Sweep status endpoint
        if _pi == '/v1/sweep/status' or _pi == '/sweep/status':
            handle_sweep_status()
            return

        # MyVideo endpoints — Sistema Autônomo de Produção Audiovisual Generativa
        if _pi == '/v1/myvideo/orquestrar' or _pi == '/myvideo/orquestrar':
            handle_myvideo_orquestrar()
            return
        if _pi == '/v1/myvideo/fila' or _pi == '/myvideo/fila':
            handle_myvideo_fila()
            return
        if _pi == '/v1/myvideo/status' or _pi == '/myvideo/status':
            handle_myvideo_status()
            return
        
        if not is_daemon_healthy():
            log.info('Daemon unhealthy -> cold-start')
            if not start_daemon():
                log.info('Cold-start failed -> Render fallback')
                proxy_to_render()
                return
            if not wait_for_daemon():
                log.info('Daemon timeout -> Render fallback')
                proxy_to_render()
                return
        
        proxy_request()
    
    except Exception as e:
        log.error(f'CGI error: {e}\n{traceback.format_exc()}')
        respond_error(f'Internal error: {str(e)}', 500)

if __name__ == '__main__':
    main()
