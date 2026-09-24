"""Chave privada / pública Schnorr BIP-340 (secp256k1).

Compatível com:
  - baitcoin_core.cryptography.schnorr
  - native_processing.schnorr_parity_verifier (verify_proof)

Uso típico (oráculo de parity)
------------------------------
  from native_processing.schnorr_keypair import SchnorrKeyPair, load_or_generate

  # Gerar e persistir (apenas em ambiente controlado / HSM / secrets manager)
  kp = SchnorrKeyPair.generate()
  kp.save_encrypted("oracle-a.key", password=b"...")

  # Carregar e assinar attestation
  kp = SchnorrKeyPair.load_encrypted("oracle-a.key", password=b"...")
  sig = kp.sign(message_bytes)          # 64 bytes r||s
  pubkey_hex = kp.public_key_hex        # 32-byte x-only (hex)

Segurança
---------
- Nunca logar, printar ou committar a chave privada.
- Em produção use HSM, AWS KMS, Vault ou arquivo criptografado com permissões 0600.
- A normalização BIP-340 (y par) é aplicada automaticamente no construtor.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import ecdsa

# ---------------------------------------------------------------------------
# Constantes secp256k1 / BIP-340
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Assinatura
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SchnorrSignature:
    """Assinatura BIP-340: r (32 bytes) || s (32 bytes) = 64 bytes."""

    r_bytes: bytes
    s: int

    def __post_init__(self):
        if not isinstance(self.r_bytes, bytes) or len(self.r_bytes) != 32:
            raise ValueError("r must be exactly 32 bytes")
        if type(self.s) is not int or not (0 <= self.s < _N):
            raise ValueError("s out of range")

    @property
    def raw(self) -> bytes:
        return self.r_bytes + _bytes32(self.s)

    @property
    def hex(self) -> str:
        return self.raw.hex()

    @classmethod
    def from_raw(cls, data: bytes) -> "SchnorrSignature":
        if len(data) != 64:
            raise ValueError("signature must be 64 bytes")
        return cls(r_bytes=data[:32], s=int.from_bytes(data[32:], "big"))

    def verify(self, pubkey_xonly: bytes, message: bytes) -> bool:
        """Verifica a assinatura contra uma chave pública x-only (32 bytes)."""
        if not isinstance(pubkey_xonly, bytes) or len(pubkey_xonly) != 32:
            return False
        if not isinstance(message, bytes):
            return False
        r = int.from_bytes(self.r_bytes, "big")
        if r >= _P or self.s >= _N:
            return False
        P = _lift_x(int.from_bytes(pubkey_xonly, "big"), even_y=True)
        if P is None:
            return False
        e = int.from_bytes(
            _tagged_hash("BIP0340/challenge", self.r_bytes + pubkey_xonly + message),
            "big",
        ) % _N
        R = self.s * _G + (_N - e) * P
        R_affine = _affine(R)
        if R_affine is None or (R_affine.y() & 1):
            return False
        return R_affine.x() == r


# ---------------------------------------------------------------------------
# KeyPair
# ---------------------------------------------------------------------------

class SchnorrKeyPair:
    """Par de chaves Schnorr BIP-340 com representação x-only da pública.

    A chave privada é normalizada para que a coordenada y da pública seja par
    (requisito BIP-340).
    """

    def __init__(self, private_key: Optional[int] = None):
        if private_key is None:
            while True:
                candidate = secrets.randbelow(_N - 1) + 1
                if 1 <= candidate < _N:
                    break
        else:
            if type(private_key) is not int or not (1 <= private_key < _N):
                raise ValueError("private_key must be an integer in [1, n-1]")
            candidate = private_key

        point = candidate * _G
        # BIP-340: force even y
        if point.y() & 1:
            candidate = _N - candidate
            point = candidate * _G

        self._priv = candidate
        self._pub_point = point
        self.pub_bytes = _bytes32(point.x())  # x-only, 32 bytes

    # ---- factories --------------------------------------------------------

    @classmethod
    def generate(cls) -> "SchnorrKeyPair":
        """Gera um novo par de chaves com CSPRNG."""
        return cls(None)

    @classmethod
    def from_private_hex(cls, hex_str: str) -> "SchnorrKeyPair":
        raw = bytes.fromhex(hex_str)
        if len(raw) != 32:
            raise ValueError("private key hex must be 32 bytes")
        return cls(int.from_bytes(raw, "big"))

    @classmethod
    def from_private_bytes(cls, data: bytes) -> "SchnorrKeyPair":
        if len(data) != 32:
            raise ValueError("private key must be 32 bytes")
        return cls(int.from_bytes(data, "big"))

    @classmethod
    def from_pubkey_hex(cls, pubkey_hex: str) -> "SchnorrKeyPair":
        """Cria um objeto somente-leitura a partir da chave pública (sem privada).

        Útil para verificação. sign() levantará RuntimeError.
        """
        raw = bytes.fromhex(pubkey_hex)
        if len(raw) == 33 and raw[0] in (2, 3):
            raw = raw[1:]  # strip compressed prefix
        if len(raw) != 32:
            raise ValueError("pubkey must be 32-byte x-only or 33-byte compressed")
        obj = object.__new__(cls)
        obj._priv = None  # type: ignore
        obj._pub_point = _lift_x(int.from_bytes(raw, "big"), even_y=True)
        if obj._pub_point is None:
            raise ValueError("invalid x-only public key")
        obj.pub_bytes = raw
        return obj

    # ---- propriedades -----------------------------------------------------

    @property
    def private_key_bytes(self) -> bytes:
        if self._priv is None:
            raise RuntimeError("this keypair has no private key (pubkey-only)")
        return _bytes32(self._priv)

    @property
    def private_key_hex(self) -> str:
        return self.private_key_bytes.hex()

    @property
    def public_key_hex(self) -> str:
        return self.pub_bytes.hex()

    @property
    def has_private(self) -> bool:
        return self._priv is not None

    # ---- assinatura -------------------------------------------------------

    def sign(self, message: bytes, aux_rand: Optional[bytes] = None) -> SchnorrSignature:
        """Assina `message` (bytes arbitrários) com BIP-340.

        aux_rand: 32 bytes opcionais (recomendado para side-channel resistance).
        """
        if self._priv is None:
            raise RuntimeError("cannot sign: no private key")
        if not isinstance(message, bytes):
            raise TypeError("message must be bytes")
        if aux_rand is None:
            aux_rand = secrets.token_bytes(32)
        if not isinstance(aux_rand, bytes) or len(aux_rand) != 32:
            raise ValueError("aux_rand must be exactly 32 bytes")

        d = self._priv
        t = bytes(a ^ b for a, b in zip(_bytes32(d), _tagged_hash("BIP0340/aux", aux_rand)))
        nonce_input = t + self.pub_bytes + message
        k0 = int.from_bytes(_tagged_hash("BIP0340/nonce", nonce_input), "big") % _N
        if k0 == 0:
            raise RuntimeError("BIP-340 nonce generation returned zero")

        R = k0 * _G
        k = k0 if (R.y() & 1) == 0 else _N - k0
        if k != k0:
            R = k * _G
        r_bytes = _bytes32(R.x())

        e = int.from_bytes(
            _tagged_hash("BIP0340/challenge", r_bytes + self.pub_bytes + message),
            "big",
        ) % _N
        s = (k + e * d) % _N
        return SchnorrSignature(r_bytes=r_bytes, s=s)

    def verify(self, message: bytes, signature: Union[SchnorrSignature, bytes]) -> bool:
        """Verifica uma assinatura contra a chave pública deste par."""
        if isinstance(signature, bytes):
            signature = SchnorrSignature.from_raw(signature)
        return signature.verify(self.pub_bytes, message)

    # ---- persistência (criptografada com senha) ---------------------------

    def save_encrypted(self, path: Union[str, Path], password: bytes) -> None:
        """Salva a chave privada criptografada (scrypt + AES-GCM via cryptography).

        Requer: pip install cryptography
        Permissões do arquivo: 0600.
        """
        if self._priv is None:
            raise RuntimeError("cannot save: no private key")
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        except ImportError as exc:
            raise ImportError(
                "cryptography package required for encrypted save: pip install cryptography"
            ) from exc

        path = Path(path)
        salt = secrets.token_bytes(16)
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        key = kdf.derive(password)
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, self.private_key_bytes, None)

        payload = {
            "version": 1,
            "kdf": "scrypt",
            "n": 16384,
            "r": 8,
            "p": 1,
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "pubkey": self.public_key_hex,  # público, para verificação
        }
        path.write_text(json.dumps(payload, indent=2))
        path.chmod(0o600)

    @classmethod
    def load_encrypted(cls, path: Union[str, Path], password: bytes) -> "SchnorrKeyPair":
        """Carrega chave privada de arquivo criptografado."""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        except ImportError as exc:
            raise ImportError(
                "cryptography package required: pip install cryptography"
            ) from exc

        path = Path(path)
        payload = json.loads(path.read_text())
        if payload.get("version") != 1:
            raise ValueError("unsupported key file version")

        salt = bytes.fromhex(payload["salt"])
        nonce = bytes.fromhex(payload["nonce"])
        ciphertext = bytes.fromhex(payload["ciphertext"])

        kdf = Scrypt(
            salt=salt,
            length=32,
            n=payload.get("n", 16384),
            r=payload.get("r", 8),
            p=payload.get("p", 1),
        )
        key = kdf.derive(password)
        aesgcm = AESGCM(key)
        priv_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        kp = cls.from_private_bytes(priv_bytes)

        # Sanity: pubkey no arquivo deve bater
        if payload.get("pubkey") and payload["pubkey"] != kp.public_key_hex:
            raise ValueError("decrypted key does not match stored pubkey")
        return kp

    def __repr__(self) -> str:
        return f"SchnorrKeyPair(pubkey={self.public_key_hex[:16]}...)"


# ---------------------------------------------------------------------------
# Helper de conveniência
# ---------------------------------------------------------------------------

def load_or_generate(
    path: Union[str, Path],
    password: bytes,
    *,
    create_if_missing: bool = True,
) -> SchnorrKeyPair:
    """Carrega chave criptografada ou gera uma nova se o arquivo não existir."""
    path = Path(path)
    if path.exists():
        return SchnorrKeyPair.load_encrypted(path, password)
    if not create_if_missing:
        raise FileNotFoundError(f"key file not found: {path}")
    kp = SchnorrKeyPair.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    kp.save_encrypted(path, password)
    return kp
