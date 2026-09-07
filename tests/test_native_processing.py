import base64
import json
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from native_processing.integration import verify_webhook_body
from native_processing.swap_engine import SwapEngine, SwapError
from native_processing.swap_protocol import IntentError, sign_quote
from baitcoin_core.network.gossip import GossipMessageType, GossipProtocol
from native_processing.webhook_auth import AuthError, EventEnvelope, WebhookAuthenticator, payload_hash


def make_envelope(private, seq=1, event_id="evt-1", payload=None, created_at=None, expires_at=None):
    created_at = time.time() if created_at is None else created_at
    expires_at = created_at + 100 if expires_at is None else expires_at
    payload = payload or {"amount": 7, "asset": "BAIT"}
    raw = dict(version=1, event_id=event_id, source_node="node-a", event_type="swap.created",
               created_at=created_at, expires_at=expires_at, sequence=seq, key_id="k1",
               payload=payload, payload_hash=payload_hash(payload))
    unsigned = EventEnvelope.from_dict({**raw, "signature": "AA=="})
    raw["signature"] = base64.b64encode(private.sign(unsigned.signing_bytes())).decode()
    return raw


def setup_auth(tmp_path):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    registry = tmp_path / "keys.json"
    registry.write_text(json.dumps({"version": 1, "keys": {"k1": {
        "node_id": "node-a", "status": "active",
        "public_key_b64": base64.b64encode(public).decode(),
        "not_before": 0, "valid_until": 10**12}}}))
    auth = WebhookAuthenticator(str(registry), str(tmp_path / "state.db"), max_skew_seconds=5, max_ttl_seconds=200)
    return private, auth


def test_accepts_and_is_idempotent(tmp_path):
    private, auth = setup_auth(tmp_path)
    body = make_envelope(private)
    assert verify_webhook_body(body, auth)[1] is False
    assert verify_webhook_body(body, auth)[1] is True
    auth.close()


def test_rejects_tamper_and_replay(tmp_path):
    private, auth = setup_auth(tmp_path)
    body = make_envelope(private)
    body["payload"]["amount"] = 8
    with pytest.raises(AuthError):
        verify_webhook_body(body, auth)
    now = time.time()
    assert auth.authenticate_and_record(EventEnvelope.from_dict(make_envelope(private, seq=1, event_id="evt-a", created_at=now, expires_at=now + 100)), now=now)[1] == "accepted"
    with pytest.raises(AuthError, match="replayed"):
        auth.authenticate_and_record(EventEnvelope.from_dict(make_envelope(private, seq=1, event_id="evt-b", created_at=now, expires_at=now + 100)), now=now)
    auth.close()


def test_rejects_expired_and_long_ttl(tmp_path):
    private, auth = setup_auth(tmp_path)
    with pytest.raises(AuthError, match="expired"):
        auth.authenticate_and_record(EventEnvelope.from_dict(make_envelope(private, event_id="expired", created_at=1, expires_at=2)), now=1000)
    with pytest.raises(AuthError, match="TTL"):
        auth.authenticate_and_record(EventEnvelope.from_dict(make_envelope(private, event_id="long", created_at=1000, expires_at=1400)), now=1000)
    auth.close()


def test_swap_order_idempotency(tmp_path):
    engine = SwapEngine(str(tmp_path / "swap.db"), quote_ttl_seconds=30)
    quote = engine.quote("buy_bait", 100_000, 2_000_000, now=100)
    first = engine.place_order(quote, "client-1", now=101)
    second = engine.place_order(quote, "client-1", now=101)
    assert first == second
    with pytest.raises(SwapError):
        engine.place_order(engine.quote("buy_bait", 100_000, 2_000_000, now=100), "client-1", now=101)
    engine.close()


def test_signed_swap_intent_is_validated_by_any_node(tmp_path):
    engine = SwapEngine(str(tmp_path / "swap.db"), quote_ttl_seconds=30)
    private = Ed25519PrivateKey.generate()
    now = 100.0
    quote = engine.quote("sell_bait", 50_000, 1_000_000, now=now)
    intent = sign_quote(quote, "maker-a", private, "client-a", now=101)
    assert intent.verify(now=101)
    tampered = {**intent.to_dict(), "bait_units": 2_000_000}
    with pytest.raises(IntentError):
        type(intent).from_dict(tampered).verify(now=101)
    engine.close()


def test_concurrent_idempotent_placement_has_one_order(tmp_path):
    engine = SwapEngine(str(tmp_path / "swap.db"), quote_ttl_seconds=30)
    quote = engine.quote("buy_bait", 100_000, 2_000_000, now=100)
    with ThreadPoolExecutor(max_workers=8) as pool:
        orders = list(pool.map(lambda _: engine.place_order(quote, "same-client", now=101), range(32)))
    assert len({order.order_id for order in orders}) == 1
    assert engine.get_order("same-client") == orders[0]
    engine.close()


def test_swap_intent_gossip_round_trip_and_deduplication():
    engine = SwapEngine(":memory:", quote_ttl_seconds=30)
    private = Ed25519PrivateKey.generate()
    now = time.time()
    quote = engine.quote("buy_bait", 100_000, 2_000_000, now=now)
    intent = sign_quote(quote, "maker-gossip", private, "client-gossip", now=now)
    origin = GossipProtocol("node-a")
    receiver = GossipProtocol("node-b")
    message = origin.create_swap_intent_message(intent.to_dict())
    raw = origin.serialize(message)
    received = receiver.receive(raw)
    assert received[0].msg_type is GossipMessageType.SWAP_INTENT
    assert GossipProtocol.validate_swap_intent_message(received[0]).order_id == intent.order_id
    assert receiver.receive(raw) == []
    engine.close()
