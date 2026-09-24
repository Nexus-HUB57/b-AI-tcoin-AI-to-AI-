import os
import hashlib
import ecdsa


def bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='big')


def int_to_bytes(i: int) -> bytes:
    return i.to_bytes(32, byteorder='big')


class SchnorrKeyPair:
    """Implementacao nativa de Assinaturas Schnorr (BIP-340) em secp256k1."""

    def __init__(self, private_key_int: int = None):
        self.curve = ecdsa.SECP256k1
        self.n = self.curve.order
        if private_key_int:
            self.priv_key = private_key_int
        else:
            self.priv_key = bytes_to_int(os.urandom(32)) % (self.n - 1) + 1

        pub_point = self.priv_key * self.curve.generator
        self.pub_bytes = int_to_bytes(pub_point.x())

    @property
    def address(self) -> str:
        """Gera endereco Taproot simulado bAI1q..."""
        return f"bAI1q{self.pub_bytes.hex()[:30]}"

    def sign_schnorr(self, msg_hash: bytes) -> bytes:
        """Assina uma mensagem usando o esquema Schnorr (BIP-340)."""
        k = bytes_to_int(hashlib.sha256(int_to_bytes(self.priv_key) + msg_hash).digest()) % (self.n - 1) + 1
        R = k * self.curve.generator
        if R.y() % 2 != 0:
            k = self.n - k
            R = k * self.curve.generator

        rx_bytes = int_to_bytes(R.x())
        e_hash = hashlib.sha256(rx_bytes + self.pub_bytes + msg_hash).digest()
        e = bytes_to_int(e_hash) % self.n
        s = (k + e * self.priv_key) % self.n
        return rx_bytes + int_to_bytes(s)
