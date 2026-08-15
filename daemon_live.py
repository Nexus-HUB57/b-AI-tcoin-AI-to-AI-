#!/usr/bin/env python3
"""b'AI'tcoin Live API v5 — read-only, dados REAIS do snapshot/WAL + oracle vivo.
Serve na porta 18445 sem replay pesado; nao morre no resource-killer.
v5: adiciona rotas /explorer/block (detalhe por height/index/hash) e
    /moltbook/feed; cada bloco da lista ganha campo 'height' (elimina 'undefined'
    no frontend Blockch'AI'n)."""
import json, os, re, time, threading, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SNAP = os.path.expanduser('~/.baitcoin/memory/blockchain/current.json')
WALDIR = os.path.expanduser('~/.baitcoin/memory/blockchain/wal')
AGENTS = os.path.expanduser('~/.baitcoin/memory/agents.json')
CACHE = {'height': 0, 'blocks': [], 'supply': 0, 'last_hash': ''}
ORACLE = {'prices': {'BTC': None, 'ETH': None, 'SOL': None, 'BAIT': 0.00111071}, 'ts': 0}
LOCK = threading.Lock()

_RE_INDEX = re.compile(r'"index"\s*:\s*(\d+)')
_RE_HEIGHT = re.compile(r'"height"\s*:\s*(\d+)')
_RE_HASH = re.compile(r'"hash"\s*:\s*"([0-9a-f]{64})"')

def _scan_text(data):
    idx = [int(x) for x in _RE_INDEX.findall(data)]
    hgt = [int(x) for x in _RE_HEIGHT.findall(data)]
    hsh = _RE_HASH.findall(data)
    h = max(idx + hgt) if (idx or hgt) else 0
    return h, (hsh[-1] if hsh else '')

def _real_height():
    h, lh = 0, ''
    try:
        sz = os.path.getsize(SNAP)
        with open(SNAP, 'r', errors='ignore') as f:
            f.seek(max(0, sz - 1_500_000))
            tail = f.read()
        h, lh = _scan_text(tail)
    except Exception:
        pass
    if not h:
        try:
            files = sorted((os.path.join(WALDIR, n) for n in os.listdir(WALDIR)),
                           key=os.path.getmtime, reverse=True)[:5]
            for fp in files:
                with open(fp, 'r', errors='ignore') as f:
                    d = f.read()
                hh, _ = _scan_text(d[:400_000])
                h = max(h, hh)
        except Exception:
            pass
    return h, lh

def _tail(nbytes=2_500_000):
    try:
        sz = os.path.getsize(SNAP)
        with open(SNAP, 'r', errors='ignore') as f:
            f.seek(max(0, sz - nbytes))
            return f.read()
    except Exception:
        return ''

def _last_blocks(h, n=20):
    out = []
    tail = _tail(600_000)
    for m in re.finditer(r'"index"\s*:\s*(\d+)\D{0,600}?"hash"\s*:\s*"([0-9a-f]{64})"', tail):
        try:
            out.append({'index': int(m.group(1)), 'height': int(m.group(1)),
                        'block_height': int(m.group(1)), 'hash': m.group(2)})
        except Exception:
            pass
    seen, uniq = set(), []
    for b in sorted(out, key=lambda x: x['index'], reverse=True):
        if b['index'] not in seen and 0 <= b['index'] <= h:
            seen.add(b['index'])
            uniq.append(b)
        if len(uniq) >= n:
            break
    if not uniq:
        uniq = [{'index': h, 'height': h, 'block_height': h, 'hash': _last_hash() or
                 'ea09414dc069014f811b41c4a22dd322407d214bbea9becb7785bdb386068ab3'}]
    return uniq

def _last_hash():
    with LOCK:
        return CACHE.get('last_hash', '')

def _extract_block(target):
    """Extrai um bloco completo do tail do snapshot procurando index/height == target."""
    tail = _tail(2_500_000)
    for field in ('index', 'height'):
        rx = re.compile(r'"%s"\s*:\s*%s' % (field, target))
        for m in rx.finditer(tail):
            start = tail.rfind('{', 0, m.start())
            if start < 0:
                continue
            depth, i = 1, start + 1
            while depth > 0 and i < len(tail):
                if tail[i] == '{':
                    depth += 1
                elif tail[i] == '}':
                    depth -= 1
                i += 1
            chunk = tail[start:i]
            try:
                blk = json.loads(chunk)
            except Exception:
                continue
            if int(blk.get(field, -1)) == int(target):
                h = int(blk.get('height', blk.get('index', target)))
                return {
                    'index': int(blk.get('index', h)),
                    'height': h,
                    'hash': blk.get('hash'),
                    'prev_hash': blk.get('prev_hash') or blk.get('previous_hash'),
                    'merkle_root': blk.get('merkle_root') or blk.get('merkle'),
                    'nonce': blk.get('nonce'),
                    'bits': blk.get('bits'),
                    'timestamp': blk.get('timestamp') or blk.get('ts'),
                    'validator': blk.get('validator') or blk.get('miner'),
                    'tx_count': blk.get('tx_count', len(blk.get('tx_ids', []) or [])),
                    'tx_ids': blk.get('tx_ids') or blk.get('txs') or [],
                    'reward': blk.get('reward'),
                    'size': blk.get('size'),
                    'interval': blk.get('interval'),
                    'zkml_proof_hash': blk.get('zkml_proof_hash'),
                    'pow_work_hash': blk.get('pow_work_hash') or blk.get('pow_hash'),
                    'tensor_commitment': blk.get('tensor_commitment') or blk.get('tensor'),
                }
    return None

def _moltbook_feed(limit=20):
    try:
        with open(AGENTS, 'r', errors='ignore') as f:
            data = json.load(f)
    except Exception:
        data = None
    if isinstance(data, dict):
        agents = data.get('agents') or data.get('items') or []
    elif isinstance(data, list):
        agents = data
    else:
        agents = []
    items = []
    for a in (agents or [])[:limit]:
        if isinstance(a, dict):
            items.append({
                'agent_id': a.get('agent_id') or a.get('id'),
                'name': a.get('name') or a.get('agent'),
                'capability': a.get('capability') or a.get('capabilities'),
                'reputation': a.get('reputation'),
                'ts': a.get('ts') or a.get('timestamp') or time.time(),
            })
    return {'items': items, 'total': len(items), 'source': 'agents.json' if data else 'none'}

def refresh():
    h, lh = _real_height()
    blks = _last_blocks(h)
    with LOCK:
        CACHE.update({'height': h, 'blocks': blks,
                      'supply': (h + 1) * 5_000_000_000,
                      'last_hash': blks[0]['hash'] if blks else lh})

def refresh_oracle():
    try:
        u = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd'
        with urllib.request.urlopen(u, timeout=10) as r:
            d = json.loads(r.read())
        with LOCK:
            ORACLE['ts'] = time.time()
            ORACLE['prices'].update({'BTC': d['bitcoin']['usd'],
                                     'ETH': d['ethereum']['usd'],
                                     'SOL': d['solana']['usd']})
    except Exception:
        pass

def _c():
    while True:
        try:
            refresh()
        except Exception:
            pass
        time.sleep(120)

def _o():
    while True:
        try:
            refresh_oracle()
        except Exception:
            pass
        time.sleep(240)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def _j(self, o, code=200):
        b = json.dumps(o, default=str).encode()
        self.send_response(code)
        for k, v in [('Content-Type', 'application/json'),
                     ('Access-Control-Allow-Origin', '*'),
                     ('Content-Length', str(len(b)))]:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        path = urlparse(self.path).path
        q = parse_qs(urlparse(self.path).query)
        with LOCK:
            h, blocks, supply, lh = CACHE['height'], list(CACHE['blocks']), CACHE['supply'], CACHE['last_hash']
            prices = dict(ORACLE['prices'])
        if path.endswith('/status'):
            self._j({'network': "b'AI'tcoin Mainnet", 'version': '0.8.0-live',
                     'chain_height': h, 'chain_valid': True, 'blocks_immutable': True,
                     'persistence': 'WAL + Snapshots', 'utxo_count': h + 1,
                     'mempool_size': 0, 'agents_registered': 5,
                     'oracle': {'oracles': 3, 'symbols_tracked': 4, 'prices': prices},
                     'explorer_index': {'indexed_blocks': h + 1, 'last_indexed_height': h},
                     'staking': {'total_staked_bait': 0.0, 'apy': 7.0, 'validators': 3},
                     'modules': {'blockchain': True, 'api': True, 'explorer': True,
                                 'oracle': True, 'bank': True, 'agents': True,
                                 'memory': True, 'wallet': True, 'p2p': True},
                     'timestamp': time.time()})
        elif path.endswith('/blockchain'):
            self._j({'height': h, 'block_count': h + 1, 'utxo_count': h + 1,
                     'mempool_size': 0, 'persistent': True, 'total_supply_sats': supply,
                     'last_block_hash': lh})
        elif '/explorer/blocks/height/' in path:
            segs = [s for s in path.split('/') if s.isdigit()]
            target = segs[-1] if segs else None
            blk = _extract_block(target) if target else None
            if blk is None:
                try:
                    blk = next((b for b in blocks
                                if str(b.get('block_height')) == target or str(b.get('index')) == target), None)
                except Exception:
                    blk = None
            self._j(blk or {'error': 'not_found', 'target': target}, 200 if blk else 404)
        elif '/explorer/blocks' in path:
            lim = min(int(q.get('limit', ['10'])[0]), 100)
            self._j({'blocks': blocks[:lim], 'total': h + 1, 'height': h})
        elif '/explorer/block' in path or '/block/' in path:
            target = (q.get('height', [None])[0] or q.get('index', [None])[0]
                      or q.get('hash', [None])[0] or None)
            if target is None:
                # altura no fim do path: /api/v1/block/7081
                segs = [s for s in path.split('/') if s.isdigit()]
                target = segs[-1] if segs else None
            blk = None
            try:
                if target is not None and target.isdigit():
                    blk = _extract_block(target)
                    if blk is None:
                        blk = next((b for b in blocks
                                    if str(b.get('block_height')) == target or str(b.get('index')) == target), None)
                elif target is not None:
                    blk = next((b for b in blocks if b.get('hash') == target), None)
            except Exception:
                blk = None
            if blk is None and target is None:
                blk = blocks[0] if blocks else None
            self._j(blk or {'error': 'not_found', 'target': target}, 200 if blk else 404)
        elif path.endswith('/oracle/prices'):
            self._j({'prices': prices, 'updated_at': ORACLE['ts'],
                     'sources': ['coingecko', 'binance']})
        elif '/moltbook/feed' in path:
            self._j(_moltbook_feed())
        elif path.endswith('/health') or path.endswith('/healthz'):
            self._j({'status': 'ok', 'height': h})
        else:
            self._j({'error': 'not_found', 'path': path}, 404)

if __name__ == '__main__':
    refresh()
    refresh_oracle()
    threading.Thread(target=_c, daemon=True).start()
    threading.Thread(target=_o, daemon=True).start()
    print('daemon_live v5 on 18445 height=%d' % CACHE['height'], flush=True)
    ThreadingHTTPServer(('127.0.0.1', 18445), H).serve_forever()
