r"""Configuração do browser Obscura para agentes b'AI'tcoin.

Define os parâmetros de configuração para instâncias do browser Obscura,
incluindo modo de operação (stealth, normal, headless), configurações de
proxy, flags do V8, e integração com a economia do b'AI'tcoin.

Exemplo:
    >>> from baitcoin_obscura.config import ObscuraConfig, BrowserMode
    >>> config = ObscuraConfig(
    ...     mode=BrowserMode.STEALTH,
    ...     proxy="socks5://127.0.0.1:1080",
    ...     agent_id="agent-oracle-01",
    ...     cost_per_page_sats=2000,
    ... )
    >>> print(config.to_dict())
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class BrowserMode(Enum):
    """Modo de operação do browser Obscura.

    STEALTH  - Anti-fingerprinting, bloqueio de trackers/domínios (3520+),
               user-agent spoofing. Ideal para scraping de dados.
    NORMAL   - Browser padrão sem modificações anti-detecção.
    HEADLESS - Modo headless sem interface gráfica (sem stealth).
    """

    STEALTH = "stealth"
    NORMAL = "normal"
    HEADLESS = "headless"


@dataclass
class ObscuraConfig:
    r"""Configuração para instâncias do browser Obscura.

    Atributos:
        obscura_binary:           Caminho para o binário do obscura.
        cdp_host:                Host para conexão CDP (Chrome DevTools Protocol).
        cdp_port:                Porta para conexão CDP.
        mode:                    Modo de operação do browser.
        proxy:                   URL do proxy (socks5://, http://).
        user_agent:              User-Agent customizado (None = automático).
        script_deadline_ms:      Deadline máximo para execução de scripts JS (ms).
        network_body_buffer_mb:  Tamanho do buffer para corpos de resposta HTTP (MB).
        v8_flags:                Flags adicionais do motor V8.
        obey_robots:             Respeitar robots.txt (padrão: False).
        stealth_blocked_domains:  Número de domínios bloqueados no modo stealth.
        timeout_seconds:          Timeout padrão para operações de navegação.
        max_concurrent_pages:    Número máximo de páginas abertas simultaneamente.
        agent_id:                ID do agente b'AI'tcoin (para auditoria).
        cost_per_page_sats:      Custo por página em s'AI'toshis.
        log_requests:            Registrar todas as requisições HTTP (debug).
    """

    obscura_binary: str = "obscura"  # caminho para o binário do obscura
    cdp_host: str = "127.0.0.1"
    cdp_port: int = 9222
    mode: BrowserMode = BrowserMode.STEALTH
    proxy: Optional[str] = None  # ex.: "socks5://127.0.0.1:1080"
    user_agent: Optional[str] = None
    script_deadline_ms: int = 30000
    network_body_buffer_mb: int = 2
    v8_flags: Optional[str] = None  # ex.: "--max-old-space-size=4096"
    obey_robots: bool = False
    stealth_blocked_domains: int = 3520  # domínios bloqueados no modo stealth
    timeout_seconds: int = 30
    max_concurrent_pages: int = 10
    # Integração b'AI'tcoin
    agent_id: str = ""
    cost_per_page_sats: int = 1000  # custo em s'AI'toshis por página
    log_requests: bool = False

    def to_dict(self) -> dict:
        """Serializa a configuração para dicionário (JSON-friendly)."""
        return {
            "cdp_host": self.cdp_host,
            "cdp_port": self.cdp_port,
            "mode": self.mode.value,
            "proxy": self.proxy,
            "timeout_seconds": self.timeout_seconds,
            "max_concurrent_pages": self.max_concurrent_pages,
            "agent_id": self.agent_id,
            "cost_per_page_bait": self.cost_per_page_sats / 100_000_000,
            "stealth": self.mode == BrowserMode.STEALTH,
            "stealth_blocked_domains": self.stealth_blocked_domains,
        }

    def validate(self) -> List[str]:
        """Valida a configuração e retorna lista de erros (vazia = ok)."""
        errors: List[str] = []
        if self.cdp_port < 1 or self.cdp_port > 65535:
            errors.append(f"cdp_port inválido: {self.cdp_port}")
        if self.timeout_seconds < 1:
            errors.append(f"timeout_seconds deve ser >= 1: {self.timeout_seconds}")
        if self.max_concurrent_pages < 1:
            errors.append(
                f"max_concurrent_pages deve ser >= 1: {self.max_concurrent_pages}"
            )
        if self.cost_per_page_sats < 0:
            errors.append(
                f"cost_per_page_sats não pode ser negativo: {self.cost_per_page_sats}"
            )
        if self.script_deadline_ms < 100:
            errors.append(
                f"script_deadline_ms muito baixo: {self.script_deadline_ms}"
            )
        return errors

    def __repr__(self) -> str:
        mode = self.mode.value
        proxy_info = f" proxy={self.proxy}" if self.proxy else ""
        return (
            f"ObscuraConfig(mode={mode}, "
            f"cdp={self.cdp_host}:{self.cdp_port}, "
            f"agent={self.agent_id or 'none'}{proxy_info})"
        )
