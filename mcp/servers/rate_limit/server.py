r"""
mcp-rate-limit — Token bucket + sliding window rate limiter.

Tools:
  check(key, limit, window_s, strategy)
  consume(key, cost, limit, window_s)
  reset(key)
  status(key)
  list_keys()
  set_policy(key, limit, window_s)
  get_policy(key)
"""

from __future__ import annotations

import hashlib
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


BUCKETS: dict = defaultdict(lambda: deque(maxlen=10_000))
POLICIES: dict = {}


def _now():
    return time.time()


server = Server(name="mcp-rate-limit", version="1.0.0", title="Rate Limiter", description="Token bucket + sliding window rate limiter for agent APIs.")


@server.tool(description="Check if a key is within its limit (does not consume)")
def check(key: str, limit: int = 100, window_s: int = 60, strategy: str = "sliding") -> dict:
    cutoff = _now() - window_s
    buf = BUCKETS[key]
    while buf and buf[0] < cutoff:
        buf.popleft()
    used = len(buf)
    allowed = used < limit
    return {"ok": allowed, "key": key, "used": used, "limit": limit, "remaining": max(0, limit - used), "window_s": window_s}


@server.tool(description="Consume a cost from a key's bucket")
def consume(key: str, cost: int = 1, limit: int = 100, window_s: int = 60) -> dict:
    chk = check(key, limit, window_s)
    if not chk["ok"]:
        return {"ok": False, "reason": "rate_limited", "used": chk["used"], "limit": limit}
    now = _now()
    for _ in range(cost):
        BUCKETS[key].append(now)
    return {"ok": True, "consumed": cost, "remaining": limit - chk["used"] - cost}


@server.tool(description="Reset the bucket for a key")
def reset(key: str) -> dict:
    BUCKETS[key].clear()
    return {"ok": True, "key": key}


@server.tool(description="Status for a key")
def status(key: str) -> dict:
    buf = BUCKETS[key]
    return {"ok": True, "key": key, "used": len(buf), "oldest_ts": buf[0] if buf else None, "newest_ts": buf[-1] if buf else None}


@server.tool(description="List all tracked keys")
def list_keys() -> dict:
    return {"ok": True, "keys": [{"key": k, "used": len(v)} for k, v in BUCKETS.items()]}


@server.tool(description="Set a default policy for a key")
def set_policy(key: str, limit: int, window_s: int) -> dict:
    POLICIES[key] = {"limit": limit, "window_s": window_s}
    return {"ok": True, "key": key, "policy": POLICIES[key]}


@server.tool(description="Get the policy for a key")
def get_policy(key: str) -> dict:
    return {"ok": True, "key": key, "policy": POLICIES.get(key, {"limit": None, "window_s": None})}


if __name__ == "__main__":
    server.run()