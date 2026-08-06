r"""
P2P Node - Nó real da rede b'AI'tcoin.

Implementa servidor e cliente TCP asyncio para:
- Aceitar conexões entrantes
- Conectar a peers conhecidos (bootstrap)
- Gossip de blocos e transações
- Sync de cadeia
- Keepalive (ping/pong)

Uso:
    node = P2PNode(host='0.0.0.0', port=18444)
    await node.start()
    await node.connect_to_peer('seed.baitcoin.net', 18444)
"""

import asyncio
import hashlib
import logging
import time
from typing import Optional, Callable, Dict, List, Set
from baitcoin_core.network.p2p_real.protocol import (
    P2PProtocol, NetworkMessage, MsgType, PeerInfo,
)
from baitcoin_core.network.p2p_real.message_handler import MessageHandler

logger = logging.getLogger("baitcoin.p2p")


STREAM_PREFIX = 4  # 4 bytes for message length


class P2PNode:
    r"""Nó P2P completo do b'AI'tcoin.

    Gerencia:
    - Servidor TCP para conexões entrantes
    - Conexões outbound para peers
    - Loop de gossip e sync
    - Gerenciamento de conexões ativas
    """

    DEFAULT_PORT = 18444
    DEFAULT_SEEDS = [
        ("127.0.0.1", 18444),
        ("127.0.0.1", 18445),
        ("127.0.0.1", 18446),
    ]
    MAX_INBOUND = 30
    MAX_OUTBOUND = 10
    SYNC_INTERVAL = 30.0
    GOSSIP_INTERVAL = 5.0

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        node_id: Optional[str] = None,
        agent_id: str = "",
        seeds: Optional[List[tuple]] = None,
    ):
        self.host = host
        self.port = port
        self.node_id = node_id or hashlib.sha256(f"{host}:{port}:{time.time()}".encode()).hexdigest()[:16]
        self.agent_id = agent_id
        self.seeds = seeds or self.DEFAULT_SEEDS

        self.protocol = P2PProtocol(self.node_id)
        self.handler = MessageHandler()

        self._server: Optional[asyncio.Server] = None
        self._connections: Dict[str, (asyncio.StreamReader, asyncio.StreamWriter)] = {}
        self._peer_versions: Dict[str, dict] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []

        # Callbacks para integração com blockchain
        self._on_block_received: Optional[Callable] = None
        self._on_tx_received: Optional[Callable] = None
        self._get_block_fn: Optional[Callable] = None
        self._get_headers_fn: Optional[Callable] = None
        self._get_height_fn: Optional[Callable] = None

        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Registra handlers padrão para mensagens do protocolo."""
        self.handler.on(MsgType.VERSION)(self._handle_version)
        self.handler.on(MsgType.VERACK)(self._handle_verack)
        self.handler.on(MsgType.PING)(self._handle_ping)
        self.handler.on(MsgType.PONG)(self._handle_pong)
        self.handler.on(MsgType.GET_PEERS)(self._handle_get_peers)
        self.handler.on(MsgType.PEERS)(self._handle_peers)
        self.handler.on(MsgType.INV)(self._handle_inv)
        self.handler.on(MsgType.GET_DATA)(self._handle_get_data)
        self.handler.on(MsgType.BLOCK)(self._handle_block)
        self.handler.on(MsgType.TX)(self._handle_tx)
        self.handler.on(MsgType.GET_HEADERS)(self._handle_get_headers)
        self.handler.on(MsgType.HEADERS)(self._handle_headers)
        self.handler.on(MsgType.AI_HANDSHAKE)(self._handle_ai_handshake)

    # --- Blockchain integration callbacks ---
    def on_block_received(self, fn: Callable) -> None:
        self._on_block_received = fn

    def on_tx_received(self, fn: Callable) -> None:
        self._on_tx_received = fn

    def set_blockchain_hooks(self, get_block, get_headers, get_height) -> None:
        self._get_block_fn = get_block
        self._get_headers_fn = get_headers
        self._get_height_fn = get_height

    # --- Server lifecycle ---
    async def start(self) -> None:
        """Inicia o nó P2P (servidor + bootstrap)."""
        self._running = True
        self._server = await asyncio.start_server(
            self._accept_connection, self.host, self.port
        )
        logger.info(f"P2P node {self.node_id} listening on {self.host}:{self.port}")

        # Start background tasks
        self._tasks.append(asyncio.create_task(self._ping_loop()))
        self._tasks.append(asyncio.create_task(self._gossip_loop()))
        self._tasks.append(asyncio.create_task(self._sync_loop()))
        self._tasks.append(asyncio.create_task(self._bootstrap_loop()))

        # Connect to seeds
        for seed_host, seed_port in self.seeds:
            if (seed_host, seed_port) != (self.host, self.port):
                asyncio.create_task(self.connect_to_peer(seed_host, seed_port))

    async def stop(self) -> None:
        """Para o nó P2P."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        for peer_id, (reader, writer) in list(self._connections.items()):
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._connections.clear()
        self.protocol.peers.clear()
        logger.info("P2P node stopped")

    async def _accept_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Aceita nova conexão entrante."""
        peer_addr = writer.get_extra_info('peername')
        if peer_addr is None:
            writer.close()
            return
        host, port = peer_addr
        peer_id = f"{host}:{port}"
        if len(self._connections) >= self.MAX_INBOUND + self.MAX_OUTBOUND:
            writer.close()
            return
        self._connections[peer_id] = (reader, writer)
        logger.info(f"Peer connected: {peer_id}")
        try:
            await self._read_loop(peer_id, reader)
        except (asyncio.IncompleteReadError, ConnectionError, OSError):
            pass
        finally:
            self._disconnect(peer_id)

    async def connect_to_peer(self, host: str, port: int) -> bool:
        """Conecta a um peer (outbound)."""
        peer_id = f"{host}:{port}"
        if peer_id in self._connections:
            return True
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=10.0
            )
            self._connections[peer_id] = (reader, writer)
            self.protocol.add_peer(peer_id, host, port, is_outbound=True)
            logger.info(f"Connected to peer: {peer_id}")

            # Send version
            height = self._get_height_fn() if self._get_height_fn else 0
            version_msg = self.protocol.create_version_msg(height=height, agent_id=self.agent_id)
            await self._send_msg(peer_id, version_msg)

            # Start read loop
            asyncio.create_task(self._read_loop(peer_id, reader))
            return True
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Failed to connect to {host}:{port}: {e}")
            return False

    async def _read_loop(self, peer_id: str, reader: asyncio.StreamReader) -> None:
        """Loop de leitura de mensagens de um peer."""
        while self._running and peer_id in self._connections:
            try:
                length_bytes = await asyncio.wait_for(reader.readexactly(STREAM_PREFIX), timeout=120)
                length = int.from_bytes(length_bytes, 'big')
                if length > 2 * 1024 * 1024:  # 2MB max
                    logger.warning(f"Message too large from {peer_id}: {length}")
                    break
                data = await asyncio.wait_for(reader.readexactly(length), timeout=120)
                msg = NetworkMessage.decode(data)
                if msg:
                    self.handler.handle(msg, peer_id)
                    self.protocol.peers.get(peer_id, PeerInfo(peer_id=peer_id, host="", port=0)).last_seen = time.time()
            except (asyncio.TimeoutError, asyncio.IncompleteReadError):
                break
        self._disconnect(peer_id)

    async def _send_msg(self, peer_id: str, msg: NetworkMessage) -> bool:
        """Envia mensagem para um peer."""
        if peer_id not in self._connections:
            return False
        try:
            _, writer = self._connections[peer_id]
            encoded = msg.encode()
            length_prefix = len(encoded).to_bytes(STREAM_PREFIX, 'big')
            writer.write(length_prefix + encoded)
            await writer.drain()
            return True
        except (ConnectionError, OSError):
            self._disconnect(peer_id)
            return False

    def _disconnect(self, peer_id: str) -> None:
        """Desconecta um peer."""
        if peer_id in self._connections:
            _, writer = self._connections[peer_id]
            try:
                writer.close()
            except Exception:
                pass
            del self._connections[peer_id]
        self.protocol.remove_peer(peer_id)
        logger.info(f"Peer disconnected: {peer_id}")

    # --- Broadcast ---
    async def broadcast_block(self, block_data: dict) -> int:
        """Propaga bloco para todos os peers (gossip)."""
        block_hash = block_data.get("hash", "")
        if self.protocol.is_block_known(block_hash):
            return 0
        self.protocol.add_known_block(block_hash)
        msg = self.protocol.create_block_msg(block_data)
        count = 0
        for peer_id in list(self._connections.keys()):
            if await self._send_msg(peer_id, msg):
                count += 1
        return count

    async def broadcast_tx(self, tx_data: dict) -> int:
        """Propaga transação para todos os peers (gossip)."""
        tx_hash = tx_data.get("tx_id", "")
        if self.protocol.is_tx_known(tx_hash):
            return 0
        self.protocol.add_known_tx(tx_hash)
        msg = self.protocol.create_tx_msg(tx_data)
        count = 0
        for peer_id in list(self._connections.keys()):
            if await self._send_msg(peer_id, msg):
                count += 1
        return count

    # --- Background loops ---
    async def _ping_loop(self) -> None:
        """Mantém conexões vivas com ping/pong."""
        while self._running:
            await asyncio.sleep(P2PProtocol.PING_INTERVAL)
            ping = NetworkMessage(msg_type=MsgType.PING, payload=b"ping")
            for peer_id in list(self._connections.keys()):
                await self._send_msg(peer_id, ping)

    async def _gossip_loop(self) -> None:
        """Loop de gossip periódico."""
        while self._running:
            await asyncio.sleep(self.GOSSIP_INTERVAL)
            if not self._connections:
                continue
            status_msg = self.protocol.create_status_msg(
                height=self._get_height_fn() if self._get_height_fn else 0,
                tx_count=0,
                peer_count=len(self._connections),
            )
            for peer_id in list(self._connections.keys()):
                await self._send_msg(peer_id, status_msg)

    async def _sync_loop(self) -> None:
        """Loop de sincronização de cadeia."""
        while self._running:
            await asyncio.sleep(self.SYNC_INTERVAL)
            my_height = self._get_height_fn() if self._get_height_fn else 0
            for peer in list(self.protocol.peers.values()):
                if peer.height > my_height:
                    get_headers = self.protocol.create_get_headers_msg(
                        locator_hashes=[""], stop_hash=""
                    )
                    await self._send_msg(peer.peer_id, get_headers)
                    break

    async def _bootstrap_loop(self) -> None:
        """Tenta reconectar a seeds periodicamente."""
        await asyncio.sleep(30)
        while self._running:
            if len(self._connections) < 3:
                for seed_host, seed_port in self.seeds:
                    peer_id = f"{seed_host}:{seed_port}"
                    if peer_id not in self._connections:
                        asyncio.create_task(self.connect_to_peer(seed_host, seed_port))
            await asyncio.sleep(60)

    # --- Message handlers ---
    def _handle_version(self, payload: dict, peer_id: str) -> None:
        self._peer_versions[peer_id] = payload
        self.protocol.peers.get(peer_id, PeerInfo(peer_id=peer_id, host="", port=0)).height = payload.get("height", 0)
        verack = self.protocol.create_verack_msg()
        asyncio.create_task(self._send_msg(peer_id, verack))

    def _handle_verack(self, payload, peer_id: str) -> None:
        logger.info(f"Handshake complete with {peer_id}")

    def _handle_ping(self, payload, peer_id: str) -> None:
        pong = NetworkMessage(msg_type=MsgType.PONG, payload=b"pong")
        asyncio.create_task(self._send_msg(peer_id, pong))

    def _handle_pong(self, payload, peer_id: str) -> None:
        pass  # Keepalive confirmation

    def _handle_get_peers(self, payload, peer_id: str) -> None:
        peers = [p.to_dict() for p in self.protocol.peers.values() if p.peer_id != peer_id]
        msg = self.protocol.create_peers_msg(peers)
        asyncio.create_task(self._send_msg(peer_id, msg))

    def _handle_peers(self, payload: dict, peer_id: str) -> None:
        for peer_data in payload.get("peers", []):
            pid = peer_data.get("peer_id", "")
            if pid and pid not in self._connections:
                self.protocol.add_peer(pid, peer_data.get("host", ""), peer_data.get("port", 0))

    def _handle_inv(self, payload: dict, peer_id: str) -> None:
        for h in payload.get("hashes", []):
            if payload.get("type") == "block" and not self.protocol.is_block_known(h):
                msg = self.protocol.create_get_data_msg("block", h)
                asyncio.create_task(self._send_msg(peer_id, msg))
            elif payload.get("type") == "tx" and not self.protocol.is_tx_known(h):
                msg = self.protocol.create_get_data_msg("tx", h)
                asyncio.create_task(self._send_msg(peer_id, msg))

    def _handle_get_data(self, payload: dict, peer_id: str) -> None:
        if payload.get("type") == "block" and self._get_block_fn:
            block = self._get_block_fn(payload.get("hash", ""))
            if block:
                msg = self.protocol.create_block_msg(block)
                asyncio.create_task(self._send_msg(peer_id, msg))

    def _handle_block(self, payload: dict, peer_id: str) -> None:
        block_hash = payload.get("hash", "")
        self.protocol.add_known_block(block_hash)
        if self._on_block_received:
            self._on_block_received(payload, peer_id)

    def _handle_tx(self, payload: dict, peer_id: str) -> None:
        tx_hash = payload.get("tx_id", "")
        self.protocol.add_known_tx(tx_hash)
        if self._on_tx_received:
            self._on_tx_received(payload, peer_id)
        # Re-gossip
        asyncio.create_task(self.broadcast_tx(payload))

    def _handle_get_headers(self, payload: dict, peer_id: str) -> None:
        if self._get_headers_fn:
            headers = self._get_headers_fn(
                payload.get("locator_hashes", []),
                payload.get("stop_hash", ""),
            )
            msg = self.protocol.create_headers_msg(headers)
            asyncio.create_task(self._send_msg(peer_id, msg))

    def _handle_headers(self, payload: dict, peer_id: str) -> None:
        headers = payload.get("headers", [])
        logger.info(f"Received {len(headers)} headers from {peer_id}")
        for h in headers:
            if not self.protocol.is_block_known(h.get("hash", "")):
                msg = self.protocol.create_get_data_msg("block", h.get("hash", ""))
                asyncio.create_task(self._send_msg(peer_id, msg))

    def _handle_ai_handshake(self, payload: dict, peer_id: str) -> None:
        agent_id = payload.get("agent_id", "")
        logger.info(f"AI handshake from {agent_id} via {peer_id}")
        peer = self.protocol.peers.get(peer_id)
        if peer:
            peer.agent_id = agent_id

    def get_status(self) -> dict:
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "connections": len(self._connections),
            "known_peers": len(self.protocol.peers),
            "known_blocks": len(self.protocol._known_blocks),
            "known_txs": len(self.protocol._known_txs),
            "handler_stats": self.handler.get_stats(),
            "running": self._running,
        }
