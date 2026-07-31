r"""
b'AI'tcoin Core - Módulo Principal do Ecossistema

Compõe a infraestrutura base: blockchain, consenso, criptografia e rede P2P.
"""

__version__ = "0.1.0"
__protocol__ = "zkML-PoUW-v1"

from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.blockchain.block import Block
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_core.network.p2p import P2PNetwork

__all__ = [
    "Blockchain",
    "Block",
    "ZkMLConsensus",
    "SchnorrKeyPair",
    "P2PNetwork",
]