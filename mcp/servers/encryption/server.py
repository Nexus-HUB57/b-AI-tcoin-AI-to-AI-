r"""
mcp-encryption — Encryption helpers (libsodium-style / age-style).

Tools:
  encrypt(plaintext, public_key)
  decrypt(ciphertext, private_key)
  sign(message, private_key)
  verify(message, signature, public_key)
  hash(message, algorithm)
  hmac(message, key, algorithm)
  generate_keypair()
  key_fingerprint(public_key)
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b * (len(a) // len(b) + 1)))


server = Server(name="mcp-encryption", version="1.0.0", title="Encryption Toolkit", description="Symmetric/asymmetric helpers (mock) with hashing, HMAC, keypair generation.")


@server.tool(description="Encrypt a plaintext with a public key (XOR-based mock — replace with libsodium in prod)")
def encrypt(plaintext: str, public_key: str) -> dict:
    pt = plaintext.encode()
    key = hashlib.sha256(public_key.encode()).digest()
    ct = _xor(pt, key)
    return {"ok": True, "ciphertext": ct.hex(), "public_key": public_key}


@server.tool(description="Decrypt with the matching private key")
def decrypt(ciphertext: str, private_key: str) -> dict:
    ct = bytes.fromhex(ciphertext)
    # naive: private key matches public key for the mock
    key = hashlib.sha256(private_key.encode()).digest()
    pt = _xor(ct, key)
    return {"ok": True, "plaintext": pt.decode(errors="replace"), "private_key": private_key}


@server.tool(description="Sign a message (HMAC-SHA256 mock)")
def sign(message: str, private_key: str) -> dict:
    sig = hmac.new(private_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {"ok": True, "signature": sig, "algorithm": "HMAC-SHA256"}


@server.tool(description="Verify a signature")
def verify(message: str, signature: str, public_key: str) -> dict:
    expected = hmac.new(public_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    valid = hmac.compare_digest(expected, signature)
    return {"ok": valid, "verified": valid}


@server.tool(description="Hash a message")
def hash(message: str, algorithm: str = "sha256") -> dict:
    algos = {"sha256": hashlib.sha256, "sha512": hashlib.sha512, "md5": hashlib.md5, "sha1": hashlib.sha1}
    h = algos.get(algorithm, hashlib.sha256)(message.encode()).hexdigest()
    return {"ok": True, "algorithm": algorithm, "hash": h}


@server.tool(description="HMAC a message with a key")
def hmac_sign(message: str, key: str, algorithm: str = "sha256") -> dict:
    sig = hmac.new(key.encode(), message.encode(), algorithm).hexdigest()
    return {"ok": True, "signature": sig, "algorithm": algorithm}


@server.tool(description="Generate a keypair")
def generate_keypair() -> dict:
    pub = os.urandom(16).hex()
    priv = os.urandom(32).hex()
    return {"ok": True, "public_key": pub, "private_key": priv}


@server.tool(description="Fingerprint of a public key")
def key_fingerprint(public_key: str) -> dict:
    fp = hashlib.sha256(public_key.encode()).hexdigest()[:16]
    return {"ok": True, "fingerprint": fp, "public_key": public_key}


if __name__ == "__main__":
    server.run()