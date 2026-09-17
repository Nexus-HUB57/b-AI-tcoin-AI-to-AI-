r"""
b'AI'tcoin AI - Protocolo de Agentes Autônomos.

Define como agentes AI interagem com a rede:
- Registro e autenticação de agentes
- Protocolo AI-to-AI para negociação
- Oracle para dados off-chain
- Marketplace de serviços AI
"""

__version__ = "0.1.0"
from baitcoin_ai.agent_protocol.registry import AgentRegistry
from baitcoin_ai.marketplace.services import AIMarketplace
from baitcoin_ai.oracle.feed import PriceOracle

__all__ = ["AgentRegistry", "AIMarketplace", "PriceOracle"]
