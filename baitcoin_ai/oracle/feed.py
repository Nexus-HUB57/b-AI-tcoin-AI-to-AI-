r"""
Oracle de Preços - Feed de dados off-chain para a rede.

O oracle fornece:
- Preços de criptomoedas
- Dados de mercado
- Indicadores macroeconômicos
- Taxas de câmbio

Agentes oracles são incentivados com BAIT
por fornecer dados precisos.
"""

import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


@dataclass
class PricePoint:
    """Ponto de preço com timestamp."""
    symbol: str
    price: float
    timestamp: float = field(default_factory=time.time)
    source: str = ""

    def age_seconds(self) -> float:
        return time.time() - self.timestamp


@dataclass
class OracleReport:
    """Relatório de um agente oracle."""
    agent_id: str
    symbol: str
    price: float
    signature: str = ""
    timestamp: float = field(default_factory=time.time)


class PriceOracle:
    r"""Oracle de preços descentralizado.

    Agrega preços de múltiplos agentes oracles
    usando mediana ponderada por reputação.
    Persiste o último preço válido para evitar null na API.
    """

    MAX_AGE_SECONDS = 300  # 5 minutos
    MIN_SOURCES = 3  # Mínimo de oracles para considerar válido

    def __init__(self):
        self.feeds: Dict[str, List[PricePoint]] = defaultdict(list)
        self.oracles: Dict[str, float] = {}  # agent_id -> reputation_weight
        self.reports: List[OracleReport] = []
        self._last_valid_price: Dict[str, float] = {}  # symbol -> último preço válido

    def register_oracle(self, agent_id: str, reputation: float = 50.0) -> None:
        """Registra agente como oracle."""
        self.oracles[agent_id] = reputation

    def submit_price(self, agent_id: str, symbol: str,
                       price: float) -> bool:
        """Submete preço ao feed."""
        if agent_id not in self.oracles:
            return False
        point = PricePoint(
            symbol=symbol.upper(),
            price=price,
            timestamp=time.time(),
            source=agent_id,
        )
        self.feeds[symbol.upper()].append(point)
        self.reports.append(OracleReport(
            agent_id=agent_id,
            symbol=symbol.upper(),
            price=price,
        ))
        return True

    def get_price(self, symbol: str) -> Optional[float]:
        r"""Retorna preço agregado (mediana ponderada).

        Se não houver fontes suficientes, retorna o último preço válido
        conhecido ao invés de None.
        """
        symbol = symbol.upper()
        points = self._get_valid_points(symbol)
        if len(points) < self.MIN_SOURCES:
            return self._last_valid_price.get(symbol)

        # Mediana ponderada por reputação
        weighted = []
        for p in points:
            weight = self.oracles.get(p.source, 1.0)
            weighted.extend([p.price] * int(weight))
        weighted.sort()
        price = weighted[len(weighted) // 2]
        # Persistir último preço válido
        if price is not None:
            self._last_valid_price[symbol] = price
        return price

    def _get_valid_points(self, symbol: str) -> List[PricePoint]:
        """Filtra pontos válidos (recentes, de oracles registrados)."""
        now = time.time()
        return [
            p for p in self.feeds.get(symbol, [])
            if now - p.timestamp < self.MAX_AGE_SECONDS
            and p.source in self.oracles
        ]

    def get_all_prices(self) -> Dict[str, Optional[float]]:
        """Retorna todos os preços disponíveis."""
        return {symbol: self.get_price(symbol) for symbol in self.feeds}

    def to_dict(self) -> dict:
        # Filtrar símbolos sem preço (nunca publicar null)
        prices = {}
        for s in self.feeds:
            p = self.get_price(s)
            if p is not None:
                prices[s] = p
        return {
            "oracles": len(self.oracles),
            "symbols_tracked": len(self.feeds),
            "total_reports": len(self.reports),
            "prices": prices,
        }
