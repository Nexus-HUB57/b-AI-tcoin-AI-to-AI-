import pytest

from baith_exchange import BaithExchange, ExchangeConfig, ExchangeError
from baith_policy import OutputIntent, PolicyError, TransactionIntent, make_mainnet_policy

DEST = "bc1qwwgdhzdgy97ysqqtd9z7rwv76fwktg0w4tvwf8"
CHANGE = "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ"
RAW = "0200000001cffbbc6e9cc08943fe296eaaca4691e817a1e526f6ef630c89821a5ab7bed67c0400000000ffffffff0260ca580e000000001600147390db89a8217c48000b6945e1b99ed25d65a1ee7122d37a010000001976a914cd6873e52bf10ece88364fc277951c05475b07f788ac00000000"


def intent(**overrides):
    data = dict(request_id="req-20260923-0001", network="bitcoin-mainnet", inputs=("cffbbc6e9cc08943fe296eaaca4691e817a1e526f6ef630c89821a5ab7bed67c:4",), outputs=(OutputIntent(DEST, 240700000), OutputIntent(CHANGE, 6355624561, "change")), fee_sats=224, fee_rate_sat_vb=1, unsigned_tx_hex=RAW, policy_id="btc-mainnet-v1")
    data.update(overrides)
    return TransactionIntent(**data)


def service():
    p = make_mainnet_policy("btc-mainnet-v1", DEST, CHANGE)
    return BaithExchange(ExchangeConfig(CHANGE, "btc-mainnet-v1"), p), p


def test_mainnet_prepare_is_deterministic_and_fail_closed():
    exchange, _ = service()
    result = exchange.validate_and_prepare(intent())
    assert result["status"] == "prepared"
    assert result["signing_enabled"] is False
    assert result["broadcast_enabled"] is False
    with pytest.raises(ExchangeError, match="signing is disabled"):
        exchange.sign(intent(request_id="req-20260923-0002"))


def test_non_mainnet_is_rejected():
    _, policy = service()
    with pytest.raises(PolicyError, match="Mainnet-only"):
        policy.validate(intent(network="regtest"))


def test_destination_and_change_are_allowlisted():
    _, policy = service()
    with pytest.raises(PolicyError, match="destination"):
        policy.validate(intent(outputs=(OutputIntent("bc1qnotallowed", 240700000), OutputIntent(CHANGE, 6355624561, "change"))))
    with pytest.raises(PolicyError, match="change"):
        policy.validate(intent(outputs=(OutputIntent(DEST, 240700000), OutputIntent("1NotAllowed", 6355624561, "change"))))


def test_duplicate_request_is_rejected():
    exchange, _ = service()
    exchange.validate_and_prepare(intent())
    with pytest.raises(ExchangeError, match="duplicate"):
        exchange.validate_and_prepare(intent())
