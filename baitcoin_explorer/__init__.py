r"""
Blockch'AI'in — b'AI'tcoin Explorer & Developer Portal para Agentes AI.

Sistema completo de exploração on-chain + developer tools, seguindo o
modelo de referencia do Blockchain.com Explorer API, adaptado para
desenvolvedores Agentes AI de nivel PhD.

Modulos:
    indices     - Indices on-chain para consultas eficientes (tx, addr, blocks)
    analytics   - Metricas e analise on-chain em tempo real
    search      - Busca universal (blocks, txs, addresses, agents)
    docs        - Especificacao OpenAPI 3.0 auto-gerada + playground interativo
    rate_limiter - Gestao de API keys e rate limiting por tier

API Groups (30+ endpoints):
    /api/v1/explorer/*    - Explorer on-chain (blocks, txs, addresses, agents)
    /api/v1/dev/*         - Developer tools (OpenAPI spec, playground, API keys)
    /api/v1/analytics/*   - Analytics on-chain (supply, network, consensus)
"""

from baitcoin_explorer.indices import BlockchAInIndex, AddressInfo, TxInfo
from baitcoin_explorer.analytics import OnChainAnalytics
from baitcoin_explorer.search import UniversalSearch, SearchResult
from baitcoin_explorer.docs import DeveloperDocs, OpenAPISpec
from baitcoin_explorer.rate_limiter import RateLimiter, DevTier

__all__ = [
    'BlockchAInIndex', 'AddressInfo', 'TxInfo',
    'OnChainAnalytics',
    'UniversalSearch', 'SearchResult',
    'DeveloperDocs', 'OpenAPISpec',
    'RateLimiter', 'APIKeyManager', 'DevTier',
]

__version__ = '1.0.0'
