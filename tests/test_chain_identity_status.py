from __future__ import annotations

import pytest

from main_daemon import get_chain_identity


class FakeHash:
    def __init__(self, value: str):
        self._value = value

    def hex(self) -> str:
        return self._value


class FakeBlock:
    def __init__(self, value: str):
        self.block_hash = FakeHash(value)


class FakeChain:
    def __init__(self, genesis: str, tip: str):
        self.chain = [FakeBlock(genesis), FakeBlock(tip)]
        self.last_block = self.chain[-1]


def test_returns_canonical_tip_and_genesis_hashes():
    genesis = "a" * 64
    tip = "b" * 64
    assert get_chain_identity(FakeChain(genesis, tip)) == {
        "tip_hash": tip,
        "genesis_hash": genesis,
    }


def test_rejects_missing_chain():
    with pytest.raises(RuntimeError, match="no blocks"):
        get_chain_identity(None)


def test_rejects_invalid_hash_length():
    with pytest.raises(RuntimeError, match="invalid block hash length"):
        get_chain_identity(FakeChain("a", "b" * 64))
