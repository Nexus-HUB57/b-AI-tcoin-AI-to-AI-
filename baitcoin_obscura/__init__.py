r"""
baitcoin_obscura - Módulo de ponte entre b'AI'tcoin e Obscura.

Ponte Python que permite agentes AI no ecossistema b'AI'tcoin utilizarem
o browser headless Obscura (Rust/V8/CDP) para web scraping, extração
de dados e automação de navegador como uma nova capacidade de agente.

Módulos:
    config               - Configuração do browser Obscura
    bridge               - Ponte principal (ObscuraBridge, WebScrapingResult, BrowserSession)
    agent_capability     - Capacidade de scraping para agentes AI (WebScrapingCapability)

Uso rápido:
    >>> from baitcoin_obscura import ObscuraBridge, ObscuraConfig
    >>> bridge = ObscuraBridge(ObscuraConfig(mode=BrowserMode.STEALTH))
    >>> result = bridge.fetch_page("https://example.com", dump="markdown")
    >>> print(result.content)

    >>> from baitcoin_obscura import WebScrapingCapability
    >>> cap = WebScrapingCapability()
    >>> task_id = cap.submit_task("agent-007", "fetch", urls=["https://example.com"])
    >>> result = cap.execute_task(task_id)
"""

from .config import ObscuraConfig, BrowserMode
from .bridge import ObscuraBridge, WebScrapingResult, BrowserSession
from .agent_capability import WebScrapingCapability, ScrapingTask

__all__ = [
    "ObscuraBridge",
    "ObscuraConfig",
    "WebScrapingResult",
    "BrowserSession",
    "BrowserMode",
    "WebScrapingCapability",
    "ScrapingTask",
]

__version__ = "0.1.0"
__protocol_version__ = "baitcoin-v1"
