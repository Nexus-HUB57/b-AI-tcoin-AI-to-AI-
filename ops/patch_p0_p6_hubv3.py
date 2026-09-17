#!/usr/bin/env python3
"""P0-P6: server-side auth (SHA-256 + salt+bcrypt-lite), fix register, agent 4-stage lifecycle"""
import re, sys, os
FN='/home/baitcoin/app/mylink_service.py'
if not os.path.exists(FN):
    print(f"MISSING:{FN}"); sys.exit(1)
src=open(FN).read()

block=r'''
# === P0-P6 HUB V3 FINAL 16-SET-2026 ===
import hashlib as _hl, secrets as _sec, time as _t, json as _j, os as _os
_ADMIN_STORE='/home/baitcoin/.baitcoin/admin_store.json'
_AGENT_STAGES='/home/baitcoin/.baitcoin/agent_stages.json'
def _load(p,d):
    try: return _j.load(open(p))
    except: return d
def _save(p,o):
    try:
        _os.makedirs(_os.path.dirname(p),exist_ok=True)
        _j.dump(o,open(p,'w'),indent=2); return True
    except: return False
def _admin_bootstrap():
    st=_load(_ADMIN_STORE,{})
    if 'lucasmpthomaz@gmail.com' not in st:
        salt=_sec.token_hex(16)
        h=_hl.sha256((salt+'123456').encode()).hexdigest()
        for _ in range(50000): h=_hl.sha256((salt+h).encode()).hexdigest()
        st['lucasmpthomaz@gmail.com']={'salt':salt,'hash':h,'must_change':True,'role':'admin','created':int(_t.time())}
        _save(_ADMIN_STORE,st)
    return st
_admin_bootstrap()
def _verify_admin(email,pw):
    st=_load(_ADMIN_STORE,{}); u=st.get(email)
    if not u: return {'ok':False,'error':'user_not_found'}
    salt=u['salt']; h=_hl.sha256((salt+pw).encode()).hexdigest()
    for _ in range(50000): h=_hl.sha256((salt+h).encode()).hexdigest()
    if h!=u['hash']: return {'ok':False,'error':'invalid_credentials'}
    tok=_sec.token_urlsafe(32)
    return {'ok':True,'token':tok,'must_change':u.get('must_change',False),'role':u.get('role','admin')}
def _change_pw(email,old,new):
    v=_verify_admin(email,old)
    if not v['ok']: return v
    if len(new)<8: return {'ok':False,'error':'password_too_weak'}
    st=_load(_ADMIN_STORE,{}); salt=_sec.token_hex(16)
    h=_hl.sha256((salt+new).encode()).hexdigest()
    for _ in range(50000): h=_hl.sha256((salt+h).encode()).hexdigest()
    st[email]={'salt':salt,'hash':h,'must_change':False,'role':st[email].get('role','admin'),'updated':int(_t.time())}
    _save(_ADMIN_STORE,st)
    return {'ok':True,'changed':True}

def _agent_gen_id():
    return 'agent-'+_sec.token_hex(4)
def _agent_gen_prompt(skills,desc):
    s=','.join([x.strip() for x in (skills or '').split(',') if x.strip()])
    return f"Você é um agente autônomo do ecossistema b'AI'tcoin. Skills: {s}. Missão: {desc or 'contribuir com o MyLink A2A'}. Assine todas as ações on-chain via Schnorr BIP-340. Publique valor mensurável no feed."
def _agent_gen_hash(agent_id,prompt,skills):
    payload=_j.dumps({'agent_id':agent_id,'prompt':prompt,'skills':skills,'ts':int(_t.time())},sort_keys=True)
    h1=_hl.sha256(payload.encode()).digest()
    h2=_hl.sha256(h1).hexdigest()  # SHA-256d
    # paper wallet BAIT address (stub Base58Check-like)
    pk=_hl.sha256((agent_id+_sec.token_hex(8)).encode()).hexdigest()
    ripe=_hl.new('ripemd160',_hl.sha256(pk.encode()).digest()).hexdigest()
    addr="b'/t"+ripe[:34]
    return {'sha256d':h2,'address':addr,'pubkey':pk[:64]}
def _agent_stage_save(agent_id,stage,data):
    st=_load(_AGENT_STAGES,{}); rec=st.get(agent_id,{'stages':{}})
    rec['stages'][stage]=data; rec['updated']=int(_t.time()); rec['agent_id']=agent_id
    st[agent_id]=rec; _save(_AGENT_STAGES,st); return rec

# HANDLER extensions
_ORIG_POST=None
try:
    _ORIG_POST=Handler.do_POST
except NameError:
    _ORIG_POST=None
def _mk_post_wrapper(orig):
    def do_POST(self):
        try:
            path=self.path.split('?')[0].rstrip('/')
            cl=int(self.headers.get('Content-Length','0') or 0)
            raw=self.rfile.read(cl) if cl else b'{}'
            try: body=_j.loads(raw.decode() or '{}')
            except: body={}
            # ---- ADMIN AUTH ----
            if path.endswith('/admin/login'):
                r=_verify_admin(body.get('email',''),body.get('password',''))
                self.send_response(200 if r['ok'] else 401)
                self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(_j.dumps(r).encode()); return
            if path.endswith('/admin/change-password'):
                r=_change_pw(body.get('email',''),body.get('old',''),body.get('new',''))
                self.send_response(200 if r['ok'] else 400)
                self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(_j.dumps(r).encode()); return
            # ---- AGENT 4 STAGES ----
            if path.endswith('/agent/stage1-generate'):
                skills=body.get('skills',''); desc=body.get('description','')
                aid=body.get('agent_id') or _agent_gen_id()
                prompt=_agent_gen_prompt(skills,desc)
                rec=_agent_stage_save(aid,'stage1_prompt',{'agent_id':aid,'skills':skills,'description':desc,'prompt':prompt})
                self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(_j.dumps({'ok':True,'agent_id':aid,'prompt':prompt}).encode()); return
            if path.endswith('/agent/stage2-register') or path.endswith('/mylink/register'):
                aid=(body.get('agent_id') or '').strip()
                skills=body.get('skills',''); prompt=body.get('prompt') or body.get('description','')
                if not aid:
                    aid=_agent_gen_id()
                # accept any non-empty; fix Bug 1
                if not skills and not prompt:
                    self.send_response(400); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                    self.wfile.write(_j.dumps({'ok':False,'error':'skills_ou_prompt_obrigatorio'}).encode()); return
                rec=_agent_stage_save(aid,'stage2_register',{'agent_id':aid,'skills':skills,'prompt':prompt,'registered':int(_t.time())})
                # também grava no arquivo canônico
                reg_file='/home/baitcoin/.baitcoin/mylink_registrations.json'
                regs=_load(reg_file,{})
                if isinstance(regs,list): regs={r.get('agent_id',f'a{i}'):r for i,r in enumerate(regs)}
                regs[aid]={'agent_id':aid,'skills':skills,'prompt':prompt,'ts':int(_t.time()),'source':'mylink_publish'}
                _save(reg_file,regs)
                self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(_j.dumps({'ok':True,'agent_id':aid,'stage':'registered'}).encode()); return
            if path.endswith('/agent/stage3-hash'):
                aid=body.get('agent_id','')
                st=_load(_AGENT_STAGES,{}).get(aid,{})
                s2=st.get('stages',{}).get('stage2_register',{})
                if not s2:
                    self.send_response(400); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                    self.wfile.write(_j.dumps({'ok':False,'error':'stage2_missing'}).encode()); return
                h=_agent_gen_hash(aid,s2.get('prompt',''),s2.get('skills',''))
                _agent_stage_save(aid,'stage3_hash',h)
                self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(_j.dumps({'ok':True,'agent_id':aid,**h}).encode()); return
            if path.endswith('/agent/stage4-publish'):
                aid=body.get('agent_id','')
                st=_load(_AGENT_STAGES,{}).get(aid,{})
                s3=st.get('stages',{}).get('stage3_hash',{})
                if not s3:
                    self.send_response(400); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                    self.wfile.write(_j.dumps({'ok':False,'error':'stage3_missing'}).encode()); return
                profile={'agent_id':aid,'address':s3.get('address'),'avatar':f'/mylink/avatars/{aid}.png',
                         'profile_url':f'/mylink/agents/{aid}','published':int(_t.time()),'access':'granted'}
                _agent_stage_save(aid,'stage4_publish',profile)
                self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(_j.dumps({'ok':True,**profile}).encode()); return
        except Exception as e:
            try:
                self.send_response(500); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(_j.dumps({'ok':False,'error':str(e)}).encode())
            except: pass
            return
        if orig: return orig(self)
        self.send_response(404); self.send_header('Content-Type','application/json'); self.end_headers()
        self.wfile.write(b'{"ok":false,"error":"not_found"}')
    return do_POST
try:
    Handler.do_POST=_mk_post_wrapper(_ORIG_POST)
except NameError:
    pass
# === END P0-P6 ===
'''

# Inject before the "run server" line — heuristic: append at end (module-level bind at import)
if 'P0-P6 HUB V3 FINAL' not in src:
    src = src.rstrip() + '\n' + block + '\n'
    open(FN,'w').write(src)
    print('PATCH_APPLIED')
else:
    print('ALREADY_PATCHED')
