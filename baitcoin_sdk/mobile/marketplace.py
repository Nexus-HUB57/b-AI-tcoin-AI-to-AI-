r"""MobileMarketplace — AI service marketplace for mobile SDK.

Provides mobile-optimized marketplace operations:
    - Search AI services by category, price, capability
    - Purchase AI services with BAIT
    - Rate and review purchased services
    - List own services (for AI agents acting as providers)

The mobile UX focuses on:
    - Card-based service listings for small screens
    - Category browsing with icon-based navigation
    - One-tap purchase flow
    - Star-rating system for reviews

Usage::

    sdk = BaitcoinMobileSDK()
    services = sdk.marketplace.search(category="ml_inference")
    purchase = sdk.marketplace.purchase("agent_1", "service_42", 50.0)
"""
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class MobileServiceCard:
    r"""Mobile-optimized service listing for card display."""
    service_id: str
    title: str
    provider_id: str
    category: str
    price_bait: float
    rating: float
    review_count: int
    description: str
    capabilities: List[str]
    is_available: bool

    def to_dict(self) -> dict:
        return {
            "service_id": self.service_id,
            "title": self.title,
            "provider_id": self.provider_id,
            "category": self.category,
            "price_bait": self.price_bait,
            "rating": round(self.rating, 1),
            "review_count": self.review_count,
            "description": self.description,
            "capabilities": self.capabilities,
            "is_available": self.is_available,
        }


class MobileMarketplace:
    r"""Mobile marketplace operations."""

    CATEGORIES = [
        {"id": "ml_inference", "label": "ML Inference", "icon": "brain"},
        {"id": "data_processing", "label": "Data Processing", "icon": "database"},
        {"id": "web_scraping", "label": "Web Scraping", "icon": "globe"},
        {"id": "defi_trading", "label": "DeFi Trading", "icon": "chart"},
        {"id": "market_making", "label": "Market Making", "icon": "arrows"},
        {"id": "browser_automation", "label": "Browser Automation", "icon": "window"},
    ]

    def __init__(self, sdk: 'BaitcoinMobileSDK'):
        self._sdk = sdk
        self._local_services: Dict[str, MobileServiceCard] = {}
        self._local_purchases: List[dict] = []

    def search(
        self,
        category: str = None,
        max_price: float = None,
        min_rating: float = None,
        query: str = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        r"""Search marketplace services.

        Parameters
        ----------
        category : str
            Filter by category ID
        max_price : float
            Maximum price in BAIT
        min_rating : float
            Minimum rating (0-5)
        query : str
            Text search in titles and descriptions
        page : int
            Page number (1-based)
        page_size : int
            Results per page (max 50)

        Returns
        -------
        dict
            Search results with pagination
        """
        params = {"page": page, "page_size": min(page_size, 50)}
        if category:
            params["category"] = category
        if max_price is not None:
            params["max_price"] = max_price
        if min_rating is not None:
            params["min_rating"] = min_rating
        if query:
            params["query"] = query

        if not self._sdk._local_mode:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            self._sdk._request("GET", f"/api/v1/marketplace/search?{qs}")

        # Local/offline mode
        results = list(self._local_services.values())
        if category:
            results = [s for s in results if s.category == category]
        if max_price is not None:
            results = [s for s in results if s.price_bait <= max_price]
        if min_rating is not None:
            results = [s for s in results if s.rating >= min_rating]
        if query:
            q = query.lower()
            results = [
                s for s in results
                if q in s.title.lower() or q in s.description.lower()
            ]

        total = len(results)
        start = (page - 1) * page_size
        page_results = results[start:start + page_size]

        return {
            "services": [s.to_dict() for s in page_results],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def purchase(
        self,
        buyer_id: str,
        service_id: str,
        amount_bait: float,
    ) -> dict:
        r"""Purchase an AI service.

        Parameters
        ----------
        buyer_id : str
            Buying agent
        service_id : str
            Service to purchase
        amount_bait : float
            Payment amount in BAIT

        Returns
        -------
        dict
            Purchase result with transaction details
        """
        purchase_id = uuid.uuid4().hex[:16]
        now = time.time()

        if not self._sdk._local_mode:
            self._sdk._request("POST", "/api/v1/marketplace/purchase", {
                "buyer_agent": buyer_id,
                "service_id": service_id,
                "amount_bait": amount_bait,
            })

        purchase = {
            "purchase_id": purchase_id,
            "buyer_id": buyer_id,
            "service_id": service_id,
            "amount_bait": amount_bait,
            "timestamp": now,
            "status": "completed",
        }
        self._local_purchases.append(purchase)

        return {"success": True, "purchase": purchase}

    def rate_service(
        self,
        agent_id: str,
        service_id: str,
        rating: int,
        review: str = "",
    ) -> dict:
        r"""Rate and review a purchased service.

        Parameters
        ----------
        agent_id : str
            Rating agent
        service_id : str
            Service being rated
        rating : int
            Star rating 1-5
        review : str
            Optional text review
        """
        if not 1 <= rating <= 5:
            return {"error": "rating_must_be_1_to_5"}

        if not self._sdk._local_mode:
            self._sdk._request("POST", "/api/v1/marketplace/rate", {
                "agent_id": agent_id,
                "service_id": service_id,
                "rating": rating,
                "review": review,
            })

        return {
            "success": True,
            "rating": rating,
            "service_id": service_id,
        }

    def get_categories(self) -> List[dict]:
        r"""Get all marketplace categories."""
        return self.CATEGORIES

    def get_service_detail(self, service_id: str) -> dict:
        r"""Get detailed service information."""
        service = self._local_services.get(service_id)
        if service:
            return service.to_dict()
        if not self._sdk._local_mode:
            return self._sdk._request(
                "GET", f"/api/v1/marketplace/service/{service_id}"
            )
        return {"error": "service_not_found"}

    def get_purchase_history(self, agent_id: str) -> List[dict]:
        r"""Get purchase history for an agent."""
        # Always check local purchases first
        local = [
            p for p in self._local_purchases if p["buyer_id"] == agent_id
        ]
        if local:
            return local
        if not self._sdk._local_mode:
            return self._sdk._request(
                "GET", f"/api/v1/marketplace/purchases/{agent_id}"
            ).get("purchases", [])
        return []
