r"""
mcp-attest — Capability attestations + signed receipts.

Tools:
  issue(agent_id, capabilities, ttl_s)
  verify(receipt_token)
  revoke(receipt_token)
  list_for_agent(agent_id)
  capabilities_of(receipt_token)
  sign_payload(payload)
  verify_signature(payload, signature)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


RECEIPTS: dict = {}
SECRET = b"mcp-attest-secret-key-replace-me"


def _sign(data: bytes) -> str:
    return hmac.new(SECRET, data, hashlib.sha256).hexdigest()


def _hash(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:24]


server = Server(name="mcp-attest", version="1.0.0", title="Capability Attestations", description="Issue / verify / revoke capability attestations with HMAC signatures.")


@server.tool(description="Issue a capability receipt")
def issue(agent_id: str, capabilities: list, ttl_s: int = 3600) -> dict:
    token = _hash("token", agent_id, time.time())
    payload = {"agent_id": agent_id, "capabilities": capabilities, "iat": int(time.time()), "exp": int(time.time()) + ttl_s}
    signature = _sign(json.dumps(payload, sort_keys=True).encode())
    RECEIPTS[token] = {**payload, "token": token, "signature": signature, "revoked": False}
    return {"ok": True, "token": token, "expires_at": payload["exp"], "signature": signature}


@server.tool(description="Verify a receipt token")
def verify(receipt_token: str) -> dict:
    r = RECEIPTS.get(receipt_token)
    if not r:
        return {"ok": False, "error": "not_found"}
    if r["revoked"]:
        return {"ok": False, "error": "revoked"}
    if time.time() > r["exp"]:
        return {"ok": False, "error": "expired"}
    payload = {"agent_id": r["agent_id"], "capabilities": r["capabilities"], "iat": r["iat"], "exp": r["exp"]}
    expected = _sign(json.dumps(payload, sort_keys=True).encode())
    valid = hmac.compare_digest(expected, r["signature"])
    return {"ok": valid, "agent_id": r["agent_id"], "capabilities": r["capabilities"], "expires_at": r["exp"]}


@server.tool(description="Revoke a receipt")
def revoke(receipt_token: str) -> dict:
    r = RECEIPTS.get(receipt_token)
    if not r:
        return {"ok": False, "error": "not_found"}
    r["revoked"] = True
    return {"ok": True, "revoked": receipt_token}


@server.tool(description="List all receipts for an agent")
def list_for_agent(agent_id: str) -> dict:
    rs = [{"token": t, "capabilities": r["capabilities"], "revoked": r["revoked"], "expires_at": r["exp"]} for t, r in RECEIPTS.items() if r["agent_id"] == agent_id]
    return {"ok": True, "receipts": rs, "count": len(rs)}


@server.tool(description="Extract capabilities from a receipt")
def capabilities_of(receipt_token: str) -> dict:
    r = RECEIPTS.get(receipt_token)
    if not r:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "capabilities": r["capabilities"]}


@server.tool(description="Sign an arbitrary payload (HMAC-SHA256)")
def sign_payload(payload: dict) -> dict:
    data = json.dumps(payload, sort_keys=True).encode()
    sig = _sign(data)
    return {"ok": True, "payload_sha256": hashlib.sha256(data).hexdigest(), "signature": sig}


@server.tool(description="Verify a signature against a payload")
def verify_signature(payload: dict, signature: str) -> dict:
    data = json.dumps(payload, sort_keys=True).encode()
    expected = _sign(data)
    valid = hmac.compare_digest(expected, signature)
    return {"ok": valid, "verified": valid}


if __name__ == "__main__":
    server.run()