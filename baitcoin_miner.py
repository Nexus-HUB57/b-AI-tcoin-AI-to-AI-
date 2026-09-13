#!/usr/bin/env python3
"""baitcoin_miner v1.1 - produtor de blocos da BlockchAIn. Paths absolutos."""
import json, os, time, hashlib, copy, fcntl, sys
BASE = "/home/baitcoin/.baitcoin"
SNAP = BASE + "/memory/blockchain/current.json"
LOCK = BASE + "/memory/blockchain/.miner.lock"
FAUCET = BASE + "/faucet_claims.json"
BCAST = BASE + "/pending_broadcasts.json"
MYLINK_REG = BASE + "/mylink_registrations.json"
INTERVAL = 60
def sha256d(b): return hashlib.sha256(hashlib.sha256(b).digest()).hexdigest()
def load_chain():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_SH)
        d = json.load(open(SNAP))
    bk = sorted([k for k in d if k.startswith("block_")], key=lambda k: int(k.split("_")[1]))
    return d, bk
def save_chain(d):
    tmp = SNAP + ".tmp"
    with open(LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        json.dump(d, open(tmp, "w"))
        os.replace(tmp, SNAP)
def mine_block():
    d, bk = load_chain()
    if not bk: return None
    last = d[bk[-1]]
    nb = copy.deepcopy(last)
    hdr = nb.get("header", {})
    new_index = int(last.get("index", 0)) + 1
    nb["index"] = new_index
    hdr["prev_block_hash"] = last.get("hash")
    hdr["timestamp"] = time.time()
    now = hdr["timestamp"]
    coinbase = copy.deepcopy(last.get("transactions", [{}])[0])
    coinbase["tx_id"] = sha256d(("coinbase:%d:%f" % (new_index, now)).encode())
    coinbase["timestamp"] = now
    txs = [coinbase]
    mined_f = []
    try: fdb = json.load(open(FAUCET))
    except Exception: fdb = {}
    if isinstance(fdb, dict):
        for aid, c in fdb.items():
            if isinstance(c, dict) and c.get("status") == "queued_broadcast":
                txs.append({"tx_id": c["txid"], "tx_type": "faucet", "agent_id": aid,
                    "timestamp": c.get("last_claim", now), "inputs": [],
                    "outputs": [{"amount_bait": c.get("amount", 10.0), "address": c.get("address"), "output_index": 0}],
                    "block_height": new_index, "status": "mined"})
                mined_f.append(aid)
    mined_b = []
    try: bdb = json.load(open(BCAST))
    except Exception: bdb = {"pending": []}
    for tx in bdb.get("pending", []):
        txs.append({"tx_id": sha256d(str(tx.get("sig")).encode()), "tx_type": "transfer",
            "timestamp": tx.get("queued_at", now),
            "inputs": [{"address": tx.get("from_address")}],
            "outputs": [{"amount_bait": tx.get("amount_bait"), "address": tx.get("to_address"), "output_index": 0}],
            "pubkey": tx.get("pubkey"), "sig": tx.get("sig"),
            "block_height": new_index, "status": "mined"})
        mined_b.append(tx)
    mined_i = []
    try: idb = json.load(open(MYLINK_REG))
    except Exception: idb = {"agents": {}}
    for aid, a2 in idb.get("agents", {}).items():
        if a2.get("status") == "pending_onchain_anchor":
            txs.append({"tx_id": a2["identity_hash"], "tx_type": "identity",
                "agent_id": aid, "timestamp": a2.get("registered_at", now),
                "address": a2.get("address"), "block_height": new_index, "status": "mined",
                "inputs": [], "outputs": []})
            mined_i.append(aid)
    nb["transactions"] = txs
    nb["tx_count"] = len(txs)
    if "merkle_root" in hdr:
        hdr["merkle_root"] = sha256d("".join(t.get("tx_id","") for t in txs).encode())
    nonce = 0
    while True:
        hdr["nonce"] = nonce
        h = sha256d(json.dumps(hdr, sort_keys=True, separators=(",",":")).encode())
        if h.startswith("0") or nonce > 200: break
        nonce += 1
    nb["hash"] = h
    nb["_persisted_at"] = now
    nb["_immutable_hash"] = h
    d["block_%d" % new_index] = nb
    for meta in ("_chain_height", "height", "chain_height"):
        if meta in d: d[meta] = new_index
    if "_last_block_hash" in d: d["_last_block_hash"] = h
    save_chain(d)
    if mined_f:
        for aid in mined_f: fdb[aid].update({"status":"mined","block_height":new_index,"mined_at":now})
        json.dump(fdb, open(FAUCET, "w"))
    if mined_b:
        bdb["mined"] = bdb.get("mined", []) + mined_b
        ids = {id(t) for t in mined_b}
        bdb["pending"] = [t for t in bdb.get("pending", []) if id(t) not in ids]
        json.dump(bdb, open(BCAST, "w"))
    if mined_i:
        for aid in mined_i: idb["agents"][aid]["status"] = "anchored_onchain"
        json.dump(idb, open(MYLINK_REG, "w"))
    return {"height": new_index, "hash": h[:16], "txs": len(txs), "faucet": len(mined_f), "bcast": len(mined_b), "nonce": nonce}
def has_pending():
    try:
        fdb = json.load(open(FAUCET)); bdb = json.load(open(BCAST))
        f = any(c.get("status")=="queued_broadcast" for c in fdb.values() if isinstance(c,dict)) if isinstance(fdb,dict) else False
        return f or bool(bdb.get("pending"))
    except Exception: return False
if __name__ == "__main__":
    if "--once" in sys.argv:
        print(json.dumps(mine_block())); sys.exit(0)
    while True:
        try:
            r = mine_block()
            if r: print(json.dumps(r), flush=True)
        except Exception as e:
            print(json.dumps({"miner_error": str(e)[:200]}), flush=True)
        time.sleep(INTERVAL)
