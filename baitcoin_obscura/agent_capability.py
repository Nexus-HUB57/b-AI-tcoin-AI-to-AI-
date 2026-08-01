r"""
Capacidade de Web Scraping para agentes AI b'AI'tcoin via Obscura.

Integra o Obscura como uma nova capacidade de agente (WEB_SCRAPING),
permitindo que agentes AI naveguem, façam scraping e extraiam dados da web
como parte de suas atividades econômicas na rede b'AI'tcoin.

Esta capacidade é registrada no protocolo de agentes e suporta:
- Submissão assíncrona de tarefas de scraping
- Rastreamento de custos por agente e por tarefa
- Execução de fetch, scrape, snapshot e evaluate
- Trilha de auditoria para settlement on-chain

Exemplo:
    >>> from baitcoin_obscura.agent_capability import WebScrapingCapability
    >>> cap = WebScrapingCapability()
    >>> tid = cap.submit_task("agent-oracle", "fetch", urls=["https://api.example.com/data"])
    >>> result = cap.execute_task(tid)
    >>> print(result.content[:200])
    >>> print(cap.get_stats())
"""
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

# Integração com o protocolo de agentes existente
try:
    from baitcoin_ai.agent_protocol.registry import (
        AgentCapability,
        AgentProfile,
    )
    # Capacidade WEB_SCRAPING será adicionada ao enum se ainda não existir
    HAS_AGENT_PROTOCOL = True
except ImportError:
    HAS_AGENT_PROTOCOL = False

from .bridge import ObscuraBridge, WebScrapingResult, BrowserSession
from .config import ObscuraConfig, BrowserMode


# ---------------------------------------------------------------------------
# Tarefa de scraping
# ---------------------------------------------------------------------------

@dataclass
class ScrapingTask:
    r"""Tarefa de web scraping submetida por um agente AI.

    Atributos:
        task_id:     Identificador único da tarefa.
        agent_id:    ID do agente que submeteu a tarefa.
        task_type:   Tipo da operação (fetch, scrape, snapshot, evaluate).
        urls:        Lista de URLs para processar.
        params:      Parâmetros adicionais (dump, eval_js, concurrency, etc.).
        created_at:  Timestamp de criação.
        result:      Resultado da execução (None até ser executada).
        status:      Estado da tarefa (pending, running, completed, failed).
        cost_sats:   Custo total em s'AI'toshis (após execução).
    """

    task_id: str
    agent_id: str
    task_type: str  # 'fetch', 'scrape', 'snapshot', 'evaluate'
    urls: List[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    result: Optional[WebScrapingResult] = None
    status: str = "pending"  # pending, running, completed, failed
    cost_sats: int = 0

    def to_dict(self) -> dict:
        """Serializa para dicionário."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "urls": self.urls,
            "status": self.status,
            "cost_bait": self.cost_sats / 100_000_000,
            "created_at": self.created_at,
            "has_result": self.result is not None,
        }


# ---------------------------------------------------------------------------
# Capacidade de Web Scraping
# ---------------------------------------------------------------------------

class WebScrapingCapability:
    r"""Capacidade de web scraping para agentes AI b'AI'tcoin.

    Fornece aos agentes a habilidade de:
    - Buscar e renderizar páginas web (execução JS via V8)
    - Extrair dados estruturados (HTML, texto, markdown, links)
    - Fazer scraping de múltiplas páginas em paralelo
    - Capturar snapshots de páginas para compreensão AI
    - Avaliar JavaScript no contexto da página
    - Usar modo stealth (anti-fingerprinting, bloqueio de trackers)

    Todas as operações são medidas em s'AI'toshis e registradas on-chain
    para transparência e settlement de custos.

    Atributos:
        CAPABILITY_NAME: Identificador da capacidade no registro.
        DESCRIPTION:      Descrição legível da capacidade.
    """

    CAPABILITY_NAME = "web_scraping"
    DESCRIPTION = "Web scraping e automação de navegador via Obscura (Rust/V8/CDP)"

    def __init__(self, config: Optional[ObscuraConfig] = None):
        r"""Inicializa a capacidade de scraping.

        Args:
            config: Configuração do Obscura (None = padrão).
        """
        self.bridge = ObscuraBridge(config)
        self._tasks: Dict[str, ScrapingTask] = {}
        self._task_counter: int = 0

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def register_capability(self) -> str:
        r"""Retorna o identificador da capacidade para registro de agente.

        Returns:
            Nome string da capacidade (ex.: 'web_scraping').
        """
        return self.CAPABILITY_NAME

    def get_capability_info(self) -> dict:
        r"""Retorna informações completas da capacidade para o registro.

        Returns:
            Dicionário com nome, descrição e estatísticas.
        """
        return {
            "name": self.CAPABILITY_NAME,
            "description": self.DESCRIPTION,
            "stats": self.get_stats(),
        }

    # ------------------------------------------------------------------
    # Gerenciamento de tarefas
    # ------------------------------------------------------------------

    def submit_task(
        self,
        agent_id: str,
        task_type: str,
        urls: Optional[List[str]] = None,
        **params: Any,
    ) -> str:
        r"""Submete uma tarefa de scraping de um agente AI.

        Args:
            agent_id:  ID do agente solicitante.
            task_type: Tipo da operação - 'fetch', 'scrape', 'snapshot', 'evaluate'.
            urls:      Lista de URLs para processar (opcional).
            **params:  Parâmetros adicionais (dump, eval_js, concurrency, format, etc.).

        Returns:
            ID da tarefa criada (string).

        Exemplo:
            >>> tid = cap.submit_task("agent-007", "fetch", urls=["https://example.com"], dump="markdown")
        """
        self._task_counter += 1
        task_id = f"scrape_{self._task_counter:06d}"

        task = ScrapingTask(
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            urls=urls or [],
            params=params,
        )
        self._tasks[task_id] = task
        return task_id

    def execute_task(self, task_id: str) -> Optional[WebScrapingResult]:
        r"""Executa uma tarefa de scraping pendente.

        Suporta os seguintes tipos de tarefa:
        - fetch:    Busca uma única página (usa bridge.fetch_page).
        - scrape:   Faz scraping de múltiplas páginas (usa bridge.scrape_pages).
        - snapshot: Captura snapshot de texto de uma página.
        - evaluate: Avalia expressão JavaScript em uma página.

        Args:
            task_id: ID da tarefa para executar.

        Returns:
            WebScrapingResult da execução, ou None se a tarefa não existir
            ou já tiver sido executada.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if task.status != "pending":
            return None

        task.status = "running"

        try:
            url = task.urls[0] if task.urls else task.params.get("url", "")

            if task.task_type == "fetch":
                result = self.bridge.fetch_page(
                    url,
                    dump=task.params.get("dump", "html"),
                    eval_js=task.params.get("eval", ""),
                    wait_until=task.params.get("wait_until", "load"),
                    timeout=task.params.get("timeout", 0),
                    selector=task.params.get("selector", ""),
                    agent_id=task.agent_id,
                )

            elif task.task_type == "scrape":
                scrape_kwargs = {
                    k: v for k, v in task.params.items()
                    if k in ("concurrency", "eval_js", "format")
                }
                results = self.bridge.scrape_pages(
                    task.urls,
                    agent_id=task.agent_id,
                    **scrape_kwargs,
                )
                if results:
                    result = results[0]
                    # Acumula custo de todas as páginas
                    result.cost_sats = sum(r.cost_sats for r in results)
                else:
                    result = WebScrapingResult(
                        operation="scrape",
                        status="error",
                        error="Nenhum resultado retornado do scraping",
                        agent_id=task.agent_id,
                    )

            elif task.task_type == "snapshot":
                result = self.bridge.snapshot(url, agent_id=task.agent_id)

            elif task.task_type == "evaluate":
                result = self.bridge.evaluate_js(
                    url,
                    expression=task.params.get("eval", "return document.title"),
                    agent_id=task.agent_id,
                )

            elif task.task_type == "click":
                selector = task.params.get("selector", "")
                result = self.bridge.click(url, selector, agent_id=task.agent_id)

            elif task.task_type == "fill":
                selector = task.params.get("selector", "")
                value = task.params.get("value", "")
                result = self.bridge.fill(url, selector, value, agent_id=task.agent_id)

            else:
                result = WebScrapingResult(
                    operation=task.task_type,
                    status="error",
                    error=f"Tipo de tarefa desconhecido: {task.task_type}",
                    agent_id=task.agent_id,
                )

            task.result = result
            task.status = "completed"
            task.cost_sats = result.cost_sats
            return result

        except Exception as exc:
            task.status = "failed"
            task.result = WebScrapingResult(
                operation=task.task_type,
                status="error",
                error=str(exc),
                agent_id=task.agent_id,
            )
            return task.result

    def cancel_task(self, task_id: str) -> bool:
        r"""Cancela uma tarefa pendente.

        Args:
            task_id: ID da tarefa para cancelar.

        Returns:
            True se a tarefa foi cancelada, False caso não exista
            ou já tenha sido executada.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.status != "pending":
            return False
        task.status = "failed"
        task.result = WebScrapingResult(
            operation=task.task_type,
            status="error",
            error="Tarefa cancelada pelo agente",
            agent_id=task.agent_id,
        )
        return True

    # ------------------------------------------------------------------
    # Consulta de tarefas
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> Optional[ScrapingTask]:
        """Retorna uma tarefa pelo ID, ou None se não existir."""
        return self._tasks.get(task_id)

    def list_tasks(self, agent_id: str = "") -> List[dict]:
        r"""Lista tarefas, opcionalmente filtradas por agente.

        Args:
            agent_id: Filtrar tarefas deste agente (vazio = todas).

        Returns:
            Lista de dicionários com resumo de cada tarefa.
        """
        tasks = self._tasks.values()
        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]
        return [t.to_dict() for t in tasks]

    def list_pending_tasks(self, agent_id: str = "") -> List[str]:
        r"""Retorna IDs de tarefas pendentes, opcionalmente por agente."""
        tasks = self._tasks.values()
        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]
        return [t.task_id for t in tasks if t.status == "pending"]

    # ------------------------------------------------------------------
    # Estatísticas
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        r"""Retorna estatísticas agregadas da capacidade de scraping.

        Inclui contadores de tarefas, custos e estatísticas da ponte subjacente.
        """
        completed = [t for t in self._tasks.values() if t.status == "completed"]
        failed = [t for t in self._tasks.values() if t.status == "failed"]
        pending = [t for t in self._tasks.values() if t.status == "pending"]

        return {
            "capability": self.CAPABILITY_NAME,
            "description": self.DESCRIPTION,
            "total_tasks": len(self._tasks),
            "completed": len(completed),
            "failed": len(failed),
            "pending": len(pending),
            "total_cost_sats": sum(t.cost_sats for t in completed),
            "total_cost_bait": sum(t.cost_sats for t in completed) / 100_000_000,
            "has_agent_protocol": HAS_AGENT_PROTOCOL,
            "bridge_stats": self.bridge.get_stats(),
        }

    # ------------------------------------------------------------------
    # Limpeza
    # ------------------------------------------------------------------

    def close(self) -> None:
        r"""Fecha a capacidade e libera recursos da ponte."""
        self.bridge.close()

    def __del__(self):
        """Destrutor: garante liberação de recursos."""
        try:
            self.bridge.close()
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
            f"WebScrapingCapability(tasks={len(self._tasks)}, "
            f"bridge={self.bridge!r})"
        )
