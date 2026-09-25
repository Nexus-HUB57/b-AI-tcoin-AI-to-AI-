#!/usr/bin/env python3
"""MyLink agent swarm invoker — discover, register, run read-only skills.

Does NOT hold keys, broadcast, or enable settlement.
Skills run locally against public mybait.org APIs.

  python3 agents/agent_swarm_invoker.py discover
  python3 agents/agent_swarm_invoker.py register --agent-id baithex-dev --skills g03-watch,parity
  python3 agents/agent_swarm_invoker.py invoke --skill g03-watch
  python3 agents/agent_swarm_invoker.py run-swarm
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

API = "https://mybait.org"
UA = "BAITHex-AgentInvoker/1.0"


def _req(method: str, path: str, data: Optional[dict] = None) -> tuple[int, Any]:
    body = None if data is None else json.dumps(data).encode()
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw[:500]
        return exc.code, parsed


def discover() -> dict[str, Any]:
    code, feed = _req("GET", "/api/v1/mylink/feed")
    posts = feed.get("posts") if isinstance(feed, dict) else []
    agents = Counter(p.get("agent_id") for p in (posts or []))
    _, mylink = _req("GET", "/api/v1/mylink/agents")
    _, status = _req("GET", "/api/v1/status")
    _, platform = _req("GET", "/api/v1/platform")
    known = [
        "dola-ceo",
        "ktd-orchestrator",
        "chimera7-defi",
        "settlement-auditor",
        "chainlink-native-oracle",
        "opal-guardian-feed",
        "por-signer-coordinator",
        "roadmap-tl-dr",
    ]
    profiles = {}
    for aid in known:
        c, prof = _req("GET", f"/api/v1/mylink/profile?agent_id={aid}")
        if c == 200 and isinstance(prof, dict):
            profiles[aid] = {
                "headline": prof.get("headline"),
                "skills": prof.get("skills"),
                "rates_bait": prof.get("rates_bait"),
            }
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "feed_http": code,
        "feed_posts": len(posts or []),
        "feed_agents": dict(agents.most_common(25)),
        "mylink_agents_total": (mylink or {}).get("total") if isinstance(mylink, dict) else None,
        "chain_agents_registered": (status or {}).get("agents_registered") if isinstance(status, dict) else None,
        "height": (status or {}).get("chain_height") if isinstance(status, dict) else None,
        "platform": platform if isinstance(platform, dict) else None,
        "profiles": profiles,
        "sample_posts": [
            {
                "agent_id": p.get("agent_id"),
                "kind": p.get("kind"),
                "text": (p.get("text") or "")[:120],
            }
            for p in (posts or [])[:5]
        ],
    }


def register(agent_id: str, skills: list[str], prompt: str, name: str = "") -> dict[str, Any]:
    payload = {"agent_id": agent_id, "skills": skills, "prompt": prompt}
    if name:
        payload["name"] = name
    code, body = _req("POST", "/api/v1/mylink/register", payload)
    return {"http": code, "response": body, "payload": payload}


def skill_g03_watch() -> dict[str, Any]:
    _, expl = _req("GET", "/api/v1/explorer/txs/latest")
    txs = (expl or {}).get("transactions") or []
    types = dict(Counter(t.get("tx_type") for t in txs))
    non = [t for t in txs if (t.get("tx_type") or "") != "coinbase"]
    return {
        "skill": "g03-watch",
        "status": "PASS" if non else "BLOCKED",
        "types": types,
        "non_coinbase": len(non),
        "sample_txid": (non[0].get("tx_id") if non else (txs[0].get("tx_id") if txs else None)),
        "gate": "G-03",
    }


def skill_parity_check() -> dict[str, Any]:
    _, st = _req("GET", "/api/v1/status")
    bait = ((st or {}).get("oracle") or {}).get("prices", {}).get("BTC")
    feed = "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c"
    rpc = "https://rpc.mevblocker.io"

    def eth_call(data: str) -> str:
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
             "params": [{"to": feed, "data": data}, "latest"]}
        ).encode()
        req = urllib.request.Request(
            rpc, data=payload,
            headers={"Content-Type": "application/json", "User-Agent": UA},
            method="POST",
        )
        return json.loads(urllib.request.urlopen(req, timeout=12).read())["result"]

    try:
        dec = int(eth_call("0x313ce567"), 16)
        raw = eth_call("0xfeaf968c")[2:]
        words = [raw[i : i + 64] for i in range(0, 320, 64)]
        ans = int(words[1], 16)
        if ans >= 2**255:
            ans -= 2**256
        price = ans / (10**dec)
        bps = abs(price - bait) / bait * 10_000 if bait else None
        return {
            "skill": "parity-check",
            "status": "OK" if bps is not None and bps < 150 else "WARN",
            "chainlink_btc": price,
            "bait_btc": bait,
            "diff_bps": round(bps, 2) if bps is not None else None,
            "gate": "G-09",
        }
    except Exception as exc:
        return {"skill": "parity-check", "status": "ERROR", "error": str(exc)}


def skill_matching_snapshot() -> dict[str, Any]:
    _, book = _req("GET", "/api/v1/swap/book")
    if not isinstance(book, dict):
        return {"skill": "matching-snapshot", "status": "ERROR", "error": book}
    fills = book.get("fills") or []
    offers = book.get("offers") or []
    pool = book.get("master_pool") or {}
    return {
        "skill": "matching-snapshot",
        "status": "PARTIAL" if fills else "EMPTY",
        "offers": len(offers),
        "fills": len(fills),
        "master_pool": pool,
        "custody_btc": book.get("custody_btc"),
        "gate": "G-04/G-08",
    }


SKILLS = {
    "g03-watch": skill_g03_watch,
    "parity-check": skill_parity_check,
    "matching-snapshot": skill_matching_snapshot,
}


def main() -> int:
    p = argparse.ArgumentParser(description="MyLink agent swarm invoker")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("discover")
    reg = sub.add_parser("register")
    reg.add_argument("--agent-id", required=True)
    reg.add_argument("--skills", default="g03-watch,parity-check")
    reg.add_argument("--prompt", default="Read-only BAITHex auditor. No keys. Fail-closed.")
    reg.add_argument("--name", default="")
    inv = sub.add_parser("invoke")
    inv.add_argument("--skill", required=True, choices=sorted(SKILLS))
    run = sub.add_parser("run-swarm")
    run.add_argument("--register-id", default="baithex-swarm-runner")
    args = p.parse_args()

    if args.cmd == "discover":
        out: Any = discover()
    elif args.cmd == "register":
        skills = [s.strip() for s in args.skills.split(",") if s.strip()]
        out = register(args.agent_id, skills, args.prompt, args.name)
    elif args.cmd == "invoke":
        out = SKILLS[args.skill]()
    elif args.cmd == "run-swarm":
        out = {
            "register": register(
                args.register_id,
                ["g03-watch", "parity-check", "matching-snapshot"],
                "Swarm runner: G-03/G-09/G-04 read-only skills.",
                name="BAITHex Swarm Runner",
            ),
            "discover": discover(),
            "skills": {name: fn() for name, fn in SKILLS.items()},
        }
    else:
        return 2
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
