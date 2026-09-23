from dataclasses import dataclass

import pytest

from baith_exchange.obscura import BaithObscuraCoordinator, ObscuraEvidenceError
from baith_exchange.service import BaithExchange, ExchangeConfig
from baith_policy.engine import OutputIntent, TransactionIntent, make_mainnet_policy


DEST = "bc1qdestination"
CHANGE = "bc1qchange"
RAW = "0200000001"  # shape-only deterministic unsigned payload for policy tests


@dataclass
class FakeObscuraResult:
    status: str
    content: str
    title: str = ""


class FakeObscura:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def fetch_page(self, url, *, agent_id="", **kwargs):
        self.calls.append((url, agent_id, kwargs))
        return self.result


def make_intent(request_id="req-obscura-0001"):
    return TransactionIntent(
        request_id=request_id,
        network="bitcoin-mainnet",
        inputs=("a" * 64 + ":0",),
        outputs=(
            OutputIntent(DEST, 100_000),
            OutputIntent(CHANGE, 50_000, "change"),
        ),
        fee_sats=100,
        fee_rate_sat_vb=2,
        unsigned_tx_hex=RAW,
        policy_id="btc-mainnet-v1",
    )


def make_coordinator(provider):
    policy = make_mainnet_policy("btc-mainnet-v1", DEST, CHANGE)
    exchange = BaithExchange(ExchangeConfig(CHANGE, "btc-mainnet-v1"), policy)
    return BaithObscuraCoordinator(exchange, provider)


def test_baith_obscura_prepare_records_content_provenance():
    provider = FakeObscura(FakeObscuraResult("success", "price=42; source=oracle", "Oracle"))
    coordinator = make_coordinator(provider)

    prepared = coordinator.prepare_with_evidence(
        make_intent(), "https://oracle.example/price", agent_id="agent-obscura"
    )

    assert prepared["status"] == "prepared"
    assert prepared["signing_enabled"] is False
    assert prepared["broadcast_enabled"] is False
    evidence = prepared["obscura_evidence"]
    assert evidence["url"] == "https://oracle.example/price"
    assert evidence["agent_id"] == "agent-obscura"
    assert evidence["content_length"] == len("price=42; source=oracle")
    assert len(evidence["content_sha256"]) == 64
    assert provider.calls == [("https://oracle.example/price", "agent-obscura", {})]


def test_baith_obscura_rejects_failed_or_empty_evidence_before_prepare():
    for result in (
        FakeObscuraResult("error", "unavailable"),
        FakeObscuraResult("success", ""),
    ):
        coordinator = make_coordinator(FakeObscura(result))
        with pytest.raises(ObscuraEvidenceError):
            coordinator.prepare_with_evidence(make_intent(), "https://oracle.example/price")


def test_baith_obscura_rejects_non_http_source():
    coordinator = make_coordinator(FakeObscura(FakeObscuraResult("success", "ok")))
    with pytest.raises(ObscuraEvidenceError, match="HTTP"):
        coordinator.prepare_with_evidence(make_intent(), "file:///tmp/source")


def test_baith_obscura_does_not_enable_signing_or_broadcast():
    provider = FakeObscura(FakeObscuraResult("success", "ok"))
    coordinator = make_coordinator(provider)
    prepared = coordinator.prepare_with_evidence(make_intent(), "https://oracle.example/price")
    assert prepared["signing_enabled"] is False
    assert prepared["broadcast_enabled"] is False
