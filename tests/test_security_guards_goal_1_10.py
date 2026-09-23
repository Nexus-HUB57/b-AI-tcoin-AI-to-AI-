import os

import pytest

from baitcoin_bridge.manager import BridgeManager
from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory


def test_bridge_requires_authorization_outside_explicit_local_mode(monkeypatch):
    monkeypatch.delenv("BAIT_ALLOW_INSECURE_LOCAL", raising=False)
    with pytest.raises(ValueError, match="RelayerAuthorization is required"):
        BridgeManager()


def test_marketplace_rejects_non_positive_listing_price():
    marketplace = AIMarketplace()
    with pytest.raises(ValueError, match="positive integer"):
        marketplace.list_service("provider", ServiceCategory.ML_INFERENCE, "svc", "desc", 0)
    with pytest.raises(ValueError, match="positive integer"):
        marketplace.list_service("provider", ServiceCategory.ML_INFERENCE, "svc", "desc", -1)


def test_marketplace_purchase_is_pending_until_external_settlement():
    marketplace = AIMarketplace()
    listing_id = marketplace.list_service("provider", ServiceCategory.ML_INFERENCE, "svc", "desc", 100)
    purchase_id = marketplace.purchase_service(listing_id, "buyer")
    assert purchase_id is not None
    purchase = marketplace.purchases[purchase_id]
    assert purchase.status == "pending_settlement"
    assert marketplace.rate_service(purchase_id, 5.0) is False
    assert marketplace.settle_purchase(purchase_id, "a" * 64, 1) is True
    assert marketplace.rate_service(purchase_id, 5.0) is True
    assert marketplace.rate_service(purchase_id, 4.0) is False


def test_marketplace_rejects_fake_settlement_txid():
    marketplace = AIMarketplace()
    listing_id = marketplace.list_service("provider", ServiceCategory.ML_INFERENCE, "svc", "desc", 100)
    purchase_id = marketplace.purchase_service(listing_id, "buyer")
    assert marketplace.settle_purchase(purchase_id, "pending-broadcast", 1) is False
