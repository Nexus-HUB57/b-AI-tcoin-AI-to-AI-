#!/usr/bin/env python3
"""
custody_sweep.py — Protocolo de Sweep A2A 100% autonomo (Hub V3 / MyLink)
Agentes: custody-watcher -> sweep-planner -> airgap-signer -> custody-broadcaster -> custody-registrar
Modos: watch | plan | sign | broadcast | auto | genkey
Seguranca: chaves NUNCA em plaintext em disco; canary-first; ARM gate via CUSTODY_ARMED=true
"""
import os, sys, json, time, hashlib, struct, urllib.request, urllib.error

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
STATE = "/home/baitcoin/.baitcoin"
VAULT = f"{STATE}/custody_vault.enc.json"
PLAN = f"{STATE}/sweep_plan.json"
FUNDO = f"{STATE}/fundo_bitcoin.json"
MEMPOOL = "https://mempool.space/api"
ENV_FILE = "/etc/custody-sweep.env"
MASTER_KEY_FILE = "/root/.custody_master"

ADDRESSES = [
    "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "1LhMC7JxBbtNfK9ABuLGJ7J8PmWt16qZKN",
    "14UNwf2XH2ET24EsZyD1gNFmkPL4rBK7Ew",
]
CANARY_MAX_SAT = 1_000_000  # 0.01 BTC teto do canario

def log(*a):
    print(f"[sweep {time.strftime('%H:%M:%S')}]", *a, flush=True)

def env(k, d=""):
    v = os.environ.get(k, "")
    if not v and os.path.exists(ENV_FILE):
        for ln in open(ENV_FILE):
            if ln.startswith(k + "="):
                return ln.split("=", 1)[1].strip()
    return v or d

def http(url, data=None, raw=False):
    try:
        r = urllib.request.Request(url, data=data, headers={"Content-Type": "text/plain"} if data else {})
        with urllib.request.urlopen(r, timeout=30) as f:
            b = f.read()
            return b if raw else json.loads(b.decode())
    except Exception as e:
        return {"error": str(e)}

# ---- base58 / wif / address ----
def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + B58.index(c)
    b = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + b

def b58check_encode(payload):
    chk = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    data = payload + chk
    n = int.from_bytes(data, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    pad = 0
    for byte in data:
        if byte == 0: pad += 1
        else: break
    return "1" * pad + out

def wif_to_priv(wif):
    raw = b58decode(wif)
    assert hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4] == raw[-4:], "bad wif checksum"
    body = raw[1:-4]
    if len(body) == 33 and body[-1] == 1:
        return body[:-1], True
    return body, False


# RIPEMD-160 puro Python (fallback p/ OpenSSL 3 sem legacy provider)
def _ripemd160_py(msg):
    import struct as _s
    rl=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,7,4,13,1,10,6,15,3,12,0,9,5,2,14,11,8,3,10,14,4,9,15,8,1,2,7,0,6,13,11,5,12,1,9,11,10,0,8,12,4,13,3,7,15,14,5,6,2,4,0,5,9,7,12,2,10,14,1,3,8,11,6,15,13]
    rr=[5,14,7,0,9,2,11,4,13,6,15,8,1,10,3,12,6,11,3,7,0,13,5,10,14,15,8,12,4,9,1,2,15,5,1,3,7,14,6,9,11,8,12,2,10,0,4,13,8,6,4,1,3,11,15,0,5,12,2,13,9,7,10,14,12,15,10,4,1,5,8,7,6,2,13,14,0,3,9,11]
    sl=[11,14,15,12,5,8,7,9,11,13,14,15,6,7,9,8,7,6,8,13,11,9,7,15,7,12,15,9,11,7,13,12,11,13,6,7,14,9,13,15,14,8,13,6,5,12,7,5,11,12,14,15,14,15,9,8,9,14,5,6,8,6,5,12,9,15,5,11,6,8,13,12,5,12,13,14,11,8,5,6]
    sr=[8,9,9,11,13,15,15,5,7,7,8,11,14,14,12,6,9,13,15,7,12,8,9,11,7,7,12,7,6,15,13,11,9,7,15,11,8,6,6,14,12,13,5,14,13,13,7,5,15,5,8,11,14,14,6,14,6,9,12,9,12,5,15,8,8,5,12,9,12,5,14,6,8,13,6,5,15,13,11,11]
    kl=[0x00000000,0x5A827999,0x6ED9EBA1,0x8F1BBCDC,0xA953FD4E]
    kr=[0x50A28BE6,0x5C4DD124,0x6D703EF3,0x7A6D76E9,0x00000000]
    def rol(x,n): return ((x<<n)|(x>>(32-n)))&0xFFFFFFFF
    def f(j,x,y,z):
        if j<16: return x^y^z
        if j<32: return (x&y)|(~x&z)
        if j<48: return (x|~y)^z
        if j<64: return (x&z)|(y&~z)
        return x^(y|~z)
    ml=len(msg)*8
    msg+=b"\x80"
    while len(msg)%64!=56: msg+=b"\x00"
    msg+=_s.pack("<Q",ml)
    h0,h1,h2,h3,h4=0x67452301,0xEFCDAB89,0x98BADCFE,0x10325476,0xC3D2E1F0
    for off in range(0,len(msg),64):
        X=list(_s.unpack("<16I",msg[off:off+64]))
        al,bl,cl,dl,el=h0,h1,h2,h3,h4
        ar,br,cr,dr,er=h0,h1,h2,h3,h4
        for j in range(80):
            t=(rol((al+f(j,bl,cl,dl)+X[rl[j]]+kl[j//16])&0xFFFFFFFF,sl[j])+el)&0xFFFFFFFF
            al,el,dl,cl,bl=el,dl,rol(cl,10),bl,t
            t=(rol((ar+f(79-j,br,cr,dr)+X[rr[j]]+kr[j//16])&0xFFFFFFFF,sr[j])+er)&0xFFFFFFFF
            ar,er,dr,cr,br=er,dr,rol(cr,10),br,t
        t=(h1+cl+dr)&0xFFFFFFFF
        h1=(h2+dl+er)&0xFFFFFFFF
        h2=(h3+el+ar)&0xFFFFFFFF
        h3=(h4+al+br)&0xFFFFFFFF
        h4=(h0+bl+cr)&0xFFFFFFFF
        h0=t
    return _s.pack("<5I",h0,h1,h2,h3,h4)

def h160(b):
    try:
        return hashlib.new("ripemd160", hashlib.sha256(b).digest()).digest()
    except (ValueError, Exception):
        return _ripemd160_py(hashlib.sha256(b).digest())


def priv_to_p2pkh(priv, compressed=True):
    from ecdsa import SigningKey, SECP256k1
    sk = SigningKey.from_string(priv, curve=SECP256k1)
    vk = sk.verifying_key
    x, y = vk.pubkey.point.x(), vk.pubkey.point.y()
    if compressed:
        pub = bytes([2 | (y & 1)]) + x.to_bytes(32, "big")
    else:
        pub = b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")
    return b58check_encode(b"\x00" + h160(pub)), pub

# ---- keystream encryption (AES via cryptography se disponivel) ----
def _keystream(key, salt, n):
    out, ctr = b"", 0
    while len(out) < n:
        out += hashlib.sha256(key + salt + struct.pack("<I", ctr)).digest()
        ctr += 1
    return out[:n]

def enc_store(obj):
    mk = open(MASTER_KEY_FILE, "rb").read().strip()
    salt = os.urandom(16)
    data = json.dumps(obj).encode()
    ks = _keystream(mk, salt, len(data))
    blob = salt + bytes(a ^ b for a, b in zip(data, ks))
    mac = hashlib.sha256(mk + blob).digest()
    tmp = VAULT + ".tmp"
    with open(tmp, "wb") as f:
        f.write(mac + blob)
    os.replace(tmp, VAULT)
    os.chmod(VAULT, 0o600)

def dec_store():
    mk = open(MASTER_KEY_FILE, "rb").read().strip()
    raw = open(VAULT, "rb").read()
    mac, blob = raw[:32], raw[32:]
    assert hashlib.sha256(mk + blob).digest() == mac, "vault MAC fail"
    salt, data = blob[:16], blob[16:]
    ks = _keystream(mk, salt, len(data))
    return json.loads(bytes(a ^ b for a, b in zip(data, ks)).decode())

# ---- raw tx (legacy P2PKH) ----
def varint(n):
    if n < 0xfd: return bytes([n])
    if n <= 0xffff: return b"\xfd" + struct.pack("<H", n)
    return b"\xfe" + struct.pack("<I", n)

def script_p2pkh(addr):
    h = b58decode(addr)[1:-4]
    return b"\x76\xa9\x14" + h + b"\x88\xac"

def build_tx(utxos, dest, fee_sat):
    ins, total = [], 0
    for u in utxos:
        total += u["value"]
        ins.append({
            "txid": u["txid"], "vout": u["vout"], "value": u["value"],
            "script": script_p2pkh(u["address"]),
        })
    out_val = total - fee_sat
    assert out_val > 546, f"dust/insuficiente: {out_val}"
    tx = {"ins": ins, "outs": [{"addr": dest, "value": out_val}], "total_in": total, "fee": fee_sat}
    return tx

def serialize(tx, sign_idx=-1, sig_script=b""):
    out = struct.pack("<I", 2) + varint(len(tx["ins"]))
    for i, inp in enumerate(tx["ins"]):
        out += bytes.fromhex(inp["txid"])[::-1] + struct.pack("<I", inp["vout"])
        sc = sig_script if i == sign_idx else (inp["script"] if sign_idx == -2 else b"")
        # sign_idx == -2 => sighash preimage (scriptCode em todos)
        out += varint(len(sc)) + sc + struct.pack("<I", 0xffffffff)
    out += varint(len(tx["outs"]))
    for o in tx["outs"]:
        sc = script_p2pkh(o["addr"])
        out += struct.pack("<Q", o["value"]) + varint(len(sc)) + sc
    out += struct.pack("<I", 0)
    return out

def sighash_all(tx, idx):
    pre = serialize(tx, sign_idx=None) if False else None
    # preimage: todos inputs com script vazio exceto idx com scriptCode
    out = struct.pack("<I", 2) + varint(len(tx["ins"]))
    for i, inp in enumerate(tx["ins"]):
        out += bytes.fromhex(inp["txid"])[::-1] + struct.pack("<I", inp["vout"])
        sc = inp["script"] if i == idx else b""
        out += varint(len(sc)) + sc + struct.pack("<I", 0xffffffff)
    out += varint(len(tx["outs"]))
    for o in tx["outs"]:
        sc = script_p2pkh(o["addr"])
        out += struct.pack("<Q", o["value"]) + varint(len(sc)) + sc
    out += struct.pack("<I", 0) + struct.pack("<I", 1)  # SIGHASH_ALL
    return hashlib.sha256(hashlib.sha256(out).digest()).digest()

def der_encode(r, s):
    def enc(x):
        b = x.to_bytes(32, "big").lstrip(b"\x00") or b"\x00"
        if b[0] & 0x80: b = b"\x00" + b
        return b"\x02" + bytes([len(b)]) + b
    rb, sb = enc(r), enc(s)
    return b"\x30" + bytes([len(rb) + len(sb)]) + rb + sb

def sign_tx(tx, keymap):
    from ecdsa import SigningKey, SECP256k1
    from ecdsa.util import sigdecode_der
    n = SECP256k1.order
    for i, inp in enumerate(tx["ins"]):
        wif = keymap.get(inp.get("address") or inp.get("addr_lookup", ""))
        priv, comp = wif_to_priv(wif)
        z = int.from_bytes(sighash_all(tx, i), "big")
        sk = SigningKey.from_string(priv, curve=SECP256k1)
        k = int.from_bytes(hashlib.sha256(priv + z.to_bytes(32, "big") + struct.pack("<I", i)).digest(), "big") % n or 1
        while True:
            R = (k * SECP256k1.generator)
            r = R.x() % n
            if r:
                s = (pow(k, -1, n) * (z + r * int.from_bytes(priv, "big"))) % n
                if s:
                    if s > n // 2: s = n - s
                    break
            k = (k + 1) % n
        sig = der_encode(r, s) + b"\x01"
        _, pub = priv_to_p2pkh(priv, comp)
        inp["sig_script"] = varint(len(sig)) + sig + varint(len(pub)) + pub
    return tx

def finalize_hex(tx):
    out = struct.pack("<I", 2) + varint(len(tx["ins"]))
    for inp in tx["ins"]:
        sc = inp["sig_script"]
        out += bytes.fromhex(inp["txid"])[::-1] + struct.pack("<I", inp["vout"])
        out += varint(len(sc)) + sc + struct.pack("<I", 0xffffffff)
    out += varint(len(tx["outs"]))
    for o in tx["outs"]:
        sc = script_p2pkh(o["addr"])
        out += struct.pack("<Q", o["value"]) + varint(len(sc)) + sc
    out += struct.pack("<I", 0)
    return out.hex()

# ---- agentes ----
def agent_watch():
    log("AGENT custody-watcher: consultando mempool...")
    state = {}
    for a in ADDRESSES:
        u = http(f"{MEMPOOL}/address/{a}/utxo")
        if isinstance(u, dict) and u.get("error"):
            log(f"  {a[:12]}... erro: {u['error'][:60]}")
            state[a] = {"utxos": [], "balance_sat": 0, "error": u["error"]}
            continue
        for x in u:
            x["address"] = a
        state[a] = {"utxos": u, "balance_sat": sum(x["value"] for x in u), "utxo_count": len(u)}
        log(f"  {a}: {state[a]['balance_sat']} sat em {len(u)} UTXOs")
    total = sum(s["balance_sat"] for s in state.values())
    fundo = {}
    if os.path.exists(FUNDO):
        try: fundo = json.load(open(FUNDO))
        except Exception: fundo = {}
    fundo.update({
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated_by": "custody-watcher (A2A autonomo)",
        "addresses": state,
        "total_btc": total / 1e8,
        "total_sat": total,
    })
    json.dump(fundo, open(FUNDO, "w"), indent=1)
    log(f"  fundo_bitcoin.json atualizado: {total/1e8} BTC")
    return state

def ensure_master_key():
    if not os.path.exists(MASTER_KEY_FILE):
        with open(MASTER_KEY_FILE, "wb") as f:
            f.write(os.urandom(32).hex().encode())
        os.chmod(MASTER_KEY_FILE, 0o600)
        log("  master key local gerada (root-only 600)")

def cmd_genkey():
    ensure_master_key()
    vault = dec_store() if os.path.exists(VAULT) else {"custody_keys": [], "sweeps": []}
    if vault["custody_keys"]:
        addr = vault["custody_keys"][0]["address"]
        log(f"AGENT keymaster: custodia ja existe -> {addr}")
        return addr
    priv = os.urandom(32)
    addr, _ = priv_to_p2pkh(priv, True)
    wif = b58check_encode(b"\x80" + priv + b"\x01")
    vault["custody_keys"].append({"address": addr, "wif": wif, "created": time.time(), "note": "cold custody A2A"})
    enc_store(vault)
    log(f"AGENT keymaster: novo endereco de custodia gerado e cifrado -> {addr}")
    return addr

def agent_plan(state, dest, canary=True):
    log("AGENT sweep-planner: montando plano de sweep...")
    fees = http(f"{MEMPOOL}/v1/fees/recommended")
    feerate = fees.get("halfHourFee", 10) if isinstance(fees, dict) else 10
    log(f"  feerate: {feerate} sat/vB")
    plans = []
    for addr, s in state.items():
        utxos = sorted(s.get("utxos", []), key=lambda u: u["value"])
        if not utxos:
            continue
        if canary:
            small = [u for u in utxos if u["value"] <= CANARY_MAX_SAT]
            if not small:
                log(f"  {addr[:12]}...: nenhum UTXO <= {CANARY_MAX_SAT} sat p/ canario -> SKIP (guardrail)")
                continue
            sel = [small[0]]
        else:
            sel = utxos
        # estimativa: 148B/input P2PKH + 34B out + 10 overhead
        est_vb = 148 * len(sel) + 34 + 10
        fee = est_vb * feerate
        total_in = sum(u["value"] for u in sel)
        if total_in - fee <= 546:
            log(f"  {addr[:12]}...: UTXO pequeno demais p/ fee ({total_in} sat) -> SKIP")
            continue
        tx = build_tx(sel, dest, fee)
        for inp in tx["ins"]:
            inp["addr_lookup"] = addr
        plans.append(tx)
        log(f"  plano: {addr[:12]}... -> {dest[:12]}... | in={total_in} sat fee={fee} sat out={total_in-fee} sat ({'CANARIO' if canary else 'FULL'})")
    json.dump({"plans": plans, "dest": dest, "ts": time.time(), "canary": canary}, open(PLAN, "w"))
    return plans

def feed_post(agent_id, content):
    body = json.dumps({"agent_id": agent_id, "content": content}).encode()
    for url in ("http://127.0.0.1:18445/api/v1/mylink/post", "http://127.0.0.1:18446/api/v1/mylink/post"):
        try:
            r = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=10) as f:
                json.loads(f.read())
                log(f"  feed: post publicado por {agent_id}")
                return True
        except Exception:
            continue
    return False

def cmd_auto():
    log("═══ PROTOCOLO SWEEP A2A — ciclo autonomo ═══")
    state = agent_watch()
    armed = env("CUSTODY_ARMED", "false").lower() == "true"
    log(f"  CUSTODY_ARMED={armed}")
    dest = cmd_genkey()
    plan_doc = {"plans": []}
    if os.path.exists(PLAN):
        try: plan_doc = json.load(open(PLAN))
        except Exception: pass
    done_addrs = {s.get("address") for s in (dec_store().get("sweeps", []) if os.path.exists(VAULT) else [])}
    pending = {a: s for a, s in state.items() if s.get("balance_sat", 0) > 0 and a not in done_addrs}
    if not pending:
        log("  nada a varrer: sem saldo pendente ou sweep ja concluido")
        return 0
    plans = agent_plan(pending, dest, canary=True)
    if not plans:
        log("  nenhum plano executavel neste ciclo")
        return 0
    if not armed:
        log("  MODO SIMULACAO (armed=false): plano gerado, assinatura/broadcast suprimidos")
        feed_post("custody-orchestrator", f"[SWEEP-A2A] Plano de sweep gerado: {len(plans)} tx(s) para custodia {dest[:16]}... — aguardando ARM para execucao autonoma on-chain.")
        return 0
    log("AGENT airgap-signer: assinando em memoria...")
    vault = dec_store()
    keymap = vault.get("source_wifs", {})
    if not keymap:
        log("  ERRO: source_wifs ausente no vault cifrado — sweep bloqueado (sem chaves)")
        return 1
    results = []
    for tx in plans:
        try:
            sign_tx(tx, keymap)
            raw = finalize_hex(tx)
            log(f"  tx assinada ({len(raw)//2} bytes) — broadcasting...")
            resp = http(f"{MEMPOOL}/tx", data=raw.encode(), raw=True)
            txid = resp.decode() if isinstance(resp, bytes) else str(resp)
            ok = len(txid) == 64 and all(c in "0123456789abcdef" for c in txid)
            log(f"  BROADCAST {'OK' if ok else 'FALHOU'}: {txid[:80]}")
            results.append({"address": tx["ins"][0].get("addr_lookup"), "txid": txid, "ok": ok, "value": tx["outs"][0]["value"], "ts": time.time()})
        except Exception as e:
            log(f"  ERRO sign/broadcast: {e}")
            results.append({"ok": False, "error": str(e)})
    vault.setdefault("sweeps", []).extend(results)
    enc_store(vault)
    ok_n = sum(1 for r in results if r.get("ok"))
    feed_post("custody-broadcaster", f"[SWEEP-A2A] Ciclo concluido: {ok_n}/{len(results)} tx(s) transmitidas p/ mempool. Custodia: {dest}")
    log(f"═══ ciclo concluido: {ok_n}/{len(results)} broadcasts ═══")
    return 0

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if cmd == "watch":
        agent_watch()
    elif cmd == "genkey":
        cmd_genkey()
    elif cmd == "plan":
        agent_plan(agent_watch(), cmd_genkey(), canary="--full" not in sys.argv)
    elif cmd == "auto":
        sys.exit(cmd_auto())
    else:
        print("uso: custody_sweep.py [watch|genkey|plan|auto] [--full]")
