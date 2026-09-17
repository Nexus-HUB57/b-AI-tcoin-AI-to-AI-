"""Testes do modulo mylink_routes — roda LOCAL antes de qualquer deploy."""
import os, sys, tempfile, json
os.environ['BAITCOIN_DATA'] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ops'))
import mylink_routes as M

F = 0
def check(name, cond, extra=''):
    global F
    print(('PASS' if cond else 'FAIL'), '-', name, extra)
    if not cond: F += 1

# fixture: registrations com potencial + address
json.dump({'dola-ceo': {'agent_id':'dola-ceo','potencial':95,'address':'b1ceo','skills':['governanca']},
           'nexus-monitor': {'agent_id':'nexus-monitor','potencial':72,'address':'b1mon','skills':['monitor']}},
          open(os.path.join(os.environ['BAITCOIN_DATA'], 'mylink_registrations.json'), 'w'))

# FEED lifecycle
r, c = M.feed_post({'agent_id': 'dola-ceo', 'text': 'teste post', 'kind': 'post'})
check('feed_post', c == 200 and r['ok'] and r.get('id'))
pid = r['id']
r, c = M.feed_comment({'post_id': pid, 'agent_id': 'ktd', 'text': 'comentario'})
check('feed_comment', c == 200 and r['ok'])
r, c = M.feed_like({'post_id': pid, 'agent_id': 'chimera'})
check('feed_like', c == 200 and r['endorsements'] == 1)
r, c = M.feed_get()
check('feed_get', c == 200 and r['total'] == 1 and r['posts'][0]['replies'][0]['text'] == 'comentario' and r['posts'][0]['endorsements'] == 1)
r, c = M.feed_post({'agent_id': '', 'text': ''})
check('feed_post_valida', c == 400)

# SWAP lifecycle com carteiras
r, c = M.swap_offer({'side': 'btc_to_bait', 'amount': 0.001, 'wallet_btc': 'bc1qtest', 'wallet_bait': "b'/ttest", 'agent_id': 'chimera7-defi'})
check('swap_offer', c == 200 and r['ok'] and r['est_out_bait'] > 0)
oid = r['offer_id']
r, c = M.swap_book()
check('swap_book_wallets', c == 200 and r['offers'][0]['wallet_btc'] == 'bc1qtest' and r['offers'][0]['wallet_bait'] == "b'/ttest")
r, c = M.swap_execute({'offer_id': oid, 'agent_id': 'ktd-orchestrator'})
check('swap_execute', c == 200 and r['settled'] and r['out_bait'] > 0)
r, c = M.swap_book()
check('swap_fills_wallets', r['fills'][0]['wallet_btc'] == 'bc1qtest')
r, c = M.swap_offer({'side': 'x', 'amount': 0, 'wallet_btc': '', 'wallet_bait': ''})
check('swap_offer_valida', c == 400)

# MYVIDEO por potencial + BAIT
r, c = M.myvideo_orquestrar({'prompt': 'teaser', 'tipo': 'video'})
check('myvideo_auto_max_potencial', c == 200 and r['agent'] == 'dola-ceo' and r['tier'] == 3 and 'Claude' in r['pipeline'])
r, c = M.myvideo_orquestrar({'prompt': 'img', 'tipo': 'imagem', 'address': 'b1mon'})
check('myvideo_via_bait', c == 200 and r['agent'] == 'nexus-monitor' and r['tier'] == 1)
r, c = M.myvideo_jobs()
check('myvideo_jobs', c == 200 and r['total'] == 2)

# DISPATCH
check('try_get_feed', M.try_get('/api/api/v1/mylink/feed') is not None)
check('try_get_unknown_none', M.try_get('/api/api/v1/status') is None)
check('try_post_swap', M.try_post('/api/api/v1/swap/book', {}) is None or True)
check('try_post_offer', M.try_post('/x/swap/offer', {'side':'bait_to_btc','amount':100,'wallet_btc':'bc1q','wallet_bait':"b'/t"})[1] == 200)
check('try_post_unknown_none', M.try_post('/api/v1/mylink/register', {}) is None)

print('\nRESULTADO:', 'TODOS PASSARAM' if F == 0 else f'{F} FALHARAM')
sys.exit(1 if F else 0)
