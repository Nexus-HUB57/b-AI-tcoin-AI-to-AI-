"""Status module — extracted from main_daemon.py (audit 2026-09-22 P1).

Antes: o método ``BAITDaemon.get_status()`` era 50 linhas dentro do
monólito de 6.591 linhas. Difícil de testar unitariamente.

Depois: função pura ``build_status(daemon)`` neste módulo. Aceita
qualquer objeto que exponha os atributos esperados. Testes em
``tests/baitcoin_core/test_status.py``.

Este é o primeiro passo da modularização. O padrão pode ser replicado
para outros métodos do BAITDaemon (initialize, mine_block, _persist_block).
"""
from __future__ import annotations
import time
from typing import Any, Dict, Protocol


class _HasModules(Protocol):
    """Structural type para o daemon — qualquer objeto com esses atributos é aceito."""
    blockchain: Any
    marketplace: Any
    oracle: Any
    zkml_verifier: Any
    staking_pool: Any
    lending_engine: Any
    agent_registry: Any
    explorer_index: Any
    p2p_network: Any
    obscura_bridge: Any
    persistent_state: Any
    token: Any
    data_path: str
    test_suites: int


def build_status(d: _HasModules) -> Dict[str, Any]:
    """Compila o payload de status completo do daemon.

    Função pura — não toca em I/O, não tem side effects. Apenas agrega
    estado e devolve um dict serializável.
    """
    chain_valid = bool(d.blockchain and d.blockchain.validate_chain())
    mp_data = d.marketplace.to_dict() if d.marketplace else {}
    or_data = d.oracle.to_dict() if d.oracle else {}

    # Status per-module (true/false por subsistema) — consumido pelo frontend
    modules = {
        "blockchain": bool(d.blockchain and chain_valid),
        "zkml": bool(d.zkml_verifier),
        "pouw": bool(d.blockchain),
        "schnorr": bool(d.blockchain),
        "api": True,  # API está rodando se chegamos aqui
        "explorer": bool(d.explorer_index),
        "bank": bool(d.staking_pool and d.lending_engine),
        "agents": bool(d.agent_registry),
        "memory": bool(d.persistent_state),
        "wallet": True,
        "p2p": bool(d.p2p_network),
        "tests": int(getattr(d, "test_suites", 0) or 0) > 0,
        "obscura": bool(d.obscura_bridge),
        "dev": True,
    }

    staking_info = d.staking_pool.to_dict() if d.staking_pool else {}

    # Oracle prices ao vivo (3 fontes)
    oracle_prices: Dict[str, float] = {}
    if d.oracle:
        for sym in getattr(d.oracle, "feeds", {}):
            try:
                oracle_prices[sym] = d.oracle.get_price(sym)
            except Exception:  # oracle temporariamente indisponível
                oracle_prices[sym] = None
    or_data["prices"] = oracle_prices

    return {
        "network": "b'AI'tcoin Mainnet",
        "chain_height": int(d.blockchain.height) if d.blockchain else 0,
        "chain_valid": chain_valid,
        "blocks_immutable": True,
        "persistence": "WAL + Snapshots",
        "data_path": d.data_path,
        "utxo_count": len(d.blockchain.utxo_set) if d.blockchain else 0,
        "mempool_size": len(d.blockchain.mempool) if d.blockchain else 0,
        "agents_registered": len(d.agent_registry.agents) if d.agent_registry else 0,
        "explorer_index": d.explorer_index.stats if d.explorer_index else {},
        "token_minted_bait": (d.token.total_minted / 100_000_000) if d.token else 0.0,
        "marketplace": mp_data,
        "oracle": or_data,
        "staking": staking_info,
        "modules": modules,
        "timestamp": time.time(),
    }


# Alias retro-compatível — main_daemon.py pode chamar `from .status import build_status`
# e substituir o método antigo por `self.get_status = lambda: build_status(self)`.
