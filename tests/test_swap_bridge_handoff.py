import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_bridge.manager import BridgeManager
from native_processing.bridge_handoff import BridgeHandoffError, SwapBridgeHandoff
from native_processing.swap_engine import SwapEngine
from native_processing.swap_protocol import sign_quote


def make_intent(tmp_path):
    engine = SwapEngine(str(tmp_path / "swap.sqlite"), quote_ttl_seconds=120)
    now = time.time()
    quote = engine.quote("sell_bait", 100_000, 10_000_000, now=now)
    intent = sign_quote(
        quote,
        "maker-e2e",
        Ed25519PrivateKey.generate(),
        "bridge-e2e-1",
        now=now,
    )
    return engine, intent


def test_swap_intent_lock_proof_mint_e2e(tmp_path):
    engine, intent = make_intent(tmp_path)
    bridge = BridgeManager()
    handoff = SwapBridgeHandoff(bridge, str(tmp_path / "handoff.sqlite"))
    try:
        locked = handoff.start_lock(intent, target_chain_id=1, recipient="0xrecipient")
        assert locked["success"] is True
        assert locked["amount_sats"] == intent.btc_sats
        assert locked["state"] == "locked"
        assert bridge.get_stats()["total_transfers"] == 1

        repeated = handoff.start_lock(intent, target_chain_id=1, recipient="0xrecipient")
        assert repeated["transfer_id"] == locked["transfer_id"]
        assert bridge.get_stats()["total_transfers"] == 1

        signatures = [(f"signer_{i}", f"proof-signature-{i}") for i in range(3)]
        pending_1 = handoff.submit_proof_and_mint(
            intent.order_id,
            proof=locked["merkle_proof"],
            signatures=[signatures[0]],
        )
        assert pending_1["handoff_state"] == "pending_proof"
        assert pending_1["signatures"] == 1
        pending_2 = handoff.submit_proof_and_mint(
            intent.order_id,
            proof=locked["merkle_proof"],
            signatures=[signatures[1]],
        )
        assert pending_2["handoff_state"] == "pending_proof"
        assert pending_2["signatures"] == 2
        minted = handoff.submit_proof_and_mint(
            intent.order_id,
            proof=locked["merkle_proof"],
            signatures=[signatures[2]],
        )
        assert minted["success"] is True
        assert minted["wrapped_token"] == "wBAIT"
        assert minted["mint_amount_sats"] == intent.btc_sats

        minted_again = handoff.submit_proof_and_mint(
            intent.order_id,
            proof=locked["merkle_proof"],
            signatures=signatures,
        )
        assert minted_again["event_id"] == minted["event_id"]
        direct_again = bridge.mint_wrapped(locked["event_id"])
        assert direct_again["idempotent"] is True
        assert bridge.get_stats()["total_minted_bait"] == intent.btc_sats / 100_000_000
        assert handoff.get(intent.order_id)["handoff_state"] == "minted"
    finally:
        handoff.close()
        engine.close()


def test_handoff_rejects_conflicting_request_and_unknown_order(tmp_path):
    engine, intent = make_intent(tmp_path)
    bridge = BridgeManager()
    handoff = SwapBridgeHandoff(bridge)
    try:
        handoff.start_lock(intent, target_chain_id=1, recipient="0xrecipient")
        with pytest.raises(BridgeHandoffError, match="different bridge request"):
            handoff.start_lock(intent, target_chain_id=1, recipient="0xother")
        with pytest.raises(BridgeHandoffError, match="unknown order_id"):
            handoff.submit_proof_and_mint("missing", proof=[], signatures=[])
    finally:
        handoff.close()
        engine.close()


def test_handoff_does_not_lock_expired_or_tampered_intent(tmp_path):
    engine = SwapEngine(str(tmp_path / "swap.sqlite"), quote_ttl_seconds=1)
    now = 100.0
    quote = engine.quote("sell_bait", 100_000, 10_000_000, now=now)
    private = Ed25519PrivateKey.generate()
    intent = sign_quote(quote, "maker-expired", private, "expired", now=now)
    bridge = BridgeManager()
    handoff = SwapBridgeHandoff(bridge)
    try:
        with pytest.raises(BridgeHandoffError, match="invalid swap intent"):
            handoff.start_lock(intent, target_chain_id=1, recipient="0xrecipient", now=1000)
        tampered = {**intent.to_dict(), "btc_sats": 200_000}
        with pytest.raises(BridgeHandoffError, match="invalid swap intent"):
            handoff.start_lock(tampered, target_chain_id=1, recipient="0xrecipient", now=100)
        assert bridge.get_stats()["total_transfers"] == 0
    finally:
        handoff.close()
        engine.close()
