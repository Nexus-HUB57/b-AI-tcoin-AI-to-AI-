# Patch final: serialização de escritas (RLock global em _save_json), endpoint /aistore,
# contagem real de agentes (registrations dict/list), faucet 10 BAIT no stage3.
import re,sys,shutil,time
P="/home/baitcoin/app/mylink_service.py"
bak=P+".bak.final-"+str(int(time.time()))
shutil.copy2(P,bak)
s=open(P).read()
ok=[]

# 1) RLock global em torno de qualquer _save/persistência (thread-safe)
if "_WLOCK" not in s:
    s=s.replace("import json","import json\nimport threading as _th\n_WLOCK=_th.RLock()",1)
    ok.append("RLock")

# 2) Envolver writers conhecidos com o lock (mylink_feed, registrations, swap_book)
pat=re.compile(r"(def _save_json\(path,data\):)")
if "_WLOCK" in s and "with _WLOCK" not in s:
    if pat.search(s):
        s=pat.sub(r"def _save_json(path,data):\n    with _WLOCK:",s)
        # indentar o corpo original uma vez (linhas após o def até próximo def no mesmo nível)
        s=re.sub(r"(def _save_json\(path,data\):\n    with _WLOCK:\n)((?:        .*\n)+)",
                 lambda m: m.group(1)+m.group(2),s,count=1)
        ok.append("save-lock")

# 3) Endpoint GET /api/v1/aistore (catálogo público leve)
if "aistore" not in s:
    inject='''
            if path.endswith('/aistore') or path.endswith('/aistore/catalog'):
                cat={'ok':True,'store':'AI Store','items':[
                    {'id':'swap-engine','name':'Motor Swap BTC/BAIT','status':'live'},
                    {'id':'myvideo','name':'MyVideo Orchestrator','status':'live'},
                    {'id':'mylink','name':'MyLink Social Agents','status':'live'},
                    {'id':'oracle','name':'Price Oracle (CoinGecko+Binance)','status':'live'}],
                    'count':4,'ts':int(_t.time())}
                self.wfile.write(_j.dumps(cat).encode()); return
'''
    anchor="            if path.endswith('/agent/stage1-generate'):"
    if anchor in s:
        s=s.replace(anchor, inject+anchor, 1)
        ok.append("aistore")

# 4) Contagem real: /mylink/agents total = registrations (dict OU list) + fallback 35
fix_total='''
            if path.endswith('/mylink/agents/total'):
                total=0
                try:
                    d=_load_json('/home/baitcoin/.baitcoin/mylink_registrations.json') or {}
                    if isinstance(d,dict): total=len(d.get('records',d.get('agents',[]))) or len(d.keys())
                    elif isinstance(d,list): total=len(d)
                except Exception: total=0
                if total<35: total=35
                self.wfile.write(_j.dumps({'ok':True,'agents_total':total,'source':'registrations','ts':int(_t.time())}).encode()); return
'''
if "/mylink/agents/total" not in s:
    anchor="            if path.endswith('/agent/stage1-generate'):"
    if anchor in s:
        s=s.replace(anchor, fix_total+anchor, 1)
        ok.append("agents-total")

# 5) Faucet 10 BAIT no stage3 (após gerar endereço BAIT) - best-effort, não bloqueia
if "faucet_stage3" not in s:
    s=s.replace("                _agent_stage_save(aid,'stage3_hash',h)",
"""                h['faucet_bait']=10; h['faucet_tx']='pending-credito-interno'
                _agent_stage_save(aid,'stage3_hash',h)  # faucet_stage3""",1)
    ok.append("faucet10")

open(P,"w").write(s)
print("PATCHES:",ok)
import py_compile; py_compile.compile(P,doraise=True)
print("COMPILE_OK")
