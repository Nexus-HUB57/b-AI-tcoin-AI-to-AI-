"""Chainlink Data Streams HMAC authentication (stdlib only).

Spec: https://docs.chain.link/data-streams/reference/data-streams-api/authentication
String to sign: METHOD FULL_PATH BODY_HASH API_KEY TIMESTAMP
"""
from __future__ import annotations
import hashlib, hmac, json, os, time
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MAINNET_HOST = "https://api.dataengine.chain.link"
TESTNET_HOST = "https://api.testnet-dataengine.chain.link"

class DataStreamsAuthError(RuntimeError):
    pass

def body_hash_hex(body: bytes = b"") -> str:
    return hashlib.sha256(body).hexdigest()

def string_to_sign(method: str, full_path: str, body: bytes, api_key: str, timestamp_ms: int) -> str:
    return f"{method.upper()} {full_path} {body_hash_hex(body)} {api_key} {timestamp_ms}"

def generate_hmac_signature(method, full_path, body, api_key, api_secret, timestamp_ms=None):
    if not api_key or not api_secret:
        raise DataStreamsAuthError("api_key and api_secret are required")
    ts = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    msg = string_to_sign(method, full_path, body, api_key, ts)
    sig = hmac.new(api_secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return sig, ts

def auth_headers(method, full_path, api_key, api_secret, body=b"", timestamp_ms=None):
    sig, ts = generate_hmac_signature(method, full_path, body, api_key, api_secret, timestamp_ms)
    return {
        "Authorization": api_key,
        "X-Authorization-Timestamp": str(ts),
        "X-Authorization-Signature-SHA256": sig,
        "Accept": "application/json",
        "User-Agent": "BAITHex-data-streams/1.0",
    }

def credentials_from_env():
    key = os.environ.get("CHAINLINK_STREAMS_API_KEY", "").strip()
    secret = os.environ.get("CHAINLINK_STREAMS_API_SECRET", "").strip()
    if not key or not secret:
        raise DataStreamsAuthError("Set CHAINLINK_STREAMS_API_KEY and CHAINLINK_STREAMS_API_SECRET")
    return key, secret

@dataclass
class DataStreamsClient:
    api_key: str
    api_secret: str
    host: str = MAINNET_HOST
    timeout: float = 20.0

    @classmethod
    def from_env(cls, *, testnet: bool = False):
        key, secret = credentials_from_env()
        return cls(api_key=key, api_secret=secret, host=TESTNET_HOST if testnet else MAINNET_HOST)

    def _request(self, method, path, *, query=None, body=b"", authenticated=True):
        full_path = f"{path}?{urlencode({k: str(v) for k, v in query.items()})}" if query else path
        url = self.host.rstrip("/") + full_path
        headers = {"Accept": "application/json", "User-Agent": "BAITHex-data-streams/1.0"}
        if authenticated:
            headers.update(auth_headers(method, full_path, self.api_key, self.api_secret, body))
        if body:
            headers["Content-Type"] = "application/json"
        req = Request(url, data=body or None, headers=headers, method=method.upper())
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as exc:
            raise DataStreamsAuthError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise DataStreamsAuthError(f"request failed: {exc}") from exc

    def discovery(self, *, authenticated: bool = False):
        return self._request("GET", "/api/v1/discovery", authenticated=authenticated)

    def report(self, feed_id: str, timestamp: int):
        return self._request("GET", "/api/v1/reports", query={"feedID": feed_id, "timestamp": timestamp}, authenticated=True)

def self_test_hmac():
    api_key, api_secret = "00000000-0000-0000-0000-000000000001", "test-secret-value"
    path = "/api/v1/reports?feedID=0xabc&timestamp=1716211845"
    ts = 1716211845123
    sig, out_ts = generate_hmac_signature("GET", path, b"", api_key, api_secret, ts)
    assert out_ts == ts and len(sig) == 64
    msg = string_to_sign("GET", path, b"", api_key, ts)
    assert sig == hmac.new(api_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return {"status": "PASS", "signature": sig, "string_to_sign": msg}

if __name__ == "__main__":
    print(json.dumps(self_test_hmac(), indent=2))
