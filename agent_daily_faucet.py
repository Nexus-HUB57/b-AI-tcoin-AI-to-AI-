#!/usr/bin/env python3
# Cron diario: faucet 10 BAIT + onboard AI Store (100 BAIT + 3 tools) para todos os agentes myLink
import json, urllib.request, sys

def post(path, payload):
    try:
        req = urllib.request.Request("http://127.0.0.1:18445" + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=10).read().decode()[:140]
    except Exception as e:
        return "ERR " + str(e)[:80]

regs = json.load(open("/home/baitcoin/.baitcoin/mylink_registrations.json"))
agents = regs.get("agents", regs)
n = 0
for aid, a in (agents.items() if isinstance(agents, dict) else []):
    addr = (a or {}).get("address", "")
    if not addr:
        continue
    n += 1
    r1 = post("/api/v1/faucet/claim", {"agent_id": aid, "address": addr})
    r2 = post("/api/v1/aistore/onboard", {"agent_id": aid, "address": addr})
    print(aid, "| faucet:", r1, "| onboard:", r2)
print("AGENTES_PROCESSADOS:", n)

try:
    b = json.load(open("/home/baitcoin/.baitcoin/balances.json"))
    print("COM_SALDO:", len(b))
    for k, v in list(b.items())[:12]:
        print("  ", k[:36], v, "BAIT")
except Exception as e:
    print("balances:", e)
