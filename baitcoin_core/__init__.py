r"""
b'AI'tcoin Core — Modulo Principal do Ecossistema

Compoe a infraestrutura base: blockchain, consenso, criptografia, rede P2P,
enderecos unificados, mercado de taxas, verificacao de transacoes e o
EcosystemNode com persistencia automatica.
"""

__version__ = "0.5.0"
__protocol__ = "zkML-PoUW-v1"

from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.blockchain.block import Block
from baitcoin_core.blockchain.addresses import BAITAddress, pubkey_to_address, agent_to_address, validate_address
from baitcoin_core.blockchain.fees import FeeMarket, FeeEstimator
from baitcoin_core.blockchain.tx_verifier import TransactionVerifier, verify_transaction
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.consensus.difficulty import DifficultyAdjuster
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_core.network.p2p import P2PNetwork
from baitcoin_core.ecosystem import EcosystemNode

__all__ = [
    "Blockchain",
    "Block",
    "BAITAddress",
    "pubkey_to_address",
    "agent_to_address",
    "validate_address",
    "FeeMarket",
    "FeeEstimator",
    "TransactionVerifier",
    "verify_transaction",
    "ZkMLConsensus",
    "DifficultyAdjuster",
    "SchnorrKeyPair",
    "P2PNetwork",
    "EcosystemNode",
]