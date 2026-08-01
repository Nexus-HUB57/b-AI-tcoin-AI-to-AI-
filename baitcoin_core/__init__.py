r"""
b'AI'tcoin Core - Modulo Principal do Ecossistema

Compoe a infraestrutura base: blockchain, consenso, criptografia, rede P2P
e o EcosystemNode com persistencia automatica.
"""

__version__ = "0.4.0"
__protocol__ = "zkML-PoUW-v1"

from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.blockchain.block import Block
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_core.network.p2p import P2PNetwork
from baitcoin_core.ecosystem import EcosystemNode

__all__ = [
    "Blockchain",
    "Block",
    "ZkMLConsensus",
    "SchnorrKeyPair",
    "P2PNetwork",
    "EcosystemNode",
]