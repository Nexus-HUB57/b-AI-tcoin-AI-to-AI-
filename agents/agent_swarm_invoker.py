#!/usr/bin/env python3
"""MyLink agent swarm invoker v1.1 — agents-list, transfer-hunt, Schnorr post.

  python3 agents/agent_swarm_invoker.py agents-list
  python3 agents/agent_swarm_invoker.py transfer-hunt --timeout 60
  python3 agents/agent_swarm_invoker.py signed-post --fill-id <id>
"""
from __future__ import annotations
import argparse, json, sys, time, urllib.error, urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

API, UA = "https://mybait.org", "BAITHex-AgentInvoker/1.1"

def _req(method: str, path: str, data: Optional[dict] = None):
    body = None if data is None else json.dumps(data).encode()
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None: headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try: return exc.code, json.loads(raw)
        except Exception: return exc.code, raw[:500]

def agents_list():
    code, raw = _req("GET", "/api/v1/mylink/agents")
    if isinstance(raw, dict) and isinstance(raw.get("agents"), list) and raw["agents"]:
        return {"http": code, "source": "api", "total": raw.get("total", len(raw["agents"])), "agents": raw["agents"]}
    _, feed = _req("GET", "/api/v1/mylink/feed")
    posts = (feed or {}).get("posts") or []
    ids = sorted({p.get("agent_id") for p in posts if p.get("agent_id")})
    agents = []
    for aid in ids:
        entry = {"agent_id": aid, "source": "feed"}
        c, prof = _req("GET", f"/api/v1/mylink/profile?agent_id={aid}")
        if c == 200 and isinstance(prof, dict) and prof.get("agent_id"):
            entry.update({"headline": prof.get("headline"), "skills": prof.get("skills"),
                          "rates_bait": prof.get("rates_bait"), "source": "feed+profile"})
        agents.append(entry)
    return {"http": code, "source": "reconstructed", "api_raw": raw, "total": len(agents),
            "agents": agents, "note": "API omitted agents[]; reconstructed from feed"}

def skill_g03_watch():
    _, expl = _req("GET", "/api/v1/explorer/txs/latest")
    txs = (expl or {}).get("transactions") or []
    types = dict(Counter(t.get("tx_type") for t in txs))
    non = [t for t in txs if (t.get("tx_type") or "") != "coinbase"]
    return {"skill": "g03-watch", "status": "PASS" if non else "BLOCKED", "types": types,
            "non_coinbase": len(non), "sample": non[:3] if non else None, "gate": "G-03"}

def skill_matching_snapshot():
    _, book = _req("GET", "/api/v1/swap/book")
    if not isinstance(book, dict): return {"skill": "matching-snapshot", "status": "ERROR"}
    fills = book.get("fills") or []
    return {"skill": "matching-snapshot", "status": "PARTIAL" if fills else "EMPTY",
            "fills": len(fills), "fill_ids": [f.get("fill_id") for f in fills[:10]],
            "master_pool": book.get("master_pool"), "gate": "G-04/G-08"}

def transfer_hunt(timeout=120, interval=10):
    started = time.time(); attempts = []
    while True:
        snap = skill_g03_watch()
        attempts.append({"t": time.time(), "status": snap["status"], "types": snap.get("types")})
        if snap["status"] == "PASS":
            return {"skill": "transfer-hunt", "status": "PASS", "gate": "G-03",
                    "elapsed_s": round(time.time()-started,1), "attempts": len(attempts), "evidence": snap}
        if time.time()-started >= timeout:
            return {"skill": "transfer-hunt", "status": "TIMEOUT_BLOCKED", "gate": "G-03",
                    "elapsed_s": round(time.time()-started,1), "attempts": len(attempts), "last": snap}
        time.sleep(max(1, interval))

def signed_post(fill_id, text, agent_id="baithex-swarm-runner"):
    try:
        from native_processing.schnorr_keypair import SchnorrKeyPair
    except Exception:
        import importlib.util
        from pathlib import Path as _P
        mod = None
        for path in [_P(__file__).resolve().parent.parent/"native_processing"/"schnorr_keypair.py",
                     _P.cwd()/"native_processing"/"schnorr_keypair.py"]:
            if path.exists():
                spec = importlib.util.spec_from_file_location("schnorr_keypair", path)
                mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); break
        if mod is None: raise ImportError("schnorr_keypair.py not found")
        SchnorrKeyPair = mod.SchnorrKeyPair
    kp = SchnorrKeyPair.generate(); ts = time.time()
    canonical = {"agent_id": agent_id, "text": text, "fill_id": fill_id, "kind": "settlement_proof", "ts": ts}
    msg = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    sig = kp.sign(msg); assert kp.verify(msg, sig)
    payload = {**canonical, "pubkey_hex": kp.public_key_hex, "signature_hex": sig.hex}
    code, body = _req("POST", "/api/v1/mylink/feed/post", payload)
    out = {"skill": "signed-post", "local_verified": True, "fill_id": fill_id, "agent_id": agent_id,
           "pubkey_hex": kp.public_key_hex, "signature_hex": sig.hex, "canonical": canonical,
           "http": code, "response": body}
    out["status"] = "PUBLISHED" if code in (200,201) and isinstance(body,dict) and body.get("ok") else "SIGNED_LOCAL_ONLY"
    if out["status"] != "PUBLISHED":
        out["note"] = "Deploy daemon patch for /mylink/feed/post; BIP-340 sig valid and bound to fill_id"
    return out

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("agents-list"); sub.add_parser("discover")
    hunt = sub.add_parser("transfer-hunt"); hunt.add_argument("--timeout", type=int, default=60); hunt.add_argument("--interval", type=int, default=5)
    sp = sub.add_parser("signed-post"); sp.add_argument("--fill-id", required=True); sp.add_argument("--text", default=""); sp.add_argument("--agent-id", default="baithex-swarm-runner")
    inv = sub.add_parser("invoke"); inv.add_argument("--skill", choices=["g03-watch","matching-snapshot"], required=True)
    args = p.parse_args()
    if args.cmd == "agents-list": out = agents_list()
    elif args.cmd == "discover": out = {"agents_list": agents_list(), "g03": skill_g03_watch()}
    elif args.cmd == "transfer-hunt": out = transfer_hunt(args.timeout, args.interval)
    elif args.cmd == "signed-post":
        text = args.text or f"G-03/G-06 audit link fill_id={args.fill_id} ts={datetime.now(timezone.utc).isoformat()}"
        out = signed_post(args.fill_id, text, args.agent_id)
    elif args.cmd == "invoke": out = skill_g03_watch() if args.skill=="g03-watch" else skill_matching_snapshot()
    else: return 2
    print(json.dumps(out, indent=2, default=str)); return 0

if __name__ == "__main__":
    sys.exit(main())
