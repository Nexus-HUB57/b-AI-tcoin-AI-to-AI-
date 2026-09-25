"""Tests unitários para baitcoin_core.daemon.status (audit 2026-09-22)."""
from __future__ import annotations
import pytest
from types import SimpleNamespace

from baitcoin_core.daemon.status import build_status


def _daemon(**overrides):
    """Constrói um stub mínimo que satisfaz o Protocol _HasModules."""
    base = dict(
        blockchain=SimpleNamespace(
            height=34953,
            utxo_set={f"tx{i}": i for i in range(100)},
            mempool=[],
            validate_chain=lambda: True,
        ),
        marketplace=SimpleNamespace(to_dict=lambda: {"products": 1504}),
        oracle=SimpleNamespace(
            to_dict=lambda: {"oracles": 3},
            feeds={"BTC": "coingecko", "ETH": "binance"},
            get_price=lambda s: {"BTC": 75639.0, "ETH": 2394.68}.get(s),
        ),
        zkml_verifier=SimpleNamespace(),
        staking_pool=SimpleNamespace(to_dict=lambda: {"apy": 7.0}),
        lending_engine=SimpleNamespace(),
        agent_registry=SimpleNamespace(agents={f"agent{i}": i for i in range(35)}),
        explorer_index=SimpleNamespace(stats={"blocks": 34954}),
        p2p_network=SimpleNamespace(),
        obscura_bridge=SimpleNamespace(),
        persistent_state=True,
        token=SimpleNamespace(total_minted=174765000000000000),
        data_path="/tmp/baitcoin-test",
        test_suites=4,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_status_returns_full_payload():
    s = build_status(_daemon())
    assert s["network"] == "b'AI'tcoin Mainnet"
    assert s["chain_height"] == 34953
    assert s["chain_valid"] is True
    assert s["utxo_count"] == 100
    assert s["mempool_size"] == 0
    assert s["agents_registered"] == 35
    assert s["marketplace"]["products"] == 1504
    assert s["oracle"]["prices"]["BTC"] == 75639.0
    assert "timestamp" in s


def test_build_status_modules_all_true_when_components_present():
    s = build_status(_daemon())
    for k, v in s["modules"].items():
        assert v is True, f"module {k} expected True, got {v}"


def test_build_status_graceful_when_blockchain_none():
    s = build_status(_daemon(blockchain=None))
    assert s["chain_height"] == 0
    assert s["chain_valid"] is False
    assert s["utxo_count"] == 0
    assert s["modules"]["blockchain"] is False


def test_build_status_graceful_when_oracle_fails():
    """Se get_price joga, prices[sym] = None — não crasha o daemon."""
    def bad_get_price(sym):
        raise RuntimeError("oracle offline")
    d = _daemon()
    d.oracle.get_price = bad_get_price
    s = build_status(d)
    assert s["oracle"]["prices"]["BTC"] is None
    assert s["oracle"]["prices"]["ETH"] is None


def test_build_status_no_oracle():
    s = build_status(_daemon(oracle=None))
    assert s["oracle"]["prices"] == {}


def test_build_status_mempool_count():
    d = _daemon()
    d.blockchain.mempool = ["tx1", "tx2", "tx3"]
    s = build_status(d)
    assert s["mempool_size"] == 3


def test_build_status_token_minted_bait():
    s = build_status(_daemon())
    assert s["token_minted_bait"] == pytest.approx(1747650000.0)


def test_build_status_timestamp_is_float():
    s = build_status(_daemon())
    assert isinstance(s["timestamp"], float)
    assert s["timestamp"] > 0


def test_build_status_no_obscura_bridge():
    """obscura_bridge=None → módulo obscura=False (não crasha)."""
    s = build_status(_daemon(obscura_bridge=None))
    assert s["modules"]["obscura"] is False


def test_build_status_idempotent():
    """Chamar 2x deve dar mesmo shape (sem mutação)."""
    s1 = build_status(_daemon())
    s2 = build_status(_daemon())
    assert set(s1.keys()) == set(s2.keys())
    assert s1["network"] == s2["network"]
    # timestamp muda, mas outras keys estáveis
    assert s1["chain_height"] == s2["chain_height"]
