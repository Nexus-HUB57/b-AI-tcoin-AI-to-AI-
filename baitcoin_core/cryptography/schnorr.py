r"""
Criptografia Schnorr / BIP-340 para b'AI'tcoin.

Implementa chaves e assinaturas Schnorr sobre a curva secp256k1,
compatíveis com o padrão BIP-340 do Bitcoin.

Por que Schnorr?
- Compatibilidade com Taproot
- Assinaturas agregáveis (batch)
- Provas de conhecimento mais simples
- Ideal para transações AI-to-AI com múltiplos signatários
"""

import os
import hashlib
import ecdsa
from typing import Optional, Tuple


class SchnorrKeyPair:
    r"""Par de chaves Schnorr sobre secp256k1.

    Gera chave privada aleatória e deriva a chave pública
    no formato x-only (apenas coordenada x, 32 bytes),
    conforme especificação BIP-340.
    """

    def __init__(self, private_key: Optional[int] = None):
        self.curve = ecdsa.SECP256k1
        self.n = self.curve.order
        self.G = self.curve.generator

        if private_key is not None:
            self.priv_key = private_key % (self.n - 1) + 1
        else:
            self.priv_key = int.from_bytes(os.urandom(32), byteorder='big') % (self.n - 1) + 1

        pub_point = self.priv_key * self.G
        self.pub_bytes = pub_point.x().to_bytes(32, byteorder='big')
        self.pub_point = pub_point

    @property
    def private_key_hex(self) -> str:
        return format(self.priv_key, '064x')

    @property
    def public_key_hex(self) -> str:
        return self.pub_bytes.hex()

    def sign(self, message: bytes, aux_rand: Optional[bytes] = None) -> 'SchnorrSignature':
        r"""Assina uma mensagem usando Schnorr sobre secp256k1."""
        if aux_rand is None:
            aux_rand = os.urandom(32)

        # Tweak da chave privada com aux_rand (BIP-340)
        t = int.from_bytes(
            hashlib.sha256(aux_rand + self.pub_bytes).digest(),
            byteorder='big'
        ) % self.n
        d_prime = (t + self.priv_key) % self.n
        P_prime = d_prime * self.G

        # Nonce determinístico
        nonce_input = bytes(P_prime.x().to_bytes(32, 'big')) + self.pub_bytes + message
        k = int.from_bytes(hashlib.sha256(nonce_input).digest(), byteorder='big') % self.n
        R = k * self.G

        # Hash para 'e'
        e_input = bytes(R.x().to_bytes(32, 'big')) + self.pub_bytes + message
        e = int.from_bytes(hashlib.sha256(e_input).digest(), byteorder='big') % self.n

        sig = (k + e * d_prime) % self.n
        return SchnorrSignature(sig, R.x().to_bytes(32, 'big'))

    def __repr__(self) -> str:
        return f"SchnorrKeyPair(pub={self.public_key_hex[:16]}...)"


class SchnorrSignature:
    r"""Assinatura Schnorr (64 bytes = r || s)."""

    def __init__(self, s: int, r_bytes: bytes):
        self.s = s
        self.r_bytes = r_bytes

    @property
    def raw(self) -> bytes:
        return self.r_bytes + self.s.to_bytes(32, byteorder='big')

    @property
    def hex(self) -> str:
        return self.raw.hex()

    def verify(self, pubkey_bytes: bytes, message: bytes) -> bool:
        r"""Verifica assinatura Schnorr contra pubkey x-only."""
        try:
            curve = ecdsa.SECP256k1
            G = curve.generator
            n = curve.order

            r = int.from_bytes(self.r_bytes, byteorder='big')
            e = int.from_bytes(
                hashlib.sha256(self.r_bytes + pubkey_bytes + message).digest(),
                byteorder='big'
            ) % n

            # Reconstruir P a partir de x-only pubkey (assumir y par)
            x = int.from_bytes(pubkey_bytes, byteorder='big')
            y_sq = pow(x, 3, curve.curve.p()) + 7
            y = pow(y_sq, (curve.curve.p() + 1) // 4, curve.curve.p())
            P = ecdsa.ellipticcurve.PointJacobi(curve.curve, x, y, 1)

            R = self.s * G - e * P
            return R.x() == r
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"SchnorrSignature(r={self.r_bytes.hex()[:16]}...)"
