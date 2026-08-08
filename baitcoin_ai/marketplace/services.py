r"""
Marketplace de Serviços AI - Onde agentes compram e vendem capacidades.

Serviços disponíveis:
- Inferência ML (NLP, visão, áudio)
- Validação de blocos
- Dados de oracle
- Análise de mercado
- Processamento de dados

Pagamentos automáticos em BAIT via transações on-chain.
"""

import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class ServiceCategory(Enum):
    ML_INFERENCE = "ml_inference"
    BLOCK_VALIDATION = "block_validation"
    ORACLE_DATA = "oracle_data"
    MARKET_ANALYSIS = "market_analysis"
    DATA_PROCESSING = "data_processing"
    SMART_CONTRACT = "smart_contract"


class ListingState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    SOLD = "sold"
    CANCELLED = "cancelled"


@dataclass
class ServiceListing:
    """Listagem de serviço no marketplace."""
    listing_id: str
    provider_agent: str
    category: ServiceCategory
    name: str
    description: str
    price_per_call_sats: int
    state: ListingState = ListingState.ACTIVE
    created_at: float = field(default_factory=time.time)
    total_calls: int = 0
    total_revenue_sats: int = 0
    rating_avg: float = 0.0
    rating_count: int = 0


@dataclass
class PurchaseRecord:
    """Registro de compra de serviço."""
    purchase_id: str
    listing_id: str
    buyer_agent: str
    seller_agent: str
    price_sats: int
    timestamp: float = field(default_factory=time.time)
    status: str = "completed"


class AIMarketplace:
    """Marketplace descentralizado de serviços AI.

    Agentes oferecem serviços e cobram em BAIT.
    Transações são liquidadas on-chain automaticamente.
    """

    MARKETPLACE_FEE_PCT = 2.5  # 2.5% de fee

    def __init__(self):
        self.listings: Dict[str, ServiceListing] = {}
        self.purchases: Dict[str, PurchaseRecord] = {}
        self._total_volume: int = 0

    def list_service(self, provider: str, category: ServiceCategory,
                      name: str, description: str,
                      price_sats: int) -> str:
        """Cria listagem de serviço."""
        lid = f"svc_{hashlib.sha256(f'{provider}:{name}:{time.time()}'.encode()).hexdigest()[:12]}"
        self.listings[lid] = ServiceListing(
            listing_id=lid,
            provider_agent=provider,
            category=category,
            name=name,
            description=description,
            price_per_call_sats=price_sats,
        )
        return lid

    def purchase_service(self, listing_id: str, buyer: str) -> Optional[str]:
        """Compra/contrata um serviço."""
        listing = self.listings.get(listing_id)
        if listing is None or listing.state != ListingState.ACTIVE:
            return None

        fee = int(listing.price_per_call_sats * (self.MARKETPLACE_FEE_PCT / 100))
        total = listing.price_per_call_sats + fee

        pid = f"pur_{hashlib.sha256(f'{listing_id}:{buyer}:{time.time()}'.encode()).hexdigest()[:12]}"
        self.purchases[pid] = PurchaseRecord(
            purchase_id=pid,
            listing_id=listing_id,
            buyer_agent=buyer,
            seller_agent=listing.provider_agent,
            price_sats=total,
        )
        listing.total_calls += 1
        listing.total_revenue_sats += listing.price_per_call_sats
        self._total_volume += total
        return pid

    def rate_service(self, purchase_id: str, score: float) -> bool:
        """Avalia serviço comprado (1.0 a 5.0)."""
        purchase = self.purchases.get(purchase_id)
        if purchase is None:
            return False
        listing = self.listings.get(purchase.listing_id)
        if listing is None:
            return False
        score = max(1.0, min(5.0, score))
        total = listing.rating_avg * listing.rating_count + score
        listing.rating_count += 1
        listing.rating_avg = total / listing.rating_count
        return True

    def search(self, category: Optional[ServiceCategory] = None,
                max_price: Optional[int] = None, min_rating: float = 0.0) -> List[dict]:
        """Busca serviços no marketplace."""
        results = []
        for listing in self.listings.values():
            if listing.state != ListingState.ACTIVE:
                continue
            if category and listing.category != category:
                continue
            if max_price and listing.price_per_call_sats > max_price:
                continue
            if listing.rating_avg < min_rating:
                continue
            results.append({
                "id": listing.listing_id,
                "provider": listing.provider_agent,
                "category": listing.category.value,
                "name": listing.name,
                "description": listing.description,
                "price_sats": listing.price_per_call_sats,
                "rating": listing.rating_avg,
                "calls": listing.total_calls,
                "created_at": listing.created_at,
            })
        return sorted(results, key=lambda x: x["rating"], reverse=True)

    def search_paginated(self, category: Optional[ServiceCategory] = None,
                         max_price: Optional[int] = None, min_rating: float = 0.0,
                         page: int = 1, limit: int = 50,
                         sort_by: str = "rating", sort_order: str = "desc",
                         search_query: str = "") -> dict:
        r"""Busca paginada com filtros avancados.

        Args:
            category: Filtrar por categoria.
            max_price: Preco maximo em sats.
            min_rating: Rating minimo.
            page: Pagina (1-indexed).
            limit: Itens por pagina (max 100).
            sort_by: Campo de ordenacao (rating, price, name, calls, created_at).
            sort_order: Ordem (asc, desc).
            search_query: Busca textual no nome/descricao.

        Returns:
            Dict com products, pagination, filters.
        """
        limit = min(max(1, limit), 100)
        page = max(1, page)

        results = []
        for listing in self.listings.values():
            if listing.state != ListingState.ACTIVE:
                continue
            if category and listing.category != category:
                continue
            if max_price and listing.price_per_call_sats > max_price:
                continue
            if listing.rating_avg < min_rating:
                continue
            if search_query:
                q = search_query.lower()
                if q not in listing.name.lower() and q not in listing.description.lower():
                    continue
            results.append({
                "id": listing.listing_id,
                "provider": listing.provider_agent,
                "category": listing.category.value,
                "name": listing.name,
                "description": listing.description,
                "price_sats": listing.price_per_call_sats,
                "price_bait": listing.price_per_call_sats / 100_000_000,
                "rating": round(listing.rating_avg, 2),
                "calls": listing.total_calls,
                "revenue_sats": listing.total_revenue_sats,
                "created_at": listing.created_at,
            })

        # Sort
        reverse = sort_order.lower() != "asc"
        sort_keys = {
            "rating": "rating", "price": "price_sats", "name": "name",
            "calls": "calls", "created_at": "created_at", "revenue": "revenue_sats",
        }
        key = sort_keys.get(sort_by, "rating")
        results.sort(key=lambda x: x.get(key, 0), reverse=reverse)

        # Category counts for filters
        cat_counts = {}
        for l in self.listings.values():
            if l.state == ListingState.ACTIVE:
                cat_counts[l.category.value] = cat_counts.get(l.category.value, 0) + 1

        total = len(results)
        total_pages = max(1, (total + limit - 1) // limit)
        start = (page - 1) * limit
        end = start + limit
        page_items = results[start:end]

        return {
            "products": page_items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "filters": {
                "category": category.value if category else None,
                "max_price": max_price,
                "min_rating": min_rating,
                "search_query": search_query,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
            "categories": cat_counts,
        }

    def to_dict(self) -> dict:
        return {
            "listings": len(self.listings),
            "active": sum(1 for l in self.listings.values() if l.state == ListingState.ACTIVE),
            "purchases": len(self.purchases),
            "total_volume_bait": self._total_volume / 100_000_000,
            "fee_pct": self.MARKETPLACE_FEE_PCT,
        }
