from scripts.validate_mybait_live_e2e import classify


def test_status_is_observed_but_not_claimed_as_bitcoin_mainnet():
    result = classify(
        "/api/v1/status",
        200,
        {
            "network": "b'AI'tcoin Mainnet",
            "version": "0.8.0-live",
            "chain_height": 45104,
            "chain_valid": True,
            "utxo_count": 45105,
            "mempool_size": 0,
            "agents_registered": 5,
        },
    )
    assert result.ok is True
    assert result.classification == "OBSERVED"
    assert result.detail["network"] == "b'AI'tcoin Mainnet"


def test_explorer_coinbase_only_does_not_claim_settlement():
    result = classify(
        "/api/v1/explorer/txs/latest",
        200,
        {"transactions": [{"tx_type": "coinbase"}, {"tx_type": "coinbase"}]},
    )
    assert result.ok is True
    assert result.detail["non_coinbase_count"] == 0
    assert result.detail["tx_types"] == ["coinbase"]


def test_swap_book_is_matching_only_observation():
    result = classify(
        "/api/v1/swap/book",
        200,
        {"orders": [{"status": "filled"}], "trades": [{}], "master_pool": 0},
    )
    assert result.ok is True
    assert result.classification == "OBSERVED_MATCHING_ONLY"
    assert result.detail["master_pool"] == 0


def test_bad_http_status_fails_closed():
    result = classify("/api/v1/health", 503, {"status": "unavailable"})
    assert result.ok is False
    assert result.classification == "FAIL"


def test_openapi_shape_is_observed():
    result = classify(
        "/mylink/openapi.json",
        200,
        {"openapi": "3.1.0", "info": {"version": "0.8.0-live"}, "paths": {}},
    )
    assert result.ok is True
    assert result.detail["api_version"] == "0.8.0-live"
