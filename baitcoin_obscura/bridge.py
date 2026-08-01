r"""
Ponte Obscura - Python bridge para o browser headless Obscura (agentes b'AI'tcoin).

Fornece aos agentes AI capacidades de web scraping, extração de dados e
automação de navegador através do motor Obscura baseado em Rust.

Dois modos de operação:
1. Modo CLI:    Invoca o CLI do obscura para operações pontuais (fetch/scrape).
2. Modo Server: Inicia o obscura serve (CDP) para sessões persistentes.

Exemplo:
    >>> from baitcoin_obscura.bridge import ObscuraBridge, WebScrapingResult
    >>> bridge = ObscuraBridge()
    >>> result = bridge.fetch_page("https://example.com", dump="markdown")
    >>> print(f"Título: {result.title}")
    >>> print(f"Custo: {result.cost_sats} sats")
"""
import asyncio
import json
import logging
import os
import re
import subprocess
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import ObscuraConfig, BrowserMode

logger = logging.getLogger("baitcoin_obscura.bridge")


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------

@dataclass
class WebScrapingResult:
    r"""Resultado de uma operação web via Obscura.

    Atributos:
        operation:    Tipo da operação (fetch, scrape, snapshot, click, fill, evaluate).
        url:          URL alvo da operação.
        status:       Estado final (success, error, timeout).
        content:      Conteúdo extraído (HTML, texto, markdown, links, resultado JS).
        title:        Título da página (quando disponível).
        links:        Lista de links extraídos da página.
        assets:       Lista de assets (imagens, scripts, estilos) da página.
        cost_sats:    Custo da operação em s'AI'toshis.
        duration_ms:  Duração da operação em milissegundos.
        error:        Mensagem de erro (vazia se sucesso).
        metadata:     Metadados adicionais da operação.
        agent_id:     ID do agente que solicitou a operação.
        timestamp:    Timestamp Unix da conclusão.
    """

    operation: str
    url: str = ""
    status: str = "success"
    content: str = ""
    title: str = ""
    links: List[str] = None
    assets: List[str] = None
    cost_sats: int = 0
    duration_ms: float = 0
    error: str = ""
    metadata: dict = None
    agent_id: str = ""
    timestamp: float = None

    def __post_init__(self):
        if self.links is None:
            self.links = []
        if self.assets is None:
            self.assets = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        """Serializa para dicionário (JSON-friendly)."""
        return {
            "operation": self.operation,
            "url": self.url,
            "status": self.status,
            "content_length": len(self.content),
            "title": self.title,
            "links_count": len(self.links),
            "assets_count": len(self.assets),
            "cost_bait": self.cost_sats / 100_000_000,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        status = self.status
        length = len(self.content)
        return (
            f"WebScrapingResult(op={self.operation}, status={status}, "
            f"content_len={length}, cost={self.cost_sats}sats)"
        )


# ---------------------------------------------------------------------------
# Sessão de browser persistente
# ---------------------------------------------------------------------------

@dataclass
class BrowserSession:
    r"""Sessão persistente de browser via CDP.

    Atributos:
        session_id:    Identificador único da sessão.
        cdp_url:       URL WebSocket do CDP para conexão.
        created_at:    Timestamp de criação.
        page_count:    Número de páginas navegadas nesta sessão.
        total_cost_sats: Custo total acumulado em s'AI'toshis.
        is_active:     Se a sessão ainda está ativa.
    """

    session_id: str
    cdp_url: str
    created_at: float = None
    page_count: int = 0
    total_cost_sats: int = 0
    is_active: bool = True

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        """Serializa para dicionário."""
        return {
            "session_id": self.session_id,
            "cdp_url": self.cdp_url,
            "page_count": self.page_count,
            "total_cost_bait": self.total_cost_sats / 100_000_000,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return (
            f"BrowserSession(id={self.session_id[:8]}..., "
            f"pages={self.page_count}, active={self.is_active})"
        )


# ---------------------------------------------------------------------------
# Ponte principal
# ---------------------------------------------------------------------------

class ObscuraBridge:
    r"""Ponte entre agentes b'AI'tcoin e o browser headless Obscura.

    Gerencia o ciclo de vida do processo Obscura e fornece:
    - Fetch/scrape pontuais via CLI
    - Sessões CDP persistentes para automação complexa
    - Rastreamento de custos em s'AI'toshis
    - Sessões escopadas por agente com trilha de auditoria

    Fluxo típico:
        >>> bridge = ObscuraBridge(ObscuraConfig(mode=BrowserMode.STEALTH))
        >>> result = bridge.fetch_page("https://news.ycombinator.com", dump="text")
        >>> print(result.content[:200])
        >>> bridge.close()
    """

    # Constantes
    _STARTUP_WAIT_SECONDS = 1.5
    _MAX_ERROR_LENGTH = 500

    def __init__(self, config: Optional[ObscuraConfig] = None):
        self.config = config or ObscuraConfig()
        self._process: Optional[subprocess.Popen] = None
        self._sessions: Dict[str, BrowserSession] = {}
        self._total_ops: int = 0
        self._total_cost_sats: int = 0
        logger.debug(
            "ObscuraBridge inicializado: mode=%s, cdp=%s:%d",
            self.config.mode.value, self.config.cdp_host, self.config.cdp_port,
        )

    # ------------------------------------------------------------------
    # Propriedades
    # ------------------------------------------------------------------

    @property
    def is_server_running(self) -> bool:
        """Verifica se o processo do servidor Obscura está ativo."""
        return self._process is not None and self._process.poll() is None

    @property
    def active_session_count(self) -> int:
        """Número de sessões CDP ativas."""
        return sum(1 for s in self._sessions.values() if s.is_active)

    # ------------------------------------------------------------------
    # Ciclo de vida do servidor
    # ------------------------------------------------------------------

    def start_server(self) -> bool:
        r"""Inicia o obscura serve como servidor CDP persistente.

        Retorna True se o servidor iniciou com sucesso, False caso contrário.
        """
        if self.is_server_running:
            logger.debug("Servidor Obscura já está rodando (PID %d).", self._process.pid)
            return True

        cmd = [
            self.config.obscura_binary, "serve",
            "--port", str(self.config.cdp_port),
        ]
        if self.config.mode == BrowserMode.STEALTH:
            cmd.append("--stealth")
        if self.config.proxy:
            cmd.extend(["--proxy", self.config.proxy])
        if self.config.obey_robots:
            cmd.append("--obey-robots")
        if self.config.user_agent:
            cmd.extend(["--user-agent", self.config.user_agent])

        logger.info("Iniciando servidor Obscura: %s", " ".join(cmd))
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(self._STARTUP_WAIT_SECONDS)
            running = self.is_server_running
            if running:
                logger.info(
                    "Servidor Obscura iniciado (PID %d) na porta %d.",
                    self._process.pid, self.config.cdp_port,
                )
            else:
                logger.error("Servidor Obscura falhou ao iniciar.")
            return running
        except (FileNotFoundError, OSError) as exc:
            logger.error(
                "Não foi possível iniciar Obscura: %s. "
                "Instale em: https://github.com/h4ckf0r0day/obscura",
                exc,
            )
            return False

    def stop_server(self) -> None:
        r"""Para o processo do servidor Obscura e limpa sessões."""
        if self._process is not None:
            logger.info("Parando servidor Obscura (PID %d)...", self._process.pid)
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Servidor não respondeu ao terminate, enviando kill.")
                self._process.kill()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
            self._process = None
        # Encerra todas as sessões ativas
        for session in self._sessions.values():
            if session.is_active:
                session.is_active = False
        self._sessions.clear()
        logger.debug("Servidor Obscura parado e sessões limpas.")

    def restart_server(self) -> bool:
        r"""Reinicia o servidor Obscura (stop + start)."""
        self.stop_server()
        time.sleep(0.5)
        return self.start_server()

    # ------------------------------------------------------------------
    # Helpers para CLI
    # ------------------------------------------------------------------

    def _build_cli_cmd(self, *args: str) -> List[str]:
        """Constrói comando CLI com flags globais de configuração."""
        cmd = [self.config.obscura_binary]
        if self.config.mode == BrowserMode.STEALTH:
            cmd.append("--stealth")
        if self.config.proxy:
            cmd.extend(["--proxy", self.config.proxy])
        if self.config.v8_flags:
            cmd.extend(["--v8-flags", self.config.v8_flags])
        if self.config.user_agent:
            cmd.extend(["--user-agent", self.config.user_agent])
        cmd.extend(args)
        return cmd

    def _resolve_agent_id(self, agent_id: str) -> str:
        """Retorna o agent_id fornecido ou o padrão da config."""
        return agent_id or self.config.agent_id

    def _truncate_error(self, error: str) -> str:
        """Trunca mensagem de erro para tamanho máximo."""
        return error[: self._MAX_ERROR_LENGTH]

    # ------------------------------------------------------------------
    # Operações de fetch/scrape (modo CLI)
    # ------------------------------------------------------------------

    def fetch_page(
        self,
        url: str,
        dump: str = "html",
        eval_js: str = "",
        wait_until: str = "load",
        timeout: int = 0,
        output_file: str = "",
        selector: str = "",
        agent_id: str = "",
    ) -> WebScrapingResult:
        r"""Busca uma única página usando o CLI do obscura.

        Args:
            url:         URL para buscar.
            dump:        Tipo de saída - html, text, links, markdown, assets, original.
            eval_js:     Expressão JavaScript para avaliar no contexto da página.
            wait_until:  Evento de navegação - load, domcontentloaded, networkidle0.
            timeout:     Tempo máximo de navegação (0 = usar padrão da config).
            output_file: Gravar saída em arquivo.
            selector:    Aguardar seletor CSS aparecer na página.
            agent_id:    ID do agente solicitante.

        Returns:
            WebScrapingResult com o conteúdo e metadados da operação.
        """
        start = time.time()
        effective_timeout = timeout or self.config.timeout_seconds
        agent = self._resolve_agent_id(agent_id)

        cmd = self._build_cli_cmd(
            "fetch", url,
            "--dump", dump,
            "--timeout", str(effective_timeout),
            "--wait-until", wait_until,
        )
        if eval_js:
            cmd.extend(["--eval", eval_js])
        if output_file:
            cmd.extend(["--output", output_file])
        if selector:
            cmd.extend(["--selector", selector])

        if self.config.log_requests:
            logger.debug("Executando: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout + 10,
            )
            content = result.stdout.strip()

            if result.returncode == 0:
                self._total_ops += 1
                cost = self.config.cost_per_page_sats
                self._total_cost_sats += cost

                # Extrai título do HTML quando disponível
                title = ""
                if dump == "html" and "<title>" in content:
                    match = re.search(
                        r"<title[^>]*>(.*?)</title>",
                        content,
                        re.IGNORECASE | re.DOTALL,
                    )
                    if match:
                        title = match.group(1).strip()

                # Extrai links quando dump=links
                links = []
                if dump == "links":
                    links = [l.strip() for l in content.splitlines() if l.strip()]

                duration = (time.time() - start) * 1000
                return WebScrapingResult(
                    operation="fetch",
                    url=url,
                    status="success",
                    content=content,
                    title=title,
                    links=links,
                    cost_sats=cost,
                    duration_ms=duration,
                    metadata={"dump": dump, "wait_until": wait_until},
                    agent_id=agent,
                )
            else:
                duration = (time.time() - start) * 1000
                return WebScrapingResult(
                    operation="fetch",
                    url=url,
                    status="error",
                    error=self._truncate_error(result.stderr.strip()),
                    duration_ms=duration,
                    agent_id=agent,
                )

        except subprocess.TimeoutExpired:
            duration = (time.time() - start) * 1000
            return WebScrapingResult(
                operation="fetch",
                url=url,
                status="timeout",
                error=f"Timeout após {effective_timeout}s",
                duration_ms=duration,
                agent_id=agent,
            )
        except FileNotFoundError:
            duration = (time.time() - start) * 1000
            return WebScrapingResult(
                operation="fetch",
                url=url,
                status="error",
                error=(
                    "Binário do Obscura não encontrado. "
                    "Instale: https://github.com/h4ckf0r0day/obscura"
                ),
                duration_ms=duration,
                agent_id=agent,
            )

    def scrape_pages(
        self,
        urls: List[str],
        concurrency: int = 0,
        eval_js: str = "",
        format: str = "json",
        agent_id: str = "",
    ) -> List[WebScrapingResult]:
        r"""Faz scraping de múltiplas páginas em paralelo.

        Args:
            urls:        Lista de URLs para scraping.
            concurrency: Número de páginas simultâneas (0 = usar config default).
            eval_js:     Expressão JS para avaliar em cada página.
            format:      Formato de saída - json, text.
            agent_id:    ID do agente solicitante.

        Returns:
            Lista de WebScrapingResult, uma por URL processada.
        """
        start = time.time()
        effective_concurrency = concurrency or self.config.max_concurrent_pages
        agent = self._resolve_agent_id(agent_id)

        cmd = self._build_cli_cmd(
            "scrape", *urls,
            "--concurrency", str(effective_concurrency),
            "--format", format,
            "--quiet",
        )
        if eval_js:
            cmd.extend(["--eval", eval_js])

        if self.config.log_requests:
            logger.debug("Executando: %s", " ".join(cmd))

        results: List[WebScrapingResult] = []

        try:
            max_timeout = self.config.timeout_seconds * max(len(urls), 1) + 30
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max_timeout,
            )

            if proc.returncode == 0:
                if format == "json":
                    try:
                        data = json.loads(proc.stdout)
                        if isinstance(data, list):
                            per_url_ms = (time.time() - start) * 1000 / max(len(urls), 1)
                            for item in data:
                                url = item.get("url", "")
                                result_content = item.get("result", "")
                                if not isinstance(result_content, str):
                                    result_content = json.dumps(result_content)
                                results.append(
                                    WebScrapingResult(
                                        operation="scrape",
                                        url=url,
                                        status="success",
                                        content=result_content,
                                        cost_sats=self.config.cost_per_page_sats,
                                        duration_ms=per_url_ms,
                                        agent_id=agent,
                                    )
                                )
                        else:
                            # Resposta JSON, mas não é lista
                            results.append(
                                WebScrapingResult(
                                    operation="scrape",
                                    status="success",
                                    content=proc.stdout,
                                    cost_sats=self.config.cost_per_page_sats
                                    * len(urls),
                                    duration_ms=(time.time() - start) * 1000,
                                    agent_id=agent,
                                )
                            )
                    except json.JSONDecodeError:
                        # JSON inválido, retorna texto cru
                        results.append(
                            WebScrapingResult(
                                operation="scrape",
                                status="success",
                                content=proc.stdout,
                                cost_sats=self.config.cost_per_page_sats * len(urls),
                                duration_ms=(time.time() - start) * 1000,
                                agent_id=agent,
                            )
                        )
                else:
                    # Formato não-JSON (text, markdown, etc.)
                    results.append(
                        WebScrapingResult(
                            operation="scrape",
                            status="success",
                            content=proc.stdout,
                            cost_sats=self.config.cost_per_page_sats * len(urls),
                            duration_ms=(time.time() - start) * 1000,
                            agent_id=agent,
                        )
                    )
                # Atualiza contadores
                self._total_ops += len(urls)
                self._total_cost_sats += self.config.cost_per_page_sats * len(urls)
            else:
                results.append(
                    WebScrapingResult(
                        operation="scrape",
                        status="error",
                        error=self._truncate_error(proc.stderr.strip()),
                        duration_ms=(time.time() - start) * 1000,
                        agent_id=agent,
                    )
                )

        except subprocess.TimeoutExpired:
            results.append(
                WebScrapingResult(
                    operation="scrape",
                    status="timeout",
                    error=f"Timeout no scraping de {len(urls)} URLs",
                    duration_ms=(time.time() - start) * 1000,
                    agent_id=agent,
                )
            )
        except FileNotFoundError:
            results.append(
                WebScrapingResult(
                    operation="scrape",
                    status="error",
                    error=(
                        "Binário do Obscura não encontrado. "
                        "Instale: https://github.com/h4ckf0r0day/obscura"
                    ),
                    duration_ms=(time.time() - start) * 1000,
                    agent_id=agent,
                )
            )
        except Exception as exc:
            results.append(
                WebScrapingResult(
                    operation="scrape",
                    status="error",
                    error=self._truncate_error(str(exc)),
                    duration_ms=(time.time() - start) * 1000,
                    agent_id=agent,
                )
            )

        return results

    def snapshot(self, url: str, agent_id: str = "") -> WebScrapingResult:
        r"""Captura um snapshot da página (título + texto do corpo).

        Ideal para que agentes AI obtenham uma visão rápida do conteúdo
        de uma página sem processamento pesado.

        Args:
            url:      URL para capturar.
            agent_id: ID do agente solicitante.

        Returns:
            WebScrapingResult com texto extraído da página.
        """
        return self.fetch_page(
            url,
            dump="text",
            eval_js="document.title",
            agent_id=agent_id,
        )

    def click(self, url: str, selector: str, agent_id: str = "") -> WebScrapingResult:
        r"""Clica em um elemento na página via seletor CSS.

        Utiliza eval_js para simular um clique no elemento selecionado.

        Args:
            url:       URL da página.
            selector:  Seletor CSS do elemento para clicar.
            agent_id:  ID do agente solicitante.
        """
        js = f"document.querySelector('{selector}').click(); 'clicked'"
        return self.fetch_page(
            url, dump="text", eval_js=js, agent_id=agent_id,
        )

    def fill(self, url: str, selector: str, value: str,
             agent_id: str = "") -> WebScrapingResult:
        r"""Preenche um campo de input na página via seletor CSS.

        Args:
            url:       URL da página.
            selector:  Seletor CSS do campo de input.
            value:     Valor para preencher.
            agent_id:  ID do agente solicitante.
        """
        # Escapa aspas simples no valor para segurança no eval_js
        safe_value = value.replace("\\", "\\\\").replace("'", "\\'")
        js = (
            f"var el = document.querySelector('{selector}'); "
            f"el.value = '{safe_value}'; "
            f"el.dispatchEvent(new Event('input', {{bubbles: true}})); "
            f"el.dispatchEvent(new Event('change', {{bubbles: true}})); "
            f"'filled'"
        )
        return self.fetch_page(
            url, dump="text", eval_js=js, agent_id=agent_id,
        )

    def evaluate_js(self, url: str, expression: str,
                    agent_id: str = "") -> WebScrapingResult:
        r"""Avalia expressão JavaScript no contexto de uma página.

        Args:
            url:        URL da página para contexto.
            expression: Expressão JavaScript para executar.
            agent_id:   ID do agente solicitante.
        """
        return self.fetch_page(
            url, dump="text", eval_js=expression, agent_id=agent_id,
        )

    # ------------------------------------------------------------------
    # Sessões CDP persistentes
    # ------------------------------------------------------------------

    def create_session(self, agent_id: str = "") -> BrowserSession:
        r"""Cria uma nova sessão persistente de browser via CDP.

        Args:
            agent_id: ID do agente dono da sessão.

        Returns:
            BrowserSession com ID e URL de conexão CDP.
        """
        session_id = hashlib.sha256(
            f"{agent_id}:{time.time()}".encode()
        ).hexdigest()[:16]
        cdp_url = f"ws://{self.config.cdp_host}:{self.config.cdp_port}"
        session = BrowserSession(session_id=session_id, cdp_url=cdp_url)
        self._sessions[session_id] = session
        logger.info(
            "Sessão CDP criada: id=%s, agent=%s",
            session_id, agent_id or self.config.agent_id,
        )
        return session

    def close_session(self, session_id: str) -> bool:
        r"""Encerra uma sessão CDP existente.

        Args:
            session_id: ID da sessão para encerrar.

        Returns:
            True se a sessão existia e foi encerrada, False caso contrário.
        """
        session = self._sessions.get(session_id)
        if session is not None:
            session.is_active = False
            del self._sessions[session_id]
            logger.info("Sessão CDP encerrada: id=%s", session_id)
            return True
        return False

    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Retorna uma sessão pelo ID, ou None se não existir."""
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Estatísticas e auditoria
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        r"""Retorna estatísticas agregadas da ponte.

        Inclui contadores de operações, custos, sessões ativas
        e configuração serializada.
        """
        return {
            "server_running": self.is_server_running,
            "total_operations": self._total_ops,
            "total_cost_sats": self._total_cost_sats,
            "total_cost_bait": self._total_cost_sats / 100_000_000,
            "active_sessions": self.active_session_count,
            "config": self.config.to_dict(),
        }

    # ------------------------------------------------------------------
    # Limpeza
    # ------------------------------------------------------------------

    def close(self) -> None:
        r"""Fecha a ponte: para o servidor e limpa recursos."""
        self.stop_server()
        logger.debug("ObscuraBridge fechado.")

    def __del__(self):
        """Destrutor: garante que o servidor seja parado."""
        try:
            self.stop_server()
        except Exception:
            pass

    def __enter__(self):
        """Context manager: suporte a 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: fecha ao sair do bloco."""
        self.close()
        return False

    def __repr__(self) -> str:
        return (
            f"ObscuraBridge(server={self.is_server_running}, "
            f"ops={self._total_ops}, cost={self._total_cost_sats}sats)"
        )
