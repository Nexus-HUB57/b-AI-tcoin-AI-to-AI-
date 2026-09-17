r"""
P2P Bridge - Conecta o P2P v0.2 (asyncio TCP) ao daemon síncrono.

O P2PNode é asyncio, mas o daemon_wrapper roda síncrono.
Esta bridge executa o loop asyncio numa thread separada
e expõe interface síncrona para o daemon.
"""
import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Dict, List, Any

logger = logging.getLogger("baitcoin.p2p_bridge")


class P2PBridge:
    r"""Bridge síncrono para o P2PNode asyncio.

    Gerencia:
    - Loop asyncio em thread dedicada
    - Inicialização e ciclo de vida do P2PNode
    - Interface síncrona para broadcast/status
    - Callbacks de integração com blockchain
    """

    DEFAULT_PORT = 18444
    DEFAULT_SEEDS = [
        ("127.0.0.1", 18444),
        ("127.0.0.1", 18445),
        ("127.0.0.1", 18446),
    ]

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT,
                 node_id: str = "", agent_id: str = "",
                 seeds: Optional[List[tuple]] = None):
        self.host = host
        self.port = port
        self._node_id = node_id
        self.agent_id = agent_id
        self.seeds = seeds or self.DEFAULT_SEEDS

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._node = None
        self._running = False

        # Blockchain hooks (preenchidos pelo daemon)
        self._get_block_fn = None
        self._get_headers_fn = None
        self._get_height_fn = None
        self._on_block_received = None
        self._on_tx_received = None

        # Compatibilidade com interface P2PNetwork v0.1 (usada pelo API handler)
        self.peers: Dict[str, Any] = {}
        self._message_log: List[dict] = []

    def set_blockchain_hooks(self, get_block, get_headers, get_height) -> None:
        r"""Registra funções de consulta ao blockchain."""
        self._get_block_fn = get_block
        self._get_headers_fn = get_headers
        self._get_height_fn = get_height

    def set_callbacks(self, on_block, on_tx) -> None:
        r"""Registra callbacks para blocos e transações recebidas."""
        self._on_block_received = on_block
        self._on_tx_received = on_tx

    def start(self) -> None:
        r"""Inicia o P2P node numa thread asyncio dedicada."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="p2p-asyncio")
        self._thread.start()
        logger.info(f"P2P Bridge iniciado na porta {self.port} (thread asyncio)")

    def _run_loop(self) -> None:
        r"""Loop asyncio rodando em thread dedicada."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            from baitcoin_core.network.p2p_real.node import P2PNode

            self._node = P2PNode(
                host=self.host,
                port=self.port,
                node_id=self._node_id,
                agent_id=self.agent_id,
                seeds=self.seeds,
            )

            # Conectar blockchain hooks
            if self._get_block_fn:
                self._node.set_blockchain_hooks(
                    self._get_block_fn,
                    self._get_headers_fn,
                    self._get_height_fn,
                )
            if self._on_block_received:
                self._node.on_block_received(self._on_block_received)
            if self._on_tx_received:
                self._node.on_tx_received(self._on_tx_received)

            self._loop.run_until_complete(self._node.start())
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"P2P loop error: {e}")
        finally:
            if self._node:
                self._loop.run_until_complete(self._node.stop())
            self._loop.close()
            self._running = False
            logger.info("P2P Bridge parado")

    def stop(self) -> None:
        r"""Para o P2P node."""
        if not self._running:
            return
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("P2P Bridge finalizado")

    def broadcast_block(self, block_data: dict) -> int:
        r"""Propaga bloco para peers (interface síncrona)."""
        if not self._node or not self._running:
            return 0
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._node.broadcast_block(block_data), self._loop
            )
            return future.result(timeout=5)
        except Exception as e:
            logger.debug(f"broadcast_block error: {e}")
            return 0

    def broadcast_tx(self, tx_data: dict) -> int:
        r"""Propaga transação para peers (interface síncrona)."""
        if not self._node or not self._running:
            return 0
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._node.broadcast_tx(tx_data), self._loop
            )
            return future.result(timeout=5)
        except Exception as e:
            logger.debug(f"broadcast_tx error: {e}")
            return 0

    @property
    def node_id(self) -> str:
        return self._node_id

    @node_id.setter
    def node_id(self, value: str):
        self._node_id = value

    def get_peer_list(self) -> List[dict]:
        r"""Retorna lista de peers (compatível com v0.1)."""
        if self._node and self._running:
            return self._node.protocol.get_peer_list()
        return []

    def get_stats(self) -> dict:
        r"""Retorna estatísticas do P2P node."""
        if self._node and self._running:
            return self._node.get_status()
        return {
            "node_id": self._node_id,
            "peers": 0,
            "messages_sent": 0,
            "handlers_registered": 0,
            "protocol": "baitcoin-p2p/0.2.0",
            "bridge": True,
        }

    def to_dict(self) -> dict:
        return self.get_stats()
