r"""
b'AI'tcoin Core — Modulo Principal do Ecossistema

Compoe a infraestrutura base: blockchain, consenso, criptografia, rede P2P,
enderecos unificados, mercado de taxas, verificacao de transacoes e o
EcosystemNode com persistencia automatica.

Audit 2026-09-22 — modularizacao: imports sao lazy para que modulos novos
(como ``baitcoin_core.daemon.status``) possam ser importados sem disparar
a cadeia de dependencias de ``ecdsa``, ``schnorr``, etc.

Uso:
    import baitcoin_core                          # so carrega __version__/__protocol__
    from baitcoin_core import Blockchain          # lazy import via __getattr__
    from baitcoin_core.daemon.status import build_status  # ja funcionava
"""

__version__ = "0.6.0"
__protocol__ = "zkML-PoUW-v1"


# Lazy import map — usado por __getattr__ para carregar modulos sob demanda.
# Isso evita que `import baitcoin_core` (sem pegar submodulos) dispare
# a cadeia de deps (ecdsa, etc.) e quebra imports leves como o novo
# ``baitcoin_core.daemon.status``.
_LAZY_IMPORTS = {
    "Blockchain":               "baitcoin_core.blockchain.chain",
    "Block":                    "baitcoin_core.blockchain.block",
    "BAITAddress":              "baitcoin_core.blockchain.addresses",
    "pubkey_to_address":        "baitcoin_core.blockchain.addresses",
    "agent_to_address":         "baitcoin_core.blockchain.addresses",
    "validate_address":         "baitcoin_core.blockchain.addresses",
    "FeeMarket":                "baitcoin_core.blockchain.fees",
    "FeeEstimator":             "baitcoin_core.blockchain.fees",
    "TransactionVerifier":      "baitcoin_core.blockchain.tx_verifier",
    "verify_transaction":       "baitcoin_core.blockchain.tx_verifier",
    "ZkMLConsensus":            "baitcoin_core.consensus.zkml_engine",
    "DifficultyAdjuster":       "baitcoin_core.consensus.difficulty",
    "SchnorrKeyPair":           "baitcoin_core.cryptography.schnorr",
    "P2PNetwork":               "baitcoin_core.network.p2p",
    "EcosystemNode":            "baitcoin_core.ecosystem",
}


def __getattr__(name: str):
    """PEP 562 lazy module attribute access."""
    if name in _LAZY_IMPORTS:
        import importlib
        module = importlib.import_module(_LAZY_IMPORTS[name])
        attr = getattr(module, name)
        globals()[name] = attr  # cache p/ proximas chamadas
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(globals().keys()) | list(_LAZY_IMPORTS.keys())


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
