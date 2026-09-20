r"""
mcp-vault — Secrets manager (env / Keychain / AWS SM abstraction).

Tools:
  get_secret(key)
  set_secret(key, value)
  delete_secret(key)
  list_keys(prefix)
  rotate_secret(key, length)
  secret_metadata(key)
  bulk_get(keys)
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


STORE: dict = {}


def _hash(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:16]


server = Server(name="mcp-vault", version="1.0.0", title="Secrets Vault", description="Secrets manager — get/set/rotate/delete, with metadata.")


@server.tool(description="Get a secret by key")
def get_secret(key: str) -> dict:
    v = STORE.get(key)
    if v is None:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "key": key, "value": v["value"], "version": v["version"]}


@server.tool(description="Set (or overwrite) a secret")
def set_secret(key: str, value: str) -> dict:
    cur = STORE.get(key)
    STORE[key] = {
        "value": value,
        "version": (cur["version"] + 1) if cur else 1,
        "created_at": cur["created_at"] if cur else time.time(),
        "updated_at": time.time(),
    }
    return {"ok": True, "key": key, "version": STORE[key]["version"]}


@server.tool(description="Delete a secret")
def delete_secret(key: str) -> dict:
    if key in STORE:
        del STORE[key]
        return {"ok": True, "deleted": key}
    return {"ok": False, "error": "not_found"}


@server.tool(description="List keys with a prefix")
def list_keys(prefix: str = "") -> dict:
    keys = [k for k in STORE if k.startswith(prefix)]
    return {"ok": True, "keys": keys, "count": len(keys)}


@server.tool(description="Rotate a secret (generate new random value)")
def rotate_secret(key: str, length: int = 32) -> dict:
    new_value = secrets.token_urlsafe(length)
    return set_secret(key, new_value)


@server.tool(description="Metadata for a secret (without exposing the value)")
def secret_metadata(key: str) -> dict:
    v = STORE.get(key)
    if not v:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "key": key, "version": v["version"], "created_at": v["created_at"], "updated_at": v["updated_at"]}


@server.tool(description="Bulk fetch secrets")
def bulk_get(keys: list) -> dict:
    out = {}
    for k in keys:
        v = STORE.get(k)
        out[k] = v["value"] if v else None
    return {"ok": True, "secrets": out, "count": len([v for v in out.values() if v is not None])}


if __name__ == "__main__":
    server.run()