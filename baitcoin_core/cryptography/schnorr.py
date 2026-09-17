"""Schnorr BIP-340 sobre secp256k1.

A implementação mantém a API local (SchnorrKeyPair/SchnorrSignature), mas usa
integralmente os domínios BIP0340/aux, BIP0340/nonce e BIP0340/challenge.
"""
from __future__ import annotations

import hashlib
import os
from typing import Optional

import ecdsa


_CURVE = ecdsa.SECP256k1
_P = _CURVE.curve.p()
_N = _CURVE.order
_G = _CURVE.generator
_INFINITE = ecdsa.ellipticcurve.INFINITY


def _tagged_hash(tag: str, message: bytes) -> bytes:
    tag_hash = hashlib.sha256(tag.encode("ascii")).digest()
    return hashlib.sha256(tag_hash + tag_hash + message).digest()


def _bytes32(value: int) -> bytes:
    return value.to_bytes(32, byteorder="big")


def _lift_x(x: int, even_y: bool = True):
    """Return the unique secp256k1 point with x and requested y parity."""
    if not isinstance(x, int) or x < 0 or x >= _P:
        return None
    y_sq = (pow(x, 3, _P) + 7) % _P
    y = pow(y_sq, (_P + 1) // 4, _P)
    if pow(y, 2, _P) != y_sq:
        return None
    if (y & 1) != (0 if even_y else 1):
        y = _P - y
    return ecdsa.ellipticcurve.PointJacobi(_CURVE.curve, x, y, 1)


def _affine(point):
    if point is None or point == _INFINITE:
        return None
    try:
        affine = point.to_affine()
        if affine == _INFINITE:
            return None
        return affine
    except Exception:
        return None


class SchnorrKeyPair:
    """BIP-340 key pair with x-only public key representation."""

    def __init__(self, private_key: Optional[int] = None):
        self.curve = _CURVE
        self.n = _N
        self.G = _G
        if private_key is None:
            while True:
                candidate = int.from_bytes(os.urandom(32), "big")
                if 1 <= candidate < self.n:
                    break
        else:
            if type(private_key) is not int or not 1 <= private_key < self.n:
                raise ValueError("private key must be an integer in [1, n-1]")
            candidate = private_key

        point = candidate * self.G
        if point.y() & 1:
            candidate = self.n - candidate
            point = candidate * self.G
        self.priv_key = candidate
        self.pub_point = point
        self.pub_bytes = _bytes32(point.x())

    @property
    def private_key_hex(self) -> str:
        return self.priv_key.to_bytes(32, "big").hex()

    @property
    def public_key_hex(self) -> str:
        return self.pub_bytes.hex()

    def sign(self, message: bytes, aux_rand: Optional[bytes] = None) -> "SchnorrSignature":
        if not isinstance(message, bytes):
            raise TypeError("message must be bytes")
        if aux_rand is None:
            aux_rand = os.urandom(32)
        if not isinstance(aux_rand, bytes) or len(aux_rand) != 32:
            raise ValueError("aux_rand must be exactly 32 bytes")

        d = self.priv_key
        # The constructor already normalizes d so that the public point is even.
        t = bytes(a ^ b for a, b in zip(_bytes32(d), _tagged_hash("BIP0340/aux", aux_rand)))
        nonce_input = t + self.pub_bytes + message
        k0 = int.from_bytes(_tagged_hash("BIP0340/nonce", nonce_input), "big") % self.n
        if k0 == 0:
            raise RuntimeError("BIP-340 nonce generation returned zero")
        R = k0 * self.G
        k = k0 if (R.y() & 1) == 0 else self.n - k0
        if k != k0:
            R = k * self.G
        r_bytes = _bytes32(R.x())
        e = int.from_bytes(
            _tagged_hash("BIP0340/challenge", r_bytes + self.pub_bytes + message), "big"
        ) % self.n
        s = (k + e * d) % self.n
        return SchnorrSignature(s=s, r_bytes=r_bytes)

    @classmethod
    def from_pubkey_hex(cls, pubkey_hex: str) -> "SchnorrKeyPair":
        if not isinstance(pubkey_hex, str):
            raise TypeError("pubkey_hex must be a string")
        raw = bytes.fromhex(pubkey_hex)
        if len(raw) == 33 and raw[0] in (2, 3):
            raw = raw[1:]
        if len(raw) != 32:
            raise ValueError("expected a 32-byte x-only public key")
        point = _lift_x(int.from_bytes(raw, "big"), even_y=True)
        if point is None:
            raise ValueError("invalid x-only public key")
        kp = cls.__new__(cls)
        kp.curve, kp.n, kp.G = _CURVE, _N, _G
        kp.priv_key = None
        kp.pub_point = point
        kp.pub_bytes = raw
        return kp

    def __repr__(self) -> str:
        return f"SchnorrKeyPair(pub={self.public_key_hex[:16]}...)"


class SchnorrSignature:
    """BIP-340 signature represented as r || s (64 bytes)."""

    def __init__(self, s: int, r_bytes: bytes):
        if type(s) is not int:
            raise TypeError("s must be an integer")
        if not isinstance(r_bytes, bytes) or len(r_bytes) != 32:
            raise ValueError("r must be exactly 32 bytes")
        self.s = s
        self.r_bytes = r_bytes

    @property
    def raw(self) -> bytes:
        if not 0 <= self.s < _N:
            raise ValueError("s is outside the BIP-340 range")
        return self.r_bytes + _bytes32(self.s)

    @property
    def hex(self) -> str:
        return self.raw.hex()

    def verify(self, pubkey_bytes: bytes, message: bytes) -> bool:
        if not isinstance(pubkey_bytes, bytes) or len(pubkey_bytes) != 32:
            return False
        if not isinstance(message, bytes) or len(self.r_bytes) != 32:
            return False
        if type(self.s) is not int or self.s < 0 or self.s >= _N:
            return False
        r = int.from_bytes(self.r_bytes, "big")
        if r >= _P:
            return False
        P = _lift_x(int.from_bytes(pubkey_bytes, "big"), even_y=True)
        if P is None:
            return False
        e = int.from_bytes(
            _tagged_hash("BIP0340/challenge", self.r_bytes + pubkey_bytes + message), "big"
        ) % _N
        R = self.s * _G + (_N - e) * P
        R_affine = _affine(R)
        if R_affine is None:
            return False
        if R_affine.y() & 1:
            return False
        return R_affine.x() == r

    def __repr__(self) -> str:
        return f"SchnorrSignature(r={self.r_bytes.hex()[:16]}...)"
