r"""
Tensor Commitment Scheme - Commitment pedersen para tensores ML.

Implementa:
- Pedersen commitment para tensores
- Vector commitment (agregação de múltiplos tensores)
- Binding e hiding properties
- Abertura de commitment (open) com verificação

O commitment permite que um validador AI prove que
processou um tensor específico sem revelar seu conteúdo.
"""

import hashlib
import hmac
import secrets
import struct
from typing import List, Optional, Tuple
from dataclasses import dataclass


# Generators para Pedersen commitment (simulados com hash-to-point)
def _hash_to_point(seed: bytes, index: int) -> int:
    """Deriva um ponto na curva a partir de seed (hash-to-curve)."""
    data = seed + struct.pack(">I", index)
    h = hashlib.sha256(data).digest()
    return int.from_bytes(h, 'big')


# Generators fixos do sistema (G, H)
G = _hash_to_point(b"baitcoin_pedersen_G", 0)
H = _hash_to_point(b"baitcoin_pedersen_H", 0)

# Primo grande para operações (aprox 256-bit)
P = 2**256 - 189


@dataclass
class TensorCommitment:
    """Commitment de um tensor ML.

    Compõe:
    - commitment: o valor do commitment (C = G^tensor * H^blind)
    - blind: o fator cego (mantido secreto)
    - tensor_hash: hash do tensor original
    - salt: salt usado no hash
    - dimensions: dimensões do tensor
    """
    commitment: int
    blind: int
    tensor_hash: str
    salt: bytes
    dimensions: Tuple[int, ...]
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "commitment": hex(self.commitment),
            "tensor_hash": self.tensor_hash,
            "salt": self.salt.hex(),
            "dimensions": list(self.dimensions),
            "timestamp": self.timestamp,
        }


class TensorCommitmentScheme:
    r"""Esquema de commitment para tensores ML.

    Usa Pedersen commitments para provar que um tensor
    foi processado sem revelar seu conteúdo:

    1. Commit: C = G^tensor_hash * H^blind mod P
    2. Open: revelar (tensor_hash, blind, salt)
    3. Verify: recalcular C' e comparar com C
    """

    @staticmethod
    def commit(tensor_data: bytes, dimensions: Optional[Tuple[int, ...]] = None) -> TensorCommitment:
        r"""Cria commitment de um tensor.

        Args:
            tensor_data: bytes brutos do tensor
            dimensions: dimensões do tensor (opcional)

        Returns:
            TensorCommitment com commitment, blind e metadata
        """
        import time
        salt = secrets.token_bytes(32)
        blind = secrets.randbelow(P)

        # Hash do tensor com salt
        tensor_hash = hashlib.sha256(salt + tensor_data).hexdigest()
        tensor_int = int(tensor_hash, 16)

        # Pedersen commitment: C = G^tensor * H^blind mod P
        commitment = pow(G, tensor_int, P) * pow(H, blind, P) % P

        return TensorCommitment(
            commitment=commitment,
            blind=blind,
            tensor_hash=tensor_hash,
            salt=salt,
            dimensions=dimensions or (len(tensor_data),),
            timestamp=time.time(),
        )

    @staticmethod
    def open(tc: TensorCommitment, tensor_data: bytes) -> dict:
        r"""Abre o commitment, revelando os parâmetros.

        Returns:
            Dict com tensor_hash, blind e commitment para verificação.
        """
        return {
            "tensor_hash": tc.tensor_hash,
            "blind": tc.blind,
            "commitment": tc.commitment,
            "salt": tc.salt,
        }

    @staticmethod
    def verify(opening: dict, tensor_data: bytes) -> bool:
        r"""Verifica se o commitment corresponde ao tensor.

        Recalcula o commitment e compara com o original.
        """
        tensor_hash = hashlib.sha256(opening["salt"] + tensor_data).hexdigest()
        if tensor_hash != opening["tensor_hash"]:
            return False

        tensor_int = int(tensor_hash, 16)
        expected = (pow(G, tensor_int, P) * pow(H, opening["blind"], P)) % P

        return expected == opening["commitment"]

    @staticmethod
    def batch_commit(tensor_list: List[bytes]) -> List[TensorCommitment]:
        r"""Cria commitments para múltiplos tensores.

        Retorna lista de TensorCommitment na mesma ordem.
        """
        return [TensorCommitmentScheme.commit(t) for t in tensor_list]

    @staticmethod
    def aggregate(commitments: List[TensorCommitment]) -> int:
        r"""Agrega múltiplos commitments em um único.

        C_agg = prod(C_i) mod P
        """
        result = 1
        for tc in commitments:
            result = (result * tc.commitment) % P
        return result
