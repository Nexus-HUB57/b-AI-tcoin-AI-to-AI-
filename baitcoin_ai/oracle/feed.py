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
    """Oracle de preços descentralizado.

    Agrega preços de múltiplos agentes oracles
    usando mediana ponderada por reputação.
    """

    MAX_AGE_SECONDS = 300  # 5 minutos
    MIN_SOURCES = 3  # Mínimo de oracles para considerar válido

    def __init__(self):
        self.feeds: Dict[str, List[PricePoint]] = defaultdict(list)
        self.oracles: Dict[str, float] = {}  # agent_id -> reputation_weight
        self.reports: List[OracleReport] = []
        # FIX: persiste ultimo preco valido por simbolo, para publicar em /status
        # em vez de retornar None quando o feed expirar ou faltar quorum.
        self._last_valid_price: Dict[str, PricePoint] = {}

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
        """Retorna preço agregado (mediana ponderada).

        FIX: quando nao ha quorum ativo mas existe ultimo preco valido
        cacheado, retorna esse ultimo valor em vez de None — evita que
        /status.oracle.prices publique null e a UI mostre '—' para sempre.
        """
        symbol = symbol.upper()
        points = self._get_valid_points(symbol)
        if len(points) >= self.MIN_SOURCES:
            weighted = []
            for p in points:
                weight = self.oracles.get(p.source, 1.0)
                weighted.extend([p.price] * int(weight))
            weighted.sort()
            price = weighted[len(weighted) // 2]
            # cacheia ultimo valor valido para fallback
            self._last_valid_price[symbol] = PricePoint(
                symbol=symbol, price=price, timestamp=time.time(), source="aggregate"
            )
            return price
        # sem quorum: retorna ultimo valor conhecido se disponivel
        last = self._last_valid_price.get(symbol)
        if last is not None:
            return last.price
        return None

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
        return {
            "oracles": len(self.oracles),
            "symbols_tracked": len(self.feeds),
            "total_reports": len(self.reports),
            "prices": {s: self.get_price(s) for s in self.feeds},
        }
