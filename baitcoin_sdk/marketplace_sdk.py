r"""
Marketplace SDK - Busca e compra de serviços para agentes third-party.
"""
from typing import List, Optional


class MarketplaceSDK:
    def __init__(self, sdk_client):
        self.sdk = sdk_client

    def search(self, category: str = None, max_price: int = None) -> List[dict]:
        r"""Busca serviços no marketplace."""
        if self.sdk._marketplace and self.sdk._local_mode:
            from baitcoin_ai.marketplace.services import ServiceCategory
            cat = ServiceCategory(category) if category else None
            return self.sdk._marketplace.search(cat, max_price)
        return []

    def list_services(self, category: str = None) -> List[dict]:
        return self.search(category)

    def purchase(self, listing_id: str, buyer_agent: str) -> Optional[str]:
        if self.sdk._marketplace and self.sdk._local_mode:
            return self.sdk._marketplace.purchase_service(listing_id, buyer_agent)
        return None

    def rate(self, purchase_id: str, score: float) -> bool:
        if self.sdk._marketplace and self.sdk._local_mode:
            return self.sdk._marketplace.rate_service(purchase_id, score)
        return False

    def get_info(self) -> dict:
        if self.sdk._marketplace and self.sdk._local_mode:
            return self.sdk._marketplace.to_dict()
        return {}
