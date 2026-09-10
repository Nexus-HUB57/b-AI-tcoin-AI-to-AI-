import base64
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_bridge.authorization import RelayerAuthorization
from baitcoin_bridge.config import BridgeConfig
from baitcoin_bridge.manager import BridgeManager
from scripts.lnd_channel_rotation import LndConnection, LndChannelRotationError, LndGrpcConnectionManager
from scripts.macaroon_rotation import RotatingMacaroonProvider


class FakeChannel:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeLightning:
    def __init__(self, network="mainnet"):
        self.network = network

    def GetInfo(self, timeout=None):
        return SimpleNamespace(identity_pubkey="02" + "22" * 32, chains=[SimpleNamespace(network=self.network)])


def test_bridge_manager_rejects_bad_signature_before_mutation():
    key = Ed25519PrivateKey.generate()
    auth = RelayerAuthorization({"relayer-a": base64.b64encode(key.public_key().public_bytes_raw()).decode()})
    manager = BridgeManager(BridgeConfig(n_of_m_threshold=1, m_signers=1), relayer_authorization=auth)
    locked = manager.lock_bait("agent", 100_000, 1, "recipient")
    assert locked["success"] is True
    event = manager._events[locked["event_id"]]
    before = list(event.signatures)
    rejected = manager.submit_proof(locked["event_id"], locked["merkle_proof"], "relayer-a", base64.b64encode(b"bad").decode())
    assert rejected["error"] == "invalid_relayer_signature"
    assert event.signatures == before


def test_bridge_manager_accepts_valid_individual_signature():
    key = Ed25519PrivateKey.generate()
    auth = RelayerAuthorization({"relayer-a": base64.b64encode(key.public_key().public_bytes_raw()).decode()})
    manager = BridgeManager(BridgeConfig(n_of_m_threshold=1, m_signers=1), relayer_authorization=auth)
    locked = manager.lock_bait("agent", 100_000, 1, "recipient")
    signature = auth.sign(key, locked["event_id"], locked["transfer_id"], 1, 100_000, locked["merkle_proof"])
    accepted = manager.submit_proof(locked["event_id"], locked["merkle_proof"], "relayer-a", signature)
    assert accepted["ready_to_mint"] is True
    assert accepted["signatures"] == 1


def test_lnd_rotation_reconnects_and_closes_old_session(tmp_path):
    provider = RotatingMacaroonProvider(tmp_path / "lnd.macaroon")
    provider.stage(b"old")
    provider.activate()
    created = []

    def factory(current_provider):
        channel = FakeChannel()
        connection = LndConnection(channel, FakeLightning(), object(), "mainnet", "")
        created.append((current_provider.load(), connection))
        return connection

    manager = LndGrpcConnectionManager(provider, factory)
    old = manager.initialize()
    current = manager.activate_and_reconnect(b"new")
    assert current is manager.current()
    assert created[-1][0] == b"new"
    assert old.channel.closed is True
    assert provider.load() == b"new"
    manager.close()


def test_lnd_rotation_rolls_back_when_revalidation_fails(tmp_path):
    provider = RotatingMacaroonProvider(tmp_path / "lnd.macaroon")
    provider.stage(b"old")
    provider.activate()
    created = []

    def factory(current_provider):
        channel = FakeChannel()
        network = "testnet" if current_provider.load() == b"bad" else "mainnet"
        connection = LndConnection(channel, FakeLightning(network), object(), network, "")
        created.append(connection)
        return connection

    manager = LndGrpcConnectionManager(provider, factory)
    old = manager.initialize()
    with pytest.raises(LndChannelRotationError):
        manager.activate_and_reconnect(b"bad")
    assert provider.load() == b"old"
    assert manager.current() is old
    assert old.channel.closed is False
    manager.close()
