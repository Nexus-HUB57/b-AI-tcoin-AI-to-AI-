import json, os
f="/home/baitcoin/.baitcoin/hub_v3_devlog.jsonl"
out="/var/www/mybait/mylink/hub/devlog.json"
en=[]
if os.path.exists(f):
    for ln in open(f).read().strip().splitlines()[-40:]:
        try: en.append(json.loads(ln))
        except Exception: pass
en=en[::-1]
os.makedirs(os.path.dirname(out),exist_ok=True)
json.dump({"ok":True,"live":True,"count":len(en),"entries":en},open(out,"w"),indent=2)
print("DEVLOG_JSON_OK",len(en))
