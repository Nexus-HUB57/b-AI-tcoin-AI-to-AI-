from baitcoin_core.blockchain.block import Transaction, TransactionOutput
from baitcoin_core.blockchain.fees import FeeEstimator, FeeMarket
from tools.hsm_signing_e2e_dry_run import run_rejection_simulation


def tx(payload: bytes) -> Transaction:
    return Transaction(tx_type="transfer", outputs=[TransactionOutput(1, b"dest")], payload=payload)


def test_dynamic_fee_targets_use_recent_block_history_and_floor():
    estimator = FeeEstimator(min_fee_rate=1)
    assert estimator.estimate_fee(1) == 10
    for rate in (2, 4, 8, 16):
        estimator.record_block_fees(rate)
    assert estimator.estimate_fee(1) == 8
    assert estimator.estimate_fee(3) == 4
    assert estimator.estimate_fee(6) == 2


def test_fee_market_prioritizes_highest_sat_vb_and_rejects_out_of_bounds():
    market = FeeMarket(min_fee_rate=2)
    low = tx(b"low")
    high = tx(b"high")
    assert market.add_transaction(low, fee_rate=2)[0]
    assert market.add_transaction(high, fee_rate=20)[0]
    selected, _total, median = market.select_transactions()
    assert selected[0] is high
    assert median == 20
    assert market.add_transaction(tx(b"too-low"), fee_rate=1)[0] is False
    assert market.add_transaction(tx(b"too-high"), fee_rate=1_000_001)[0] is False


def test_hsm_rejection_pauses_without_mutation_or_broadcast():
    result = run_rejection_simulation()
    assert result == {
        "state": "signing_rejected",
        "error": "HSM_REJECTED: policy denied test key operation",
        "broadcast_attempted": False,
        "mutation": "none",
        "action": "pause_and_alert",
    }
