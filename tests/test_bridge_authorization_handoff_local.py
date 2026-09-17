import base64
import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_bridge.authorization import RelayerAuthorization
from baitcoin_bridge.manager import BridgeManager
from native_processing.bridge_handoff import BridgeHandoffError, SwapBridgeHandoff
from native_processing.swap_engine import SwapEngine
from native_processing.swap_protocol import sign_quote


def test_handoff_verifies_each_relayer_before_bridge_submission(tmp_path):
    engine = SwapEngine(str(tmp_path / "swap.sqlite"), quote_ttl_seconds=120)
    now = time.time()
    quote = engine.quote("sell_bait", 100_000, 10_000_000, now=now)
    intent = sign_quote(quote, "maker-auth", Ed25519PrivateKey.generate(), "handoff-auth", now=now)
    key = Ed25519PrivateKey.generate()
    auth = RelayerAuthorization({"relayer-a": base64.b64encode(key.public_key().public_bytes_raw()).decode()})
    bridge = BridgeManager()
    handoff = SwapBridgeHandoff(bridge, str(tmp_path / "handoff.sqlite"), authorizer=auth)
    try:
        locked = handoff.start_lock(intent, target_chain_id=1, recipient="0xrecipient", now=now)
        with pytest.raises(BridgeHandoffError, match="proof authorization failed"):
            handoff.submit_proof_and_mint(
                intent.order_id,
                proof=locked["merkle_proof"],
                signatures=[("relayer-a", base64.b64encode(b"bad").decode())],
            )
        assert bridge._events[locked["event_id"]].signatures == []
        signature = auth.sign(key, locked["event_id"], locked["transfer_id"], 1, intent.btc_sats, locked["merkle_proof"])
        accepted = handoff.submit_proof_and_mint(
            intent.order_id,
            proof=locked["merkle_proof"],
            signatures=[("relayer-a", signature)],
        )
        assert accepted["signatures"] == 1
    finally:
        handoff.close()
        engine.close()
