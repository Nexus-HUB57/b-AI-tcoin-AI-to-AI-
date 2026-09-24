import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_bridge.authorization import RelayerAuthorization
from baitcoin_bridge.manager import BridgeManager
from baitcoin_bridge.relayer import Relayer, RelayerConfig


def test_relayer_submits_only_individually_verified_signature():
    manager = BridgeManager()
    key = Ed25519PrivateKey.generate()
    signer_id = "relayer-auth-test"
    authorization = RelayerAuthorization({
        signer_id: base64.b64encode(key.public_key().public_bytes_raw()).decode()
    })
    relayer = Relayer(manager, RelayerConfig(relayer_id=signer_id), authorization, key)
    lock = manager.lock_bait("maker", 100_000, 1, "0xrecipient")

    result = relayer.relay_event(lock["event_id"])

    assert result["success"] is True
    assert result["manager_result"]["signatures"] == 1
    assert manager._events[lock["event_id"]].signatures[0].startswith(f"{signer_id}:")


def test_relayer_without_authorization_cannot_mutate_bridge():
    manager = BridgeManager()
    relayer = Relayer(manager, RelayerConfig(relayer_id="unauthorized"))
    lock = manager.lock_bait("maker", 100_000, 1, "0xrecipient")

    result = relayer.relay_event(lock["event_id"])

    assert result == {"error": "authorization_required"}
    assert manager._events[lock["event_id"]].signatures == []
    assert manager._events[lock["event_id"]].state == "locked"
