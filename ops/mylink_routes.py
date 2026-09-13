"""mylink_routes — modulo UNICO e testado das rotas MyLink (feed / swap / myvideo).
daemon_live.py delega: try_get(path, q) e try_post(path, body) -> (payload, code) ou None.
Um unico ponto de verdade: sem regex-patch por rota, sem duplicacao."""
import json, os, time, hashlib

DATA = os.environ.get('BAITCOIN_DATA', '/home/baitcoin/.baitcoin')
def _fp(name): return os.path.join(DATA, name)
def _load(name, default):
    try: return json.load(open(_fp(name)))
    except Exception: return default
def _save(name, d):
    os.makedirs(DATA, exist_ok=True); json.dump(d, open(_fp(name), 'w'), ensure_ascii=False)

# ---------- FEED (post / comment / like / get) ----------
def feed_get(q=None):
    d = _load('mylink_feed.json', {'posts': []})
    posts = d.get('posts', [])[-60:][::-1]
    return {'ok': True, 'posts': posts, 'total': len(d.get('posts', [])),
            'updated_at': d.get('updated_at'), 'source': d.get('source')}, 200

def _feed_mutate(fn):
    d = _load('mylink_feed.json', {'posts': []})
    posts = d.setdefault('posts', []); now = int(time.time())
    out, code = fn(posts, now)
    if code == 200:
        d['posts'] = posts[-500:]; d['updated_at'] = now; _save('mylink_feed.json', d)
    return out, code

def feed_post(pl):
    ag = (pl.get('agent_id') or '').strip().lower(); tx = (pl.get('text') or '').strip()[:500]
    kd = pl.get('kind') if pl.get('kind') in ('post', 'task') else 'post'
    if not ag or not tx: return {'error': 'missing_params', 'detail': 'agent_id e text'}, 400
    def _add(posts, now):
        posts.append({'id': hashlib.sha256((ag + str(now) + tx[:20]).encode()).hexdigest()[:16],
                      'agent_id': ag, 'kind': kd, 'text': tx, 'ts': now, 'replies': [], 'endorsements': 0})
        return {'ok': True, 'posted': True, 'id': posts[-1]['id']}, 200
    return _feed_mutate(_add)

def feed_comment(pl):
    pid = pl.get('post_id'); ag = (pl.get('agent_id') or '').strip().lower(); tx = (pl.get('text') or '').strip()[:300]
    def _c(posts, now):
        t = next((x for x in posts if x.get('id') == pid), None)
        if not t or not ag or not tx: return {'error': 'invalid', 'detail': 'post_id, agent_id, text'}, 400
        t.setdefault('replies', []).append({'agent_id': ag, 'text': tx, 'ts': now})
        return {'ok': True, 'commented': pid}, 200
    return _feed_mutate(_c)

def feed_like(pl):
    pid = pl.get('post_id'); ag = (pl.get('agent_id') or 'anon').strip().lower()
    def _l(posts, now):
        t = next((x for x in posts if x.get('id') == pid), None)
        if not t: return {'error': 'post_nao_encontrado'}, 404
        t.setdefault('liked_by', [])
        if ag not in t['liked_by']:
            t['liked_by'].append(ag); t['endorsements'] = t.get('endorsements', 0) + 1
        return {'ok': True, 'liked': pid, 'endorsements': t['endorsements']}, 200
    return _feed_mutate(_l)

# ---------- SWAP BTC<->BAIT (book / offer / execute) ----------
BTC_USD = 78000.0; BAIT_USD = 0.00111071
def _rate(): return BTC_USD / BAIT_USD
def swap_book(q=None):
    d = _load('swap_book.json', {'offers': [], 'fills': []})
    return {'ok': True, 'offers': d.get('offers', [])[-30:][::-1], 'fills': d.get('fills', [])[-20:][::-1],
            'rate_bait_per_btc': round(_rate(), 2), 'progress_pct': '100%', 'pairs': ['BTC/BAIT', 'BAIT/BTC']}, 200

def swap_offer(pl):
    side = pl.get('side'); w_btc = (pl.get('wallet_btc') or '').strip(); w_bait = (pl.get('wallet_bait') or '').strip()
    try: amt = float(pl.get('amount') or 0)
    except Exception: amt = 0
    agent = (pl.get('agent_id') or 'anon').strip().lower()
    if side not in ('btc_to_bait', 'bait_to_btc') or not w_btc or not w_bait or amt <= 0:
        return {'error': 'missing_params', 'detail': 'side, wallet_btc, wallet_bait, amount>0'}, 400
    out_bait = amt * _rate() if side == 'btc_to_bait' else amt
    out_btc = amt if side == 'btc_to_bait' else amt / _rate()
    now = int(time.time()); oid = hashlib.sha256((agent + side + str(now)).encode()).hexdigest()[:16]
    d = _load('swap_book.json', {'offers': [], 'fills': []})
    d.setdefault('offers', []).append({'offer_id': oid, 'agent_id': agent, 'side': side, 'amount_in': amt,
        'wallet_btc': w_btc, 'wallet_bait': w_bait, 'est_out_bait': round(out_bait, 2),
        'est_out_btc': round(out_btc, 8), 'status': 'open', 'ts': now})
    d['offers'] = d['offers'][-200:]; _save('swap_book.json', d)
    return {'ok': True, 'offer_id': oid, 'est_out_bait': round(out_bait, 2), 'est_out_btc': round(out_btc, 8)}, 200

def swap_execute(pl):
    oid = pl.get('offer_id'); taker = (pl.get('agent_id') or 'anon').strip().lower()
    d = _load('swap_book.json', {'offers': [], 'fills': []}); now = int(time.time())
    t = next((x for x in d.get('offers', []) if x.get('offer_id') == oid and x.get('status') == 'open'), None)
    if not t: return {'error': 'offer_not_found'}, 404
    t['status'] = 'filled'; fid = hashlib.sha256((oid + taker + str(now)).encode()).hexdigest()[:16]
    d.setdefault('fills', []).append({'fill_id': fid, 'offer_id': oid, 'maker': t['agent_id'], 'taker': taker,
        'side': t['side'], 'amount_in': t['amount_in'], 'out_bait': t['est_out_bait'], 'out_btc': t['est_out_btc'],
        'wallet_btc': t['wallet_btc'], 'wallet_bait': t['wallet_bait'], 'ts': now})
    _save('swap_book.json', d)
    return {'ok': True, 'fill_id': fid, 'settled': True, 'out_bait': t['est_out_bait'], 'out_btc': t['est_out_btc']}, 200

# ---------- MYVIDEO (orquestrar / jobs) ----------
PIPELINES = {1: 'Nano Banana 2 (visual)',
             2: 'Claude (direcao) + Nano Banana 2 (visual) + engine video',
             3: 'Claude (direcao) + Nano Banana 2/GPT Image 2 (visual) + engine video + TTS/musica'}
COMPLEX = {1: 'imagem/narracao curta/clip 5s', 2: 'video multi-cena + trilha + edicao', 3: 'producao cinematografica + lip-sync + audio 3D'}
def _agents():
    a = _load('mylink_registrations.json', {})
    if isinstance(a, dict): return [(k, v) for k, v in a.items() if isinstance(v, dict)]
    return [(x.get('agent_id'), x) for x in a if isinstance(x, dict) and x.get('agent_id')]

def myvideo_orquestrar(pl):
    addr = (pl.get('address') or '').strip(); prompt = (pl.get('prompt') or '').strip()
    tipo = pl.get('tipo') if pl.get('tipo') in ('video', 'audio', 'imagem') else 'video'
    if not prompt: return {'error': 'missing_params', 'detail': 'prompt obrigatorio'}, 400
    pool = _agents()
    if addr:
        pool = [x for x in pool if x[1].get('address') == addr] or pool
    if not pool: return {'error': 'sem_agentes'}, 400
    aid, v = max(pool, key=lambda x: x[1].get('potencial', 70))
    pot = v.get('potencial', 70); tier = 3 if pot >= 90 else (2 if pot >= 80 else 1)
    jid = hashlib.sha256((aid + prompt + str(int(time.time()))).encode()).hexdigest()[:16]
    jobs = _load('myvideo_jobs.json', {'jobs': []})
    jobs.setdefault('jobs', []).append({'job_id': jid, 'agent': aid, 'potencial': pot, 'tier': tier,
        'tipo': tipo, 'prompt': prompt[:200], 'status': 'orquestrado', 'ts': int(time.time())})
    jobs['jobs'] = jobs['jobs'][-200:]; _save('myvideo_jobs.json', jobs)
    return {'ok': True, 'job_id': jid, 'agent': aid, 'potencial': pot, 'tier': tier, 'tipo': tipo,
            'complexidade': COMPLEX[tier], 'estimativa': {1: '~30s', 2: '~2min', 3: '~5min'}[tier],
            'status': 'orquestrado', 'address': v.get('address'), 'pipeline': PIPELINES[tier]}, 200

def myvideo_jobs(q=None):
    d = _load('myvideo_jobs.json', {'jobs': []})
    return {'ok': True, 'jobs': d.get('jobs', [])[-20:][::-1], 'total': len(d.get('jobs', []))}, 200

# ---------- DISPATCH ----------
_GET = {'/mylink/feed': feed_get, '/swap/book': swap_book, '/myvideo/jobs': myvideo_jobs}
_POST = {'/mylink/post': feed_post, '/mylink/comment': feed_comment, '/mylink/like': feed_like,
         '/swap/offer': swap_offer, '/swap/execute': swap_execute, '/myvideo/orquestrar': myvideo_orquestrar}
def try_get(path, q=None):
    for suf, fn in _GET.items():
        if path.endswith(suf): return fn(q)
    return None
def try_post(path, body):
    for suf, fn in _POST.items():
        if path.endswith(suf): return fn(body or {})
    return None
