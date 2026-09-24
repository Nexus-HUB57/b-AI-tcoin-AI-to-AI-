import pytest

from baith_exchange.service import BaithExchange, ExchangeConfig
from baith_policy.engine import OutputIntent, TransactionIntent, make_mainnet_policy
from funddecana import AtomicCycleError, CustodyAsset, FundManifest, FundReadOnlyCoordinator


BTC_DEST = "bc1qfunddestination"
BTC_CHANGE = "bc1qfundchange"


def make_manifest(environment="mainnet", broadcast_enabled=False):
    return FundManifest(
        fund_id="funddecana-my",
        environment=environment,
        assets=(
            CustodyAsset("BTC", "bitcoin-mainnet", "bc1qfundcustody000000000000000000000000"),
            CustodyAsset("ETH", "ethereum-mainnet", "0x0000000000000000000000000000000000000001"),
            CustodyAsset("BAIT", "bait-mainnet", "bait-custody-ledger"),
        ),
        multisig_threshold="3-of-5",
        signer_external=True,
        broadcast_enabled=broadcast_enabled,
    )


def make_coordinator():
    policy = make_mainnet_policy("btc-mainnet-v1", BTC_DEST, BTC_CHANGE)
    exchange = BaithExchange(ExchangeConfig(BTC_CHANGE, "btc-mainnet-v1"), policy)
    return FundReadOnlyCoordinator(exchange)


def make_intent():
    return TransactionIntent(
        request_id="fund-cycle-0001",
        network="bitcoin-mainnet",
        inputs=("a" * 64 + ":0",),
        outputs=(OutputIntent(BTC_DEST, 100_000), OutputIntent(BTC_CHANGE, 50_000, "change")),
        fee_sats=100,
        fee_rate_sat_vb=2,
        unsigned_tx_hex="0200000001",
        policy_id="btc-mainnet-v1",
    )


def test_prepare_cycle_is_read_only_and_hashes_record():
    result = make_coordinator().prepare_cycle(
        make_manifest(), sweep_observation={"status": "planned", "plans": 0}, btc_intent=make_intent()
    )
    assert result["status"] == "prepared_read_only"
    assert result["signing_performed"] is False
    assert result["broadcast_performed"] is False
    assert result["capital_moved"] is False
    assert len(result["audit_sha256"]) == 64
    assert result["baith_hex"]["broadcast_enabled"] is False


def test_testnet_does_not_prepare_mainnet_baith_hex_intent():
    with pytest.raises(AtomicCycleError, match="mainnet-only"):
        make_coordinator().prepare_cycle(
            make_manifest(environment="testnet"), sweep_observation={}, btc_intent=make_intent()
        )


def test_broadcast_cannot_be_enabled_in_read_only_coordinator():
    with pytest.raises(AtomicCycleError, match="broadcast"):
        make_coordinator().prepare_cycle(make_manifest(broadcast_enabled=True), sweep_observation={})


def test_unverified_eth_address_is_still_validated_as_an_address_but_not_claimed_verified():
    manifest = make_manifest()
    eth = next(asset for asset in manifest.assets if asset.symbol == "ETH")
    assert eth.verified_on_chain is False
    manifest.validate()
