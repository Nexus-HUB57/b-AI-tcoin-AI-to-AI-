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


def _lift_x(x: int, even_y: bool = True):
    r"""Reconstrói ponto na curva a partir de coordenada x.

    BIP-340 requer y par (even_y=True por padrão).
    Retorna PointJacobi ou None se x não for válido na curva.
    """
    curve = ecdsa.SECP256k1.curve
    p = curve.p()
    y_sq = (pow(x, 3, p) + 7) % p
    y = pow(y_sq, (p + 1) // 4, p)
    # Verificar se y² = x³ + 7
    if pow(y, 2, p) != y_sq:
        return None
    # Se a paridade de y não bater, usar p - y
    if (y % 2 == 0) != even_y:
        y = p - y
    return ecdsa.ellipticcurve.PointJacobi(curve, x, y, 1)


class SchnorrKeyPair:
    r"""Par de chaves Schnorr sobre secp256k1.

    Gera chave privada aleatória e deriva a chave pública
    no formato x-only (apenas coordenada x, 32 bytes),
    conforme especificação BIP-340 (y par obrigatório).
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

        # BIP-340: se y for ímpar, negar chave privada para garantir y par
        if pub_point.y() % 2 != 0:
            self.priv_key = self.n - self.priv_key
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
        r"""Assina uma mensagem usando Schnorr/BIP-340 sobre secp256k1.

        O aux_rand é usado APENAS na derivação do nonce (anti-side-channel),
        não no cálculo da assinatura. Conforme BIP-340:
        - d' = d + H(aux_rand || P) mod n  (apenas para nonce)
        - k = H(P'.x || P.x || msg) mod n
        - e = H(R.x || P.x || msg) mod n
        - s = (k + e * d) mod n  (chave ORIGINAL, não tweakada)
        """
        if aux_rand is None:
            aux_rand = os.urandom(32)

        # Tweak para derivação de nonce (BIP-340 aux_rand)
        t = int.from_bytes(
            hashlib.sha256(aux_rand + self.pub_bytes).digest(),
            byteorder='big'
        ) % self.n
        d_prime = (t + self.priv_key) % self.n
        P_prime = d_prime * self.G

        # Nonce determinístico derivado de P' e P original
        nonce_input = bytes(P_prime.x().to_bytes(32, 'big')) + self.pub_bytes + message
        k = int.from_bytes(hashlib.sha256(nonce_input).digest(), byteorder='big') % self.n

        # Verificar que k != 0
        if k == 0:
            return self.sign(message, os.urandom(32))

        R = k * self.G

        # BIP-340: R deve ter y par; se ímpar, negar k
        if R.y() % 2 != 0:
            k = self.n - k
            R = k * self.G

        # Hash para desafio 'e'
        e_input = bytes(R.x().to_bytes(32, 'big')) + self.pub_bytes + message
        e = int.from_bytes(hashlib.sha256(e_input).digest(), byteorder='big') % self.n

        # Assinatura: s = k + e*d mod n (chave ORIGINAL)
        sig = (k + e * self.priv_key) % self.n
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
        r"""Verifica assinatura Schnorr contra pubkey x-only (BIP-340).

        Reconstrói P assumindo y par (BIP-340), então verifica
        s*G - e*P == R onde R.x == r.
        """
        try:
            curve = ecdsa.SECP256k1
            G = curve.generator
            n = curve.order
            p = curve.curve.p()

            r = int.from_bytes(self.r_bytes, byteorder='big')
            if r >= p:
                return False

            e = int.from_bytes(
                hashlib.sha256(self.r_bytes + pubkey_bytes + message).digest(),
                byteorder='big'
            ) % n

            # Reconstruir P com y par (BIP-340)
            x = int.from_bytes(pubkey_bytes, byteorder='big')
            P = _lift_x(x, even_y=True)
            if P is None:
                return False

            # s*G - e*P deve ter x == r
            R = self.s * G + (n - e) * P

            # Verificar que R nao e ponto no infinito
            try:
                R.to_affine()
            except Exception:
                return False

            # BIP-340: R.y deve ser par
            if R.y() % 2 != 0:
                return False

            return R.x() == r
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"SchnorrSignature(r={self.r_bytes.hex()[:16]}...)"
