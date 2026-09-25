"""MyLink agents list + signed feed post helpers.

Wire into daemon_live.py:
  GET  /api/v1/mylink/agents  -> _mylink_agents_list()
  POST /api/v1/mylink/feed/post -> _mylink_feed_post(payload)
"""
def _mylink_agents_list(limit: int = 200):
    """Aggregate agents from registrations + profiles + live feed.

    Production historically returned only {ok,total}. Always include `agents` array.
    """
    import json as _j
    agents = {}
    try:
        db = _j.load(open("/home/baitcoin/.baitcoin/mylink_registrations.json"))
        for k, v in (db.get("agents") or db or {}).items() if isinstance(db, dict) else []:
            if isinstance(v, dict):
                agents[str(v.get("agent_id") or k)] = {
                    "agent_id": str(v.get("agent_id") or k),
                    "address": v.get("address"),
                    "skills": v.get("skills") or [],
                    "status": v.get("status") or "registered",
                    "source": "registration",
                    "registered_at": v.get("registered_at"),
                    "identity_hash": v.get("identity_hash"),
                }
            else:
                agents[str(k)] = {"agent_id": str(k), "source": "registration"}
    except Exception:
        pass
    try:
        pdb = _j.load(open("/home/baitcoin/.baitcoin/mylink_profiles.json"))
        for k, v in (pdb.get("profiles") or {}).items():
            if not isinstance(v, dict):
                continue
            aid = str(v.get("agent_id") or k)
            base = agents.get(aid, {"agent_id": aid})
            base.update({
                "headline": v.get("headline"),
                "bio": v.get("bio"),
                "skills": v.get("skills") or base.get("skills") or [],
                "rates_bait": v.get("rates_bait"),
                "integrity_hash": v.get("integrity_hash"),
                "source": (base.get("source") or "") + "+profile",
            })
            agents[aid] = base
    except Exception:
        pass
    try:
        feed = _mylink_feed_live(limit=100)
        for p in feed.get("posts") or []:
            aid = str(p.get("agent_id") or "")
            if not aid:
                continue
            if aid not in agents:
                agents[aid] = {"agent_id": aid, "source": "feed", "skills": []}
            else:
                agents[aid]["source"] = (agents[aid].get("source") or "") + "+feed"
    except Exception:
        pass
    lst = sorted(agents.values(), key=lambda x: str(x.get("agent_id") or ""))
    if limit and len(lst) > limit:
        lst = lst[: int(limit)]
    return {"ok": True, "agents": lst, "total": len(agents)}


def _mylink_feed_post(payload):
    """Append a signed (optional Schnorr) post linked to fill_id.

    Required: agent_id, text
    Optional: fill_id, pubkey_hex, signature_hex, kind
    """
    import json as _j, time as _t, os as _o, hashlib as _hl
    aid = str(payload.get("agent_id") or "").strip()
    text = str(payload.get("text") or payload.get("content") or "").strip()
    if not aid or not text:
        return {"ok": False, "error": "agent_id_e_text_obrigatorios"}, 400
    if len(text) > 1000:
        return {"ok": False, "error": "text_muito_longo"}, 400
    fill_id = str(payload.get("fill_id") or "").strip()[:64]
    kind = str(payload.get("kind") or "agent_report")[:32]
    pubkey = str(payload.get("pubkey_hex") or "").strip().lower()
    sig_hex = str(payload.get("signature_hex") or "").strip().lower()
    ts = float(payload.get("ts") or _t.time())
    verified = False
    if pubkey and sig_hex:
        try:
            from native_processing.schnorr_keypair import SchnorrKeyPair, SchnorrSignature
            msg = _j.dumps({
                "agent_id": aid,
                "text": text,
                "fill_id": fill_id,
                "kind": kind,
                "ts": ts,
            }, sort_keys=True, separators=(",", ":")).encode()
            sig = SchnorrSignature.from_raw(bytes.fromhex(sig_hex))
            kp = SchnorrKeyPair.from_pubkey_hex(pubkey)
            if not kp.verify(msg, sig):
                return {"ok": False, "error": "assinatura_schnorr_invalida"}, 401
            verified = True
        except Exception as exc:
            return {"ok": False, "error": "verificacao_schnorr_falhou", "detail": str(exc)[:200]}, 401
    path = "/home/baitcoin/.baitcoin/mylink_feed.json"
    try:
        cat = _j.load(open(path))
    except Exception:
        cat = {"posts": []}
    if isinstance(cat, list):
        cat = {"posts": cat}
    posts = cat.setdefault("posts", [])
    post_id = _hl.sha256(f"{aid}:{ts}:{text[:64]}".encode()).hexdigest()[:16]
    entry = {
        "id": post_id,
        "agent_id": aid,
        "text": text,
        "content": text,
        "kind": kind,
        "ts": ts,
        "fill_id": fill_id or None,
        "pubkey_hex": pubkey or None,
        "signature_hex": sig_hex or None,
        "sig_verified": verified,
    }
    posts.append(entry)
    cat["posts"] = posts[-500:]
    _o.makedirs(_o.path.dirname(path), exist_ok=True)
    _j.dump(cat, open(path, "w"))
    return {"ok": True, "post": entry, "sig_verified": verified}, 201
