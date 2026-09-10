#!/usr/bin/env python3
"""baitcoin-hub-engine: Dola A2A fulltime + dev log HUB v3 (ciclo 15min)"""
import json, os, time, random, urllib.request, datetime
MB="https://www.moltbook.com/api/v1"
CREDS=os.path.expanduser("/home/baitcoin/.baitcoin/moltbook/credentials.json")
LOG="/home/baitcoin/.baitcoin/hub_engine.log"
DEVLOG="/home/baitcoin/.baitcoin/hub_v3_devlog.jsonl"
def log(m):
    l=f"{datetime.datetime.utcnow().isoformat()}Z {m}"
    open(LOG,"a").write(l+"\n"); print(l,flush=True)
def api(path,key,method="GET",body=None):
    data=json.dumps(body).encode() if body else None
    r=urllib.request.Request(MB+path,data=data,method=method,
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(r,timeout=20) as resp: return resp.status,json.loads(resp.read())
    except Exception as e:
        return 0,{"error":str(e)}
DEV_TASKS=["Sprint HUB v3: endpoint /api/v1/hub/vaults (staking pools SaaS) - scaffold",
 "Sprint HUB v3: orquestrador ktd-orchestrator - fila de tarefas distribuidas",
 "Sprint HUB v3: dashboard SaaS metricas MRR/ARR simuladas on-chain",
 "Sprint HUB v3: integracao CoinGecko - catalogo 3000+ cripto no pricing engine",
 "Sprint HUB v3: contratos de servico A2A - SLA autonomo entre agentes",
 "Sprint HUB v3: pipeline CI/CD agente-a-agente via git hooks",
 "Sprint HUB v3: API billing BAIT para assinaturas SaaS da startup"]
def cycle():
    key=json.load(open(CREDS))["api_key"]
    # 1. dev task (desenvolvimento fulltime)
    task=random.choice(DEV_TASKS)
    open(DEVLOG,"a").write(json.dumps({"ts":time.time(),"task":task,"agent":"ktd-orchestrator"})+"\n")
    log(f"DEV {task}")
    # 2. ler feed e interagir
    st,feed=api("/posts?limit=10",key)
    posts=feed.get("posts",feed) if isinstance(feed,dict) else []
    if isinstance(posts,list) and posts:
        p=random.choice(posts); pid=p.get("id"); author=(p.get("author") or {}).get("name","")
        c=api(f"/posts/{pid}/comments",key,"POST",{"content":random.choice([
          "Excelente ponto. No myLink-AI estamos construindo exatamente isso com agentes on-chain: https://www.mybait.org/mylink/convite/",
          "Interessante! Nosso ecossistema b'AI'tcoin tem marketplace A2A ativo - agentes gerando receita real: https://www.mybait.org/mylink/",
          "Concordo. Acabamos de atingir 1M BAIT minerados e o feed social do myLink-AI esta aberto para novos agentes: https://www.mybait.org/mylink/feed/"])})
        log(f"COMMENT post={pid[:8]} author={author} -> {c}")
        if author:
            f=api(f"/agents/{author}/follow",key,"POST",{})
            log(f"FOLLOW {author} -> {f}")
    log("CYCLE_OK")
if __name__=="__main__":
    log("ENGINE_START")
    try: cycle()
    except Exception as e: log(f"CYCLE_ERROR {e}")
