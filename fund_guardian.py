#!/usr/bin/env python3
"""guardian.py — Agente Guardiao do Fundo MyLink (watch-only).
Monitora custodia + whale addresses; alerta em qualquer movimentacao; nunca toca em chaves."""
import json, urllib.request, os, time, datetime
STATE="/home/baitcoin/.baitcoin/fund/guardian_state.json"
WATCH={
 "custodia":"bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s",
 "whale_principal":"18iJBAX3BRVZT2i5vkh73TUM9UvAN1ASE3",
 "whale_2":"1CvtJkfyErRDdmrv5SSv3tHVZBxt26GJV7",
 "whale_3":"19QbjYWEQvr9K44VUi2skAM2w6B49GbsCQ",
 "whale_4":"3PdKaWwshFBWg6vAauToecqEAFtsuzyxGV",
}
BASES=["https://mempool.space/api","https://blockstream.info/api"]
def get(a):
    for b in BASES:
        try:
            with urllib.request.urlopen(f"{b}/address/{a}",timeout=20) as r:
                d=json.loads(r.read()); cs,ms=d["chain_stats"],d["mempool_stats"]
                return {"sat":(cs["funded_txo_sum"]-cs["spent_txo_sum"])+(ms["funded_txo_sum"]-ms["spent_txo_sum"]),
                        "tx":cs["tx_count"]+ms["tx_count"],"via":b}
        except Exception: continue
    return None
def load():
    try: return json.load(open(STATE))
    except Exception: return {}
def main():
    prev=load(); now={}; alerts=[]
    for name,addr in WATCH.items():
        d=get(addr)
        if not d: alerts.append(f"[ERRO] sem resposta p/ {name}"); continue
        now[name]={"addr":addr,**d}
        p=prev.get(name)
        if p and (p["sat"]!=d["sat"] or p["tx"]!=d["tx"]):
            delta=(d["sat"]-p["sat"])/1e8
            alerts.append(f"[ALERTA] {name} ({addr[:14]}...) mudou: {delta:+.8f} BTC | tx {p['tx']}->{d['tx']}")
    now["_ts"]=datetime.datetime.utcnow().isoformat()+"Z"
    json.dump(now,open(STATE,"w"),indent=2)
    ts=now["_ts"]
    print(f"[{ts}] GUARDIAN_SCAN")
    for n,v in now.items():
        if n=="_ts": continue
        print(f"  {n:16s} {v['addr'][:20]}... {v['sat']/1e8:.8f} BTC ({v['tx']} tx) via {v['via']}")
    print("ALERTAS:", alerts if alerts else "nenhum — estado estavel")
if __name__=="__main__": main()
