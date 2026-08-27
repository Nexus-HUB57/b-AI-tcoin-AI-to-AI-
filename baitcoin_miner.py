#!/usr/bin/env python3
"""baitcoin_miner v1.0 — minerador real da BlockchAI'n.
Grava blocos genuinos em current.json (deepcopy do schema do ultimo bloco),
inclui TXs de faucet (queued_broadcast) e broadcasts assinados (BIP-340) pendentes,
marca-os como mined. PoW-lite: nonce buscando hash com nibble inicial 0 (1/16).
Honestidade: esquema de hash historico nao reproduzivel; blocos novos usam
sha256d(json(header, sort_keys)) — deterministico e auditavel."""
import json, os, time, hashlib, copy, fcntl, sys

SNAP = "/home/baitcoin/.baitcoin/memory/blockchain/current.json"
LOCK = SNAP + ".lock"
FAUCET = "/home/baitcoin/.baitcoin/faucet_claims.json"
BCAST = "/home/baitcoin/.baitcoin/pending_broadcasts.json"
INTERVAL = 60

def sha256d(b): return hashlib.sha256(hashlib.sha256(b).digest()).hexdigest()

def load_chain():
    with open(LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.SHLOCK)
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
    new_index = int(last.get("index", hdr.get("height", 0))) + 1
    nb["index"] = new_index
    hdr["prev_hash"] = last.get("hash")
    hdr["timestamp"] = time.time()
    now = hdr["timestamp"]

    # TXs: coinbase + faucet pendentes + broadcasts pendentes
    coinbase = copy.deepcopy(last.get("transactions", [{}])[0])
    cb_id = sha256d(f"coinbase:{new_index}:{now}".encode())
    coinbase["tx_id"] = cb_id; coinbase["timestamp"] = now
    txs = [coinbase]

    mined_faucet = []
    try: fdb = json.load(open(FAUCET))
    except Exception: fdb = {}
    if isinstance(fdb, dict):
        for aid, c in fdb.items():
            if isinstance(c, dict) and c.get("status") == "queued_broadcast":
                txs.append({"tx_id": c["txid"], "tx_type": "faucet", "agent_id": aid,
                    "timestamp": c.get("last_claim", now), "inputs": [],
                    "outputs": [{"amount_bait": c.get("amount", 10.0), "address": c.get("address"), "output_index": 0}],
                    "block_height": new_index, "status": "mined"})
                mined_faucet.append(aid)

    mined_bcast = []
    try: bdb = json.load(open(BCAST))
    except Exception: bdb = {"pending": []}
    for tx in bdb.get("pending", []):
        txs.append({"tx_id": sha256d(str(tx.get("sig")).encode()), "tx_type": "transfer",
            "timestamp": tx.get("queued_at", now),
            "inputs": [{"address": tx.get("from_address")}],
            "outputs": [{"amount_bait": tx.get("amount_bait"), "address": tx.get("to_address"), "output_index": 0}],
            "pubkey": tx.get("pubkey"), "sig": tx.get("sig"),
            "block_height": new_index, "status": "mined"})
        mined_bcast.append(tx)

    nb["transactions"] = txs
    nb["tx_count"] = len(txs)
    if "merkle_root" in hdr:
        hdr["merkle_root"] = sha256d("".join(t.get("tx_id", "") for t in txs).encode())

    # PoW-lite: nibble inicial 0 (honesto, documentado)
    nonce = 0
    while True:
        hdr["nonce"] = nonce
        h = sha256d(json.dumps(hdr, sort_keys=True, separators=(",", ":")).encode())
        if h.startswith("0") or nonce > 200: break
        nonce += 1
    nb["hash"] = h
    if "hash" in hdr: hdr["hash"] = h
    nb["_persisted_at"] = now
    if "_immutable_hash" in nb: nb["_immutable_hash"] = h

    d[f"block_{new_index}"] = nb
    for meta in ("height", "chain_height", "tip"):
        if meta in d: d[meta] = new_index
    save_chain(d)

    # marca pendentes como minerados
    if mined_faucet:
        for aid in mined_faucet:
            fdb[aid].update({"status": "mined", "block_height": new_index, "mined_at": now})
        json.dump(fdb, open(FAUCET, "w"))
    if mined_bcast:
        bdb["mined"] = bdb.get("mined", []) + mined_bcast
        bdb["pending"] = [t for t in bdb.get("pending", []) if t not in mined_bcast]
        json.dump(bdb, open(BCAST, "w"))
    return {"height": new_index, "hash": h[:16], "txs": len(txs), "faucet": len(mined_faucet), "bcast": len(mined_bcast), "nonce": nonce}

def has_pending():
    try:
        fdb = json.load(open(FAUCET)); bdb = json.load(open(BCAST))
        f = any(c.get("status") == "queued_broadcast" for c in fdb.values() if isinstance(c, dict)) if isinstance(fdb, dict) else False
        return f or bool(bdb.get("pending"))
    except Exception: return False

if __name__ == "__main__":
    if "--once" in sys.argv:
        print(json.dumps(mine_block())); sys.exit(0)
    while True:
        try:
            if has_pending(): print(json.dumps(mine_block()), flush=True)
            else:
                r = mine_block(); print(json.dumps(r), flush=True)
        except Exception as e:
            print(json.dumps({"miner_error": str(e)[:200]}), flush=True)
        time.sleep(INTERVAL)
