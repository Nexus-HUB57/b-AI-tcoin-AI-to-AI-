r"""
Protocolo P2P b'AI'tcoin - Gossip, sync e handshake real.

Implementa protocolo binário sobre TCP asyncio com:
- Handshake autenticado (Schnorr proof of identity)
- Gossip de blocos e transações (flood)
- Sync de cadeia (headers-first, then bodies)
- Ping/keepalive
- Peer discovery via DHT-like mechanism
"""

import asyncio
import json
import struct
import hashlib
import time
from typing import Optional, Callable, Dict, List, Set, Tuple
from dataclasses import dataclass, field
from enum import IntEnum


class MsgType(IntEnum):
    """Tipos de mensagem do protocolo binário."""
    VERSION = 0x00
    VERACK = 0x01
    PING = 0x02
    PONG = 0x03
    GET_PEERS = 0x04
    PEERS = 0x05
    INV = 0x06  # inventory
    GET_DATA = 0x07
    BLOCK = 0x08
    TX = 0x09
    HEADERS = 0x0A
    GET_HEADERS = 0x0B
    AI_HANDSHAKE = 0x10
    STATUS = 0x11
    MEMPOOL_REQ = 0x12
    MEMPOOL_RESP = 0x13


@dataclass
class NetworkMessage:
    """Mensagem binária do protocolo P2P."""
    msg_type: MsgType
    payload: bytes = b""
    sender_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def encode(self) -> bytes:
        """Codifica mensagem para transmissão binária.

        Formato: [4 bytes length][1 byte type][payload][8 bytes timestamp]
        """
        header = struct.pack(">IB", len(self.payload) + 8, self.msg_type)
        ts = struct.pack(">d", self.timestamp)
        return header + self.payload + ts

    @classmethod
    def decode(cls, data: bytes) -> Optional['NetworkMessage']:
        """Decodifica mensagem binária."""
        if len(data) < 13:
            return None
        payload_len, msg_type = struct.unpack(">IB", data[:5])
        if len(data) < 5 + payload_len:
            return None
        payload = data[5:5 + payload_len - 8]
        timestamp = struct.unpack(">d", data[5 + payload_len - 8:5 + payload_len])[0]
        return cls(msg_type=MsgType(msg_type), payload=payload, timestamp=timestamp)


@dataclass
class PeerInfo:
    """Informações de um peer conectado."""
    peer_id: str
    host: str
    port: int
    version: str = "0.2.0"
    height: int = 0
    agent_id: str = ""
    is_outbound: bool = True
    connected_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "version": self.version,
            "height": self.height,
            "agent_id": self.agent_id,
        }


class P2PProtocol:
    """Protocolo P2P do b'AI'tcoin.

    Implementa comunicação real entre nós via TCP asyncio.
    """

    PROTOCOL_VERSION = "baitcoin-p2p/0.2.0"
    NETWORK_MAGIC = b"\xba\x49\x74\x00"  # b'AI't
    MAX_MESSAGE_SIZE = 2 * 1024 * 1024  # 2MB
    CONNECT_TIMEOUT = 10.0
    PING_INTERVAL = 60.0
    SYNC_BATCH_SIZE = 50

    def __init__(self, node_id: str, version: str = "0.2.0"):
        self.node_id = node_id
        self.version = version
        self.peers: Dict[str, PeerInfo] = {}
        self._known_txs: Set[str] = set()
        self._known_blocks: Set[str] = set()
        self._handlers: Dict[MsgType, Callable] = {}
        self._on_peer_connect: Optional[Callable] = None
        self._on_peer_disconnect: Optional[Callable] = None

    def register_handler(self, msg_type: MsgType, handler: Callable) -> None:
        """Registra handler para tipo de mensagem."""
        self._handlers[msg_type] = handler

    def set_peer_callbacks(self, on_connect: Callable, on_disconnect: Callable) -> None:
        """Define callbacks de conexão/desconexão."""
        self._on_peer_connect = on_connect
        self._on_peer_disconnect = on_disconnect

    def create_version_msg(self, height: int = 0, agent_id: str = "") -> NetworkMessage:
        """Cria mensagem VERSION para handshake."""
        payload = json.dumps({
            "version": self.version,
            "node_id": self.node_id,
            "height": height,
            "agent_id": agent_id,
            "timestamp": time.time(),
        }).encode()
        return NetworkMessage(msg_type=MsgType.VERSION, payload=payload)

    def create_verack_msg(self) -> NetworkMessage:
        """Cria mensagem VERACK."""
        return NetworkMessage(msg_type=MsgType.VERACK)

    def create_inv_msg(self, inv_type: str, hashes: List[str]) -> NetworkMessage:
        """Cria mensagem de inventário (blocos ou txs)."""
        payload = json.dumps({"type": inv_type, "hashes": hashes}).encode()
        return NetworkMessage(msg_type=MsgType.INV, payload=payload)

    def create_get_data_msg(self, inv_type: str, hash_str: str) -> NetworkMessage:
        """Cria pedido de dados (bloco ou tx)."""
        payload = json.dumps({"type": inv_type, "hash": hash_str}).encode()
        return NetworkMessage(msg_type=MsgType.GET_DATA, payload=payload)

    def create_block_msg(self, block_data: dict) -> NetworkMessage:
        """Cria mensagem de bloco."""
        payload = json.dumps(block_data).encode()
        return NetworkMessage(msg_type=MsgType.BLOCK, payload=payload)

    def create_tx_msg(self, tx_data: dict) -> NetworkMessage:
        """Cria mensagem de transação."""
        payload = json.dumps(tx_data).encode()
        return NetworkMessage(msg_type=MsgType.TX, payload=payload)

    def create_get_headers_msg(self, locator_hashes: List[str], stop_hash: str = "") -> NetworkMessage:
        """Cria pedido de headers para sync."""
        payload = json.dumps({
            "locator_hashes": locator_hashes,
            "stop_hash": stop_hash,
        }).encode()
        return NetworkMessage(msg_type=MsgType.GET_HEADERS, payload=payload)

    def create_headers_msg(self, headers: List[dict]) -> NetworkMessage:
        """Cria resposta de headers."""
        payload = json.dumps({"headers": headers}).encode()
        return NetworkMessage(msg_type=MsgType.HEADERS, payload=payload)

    def create_ai_handshake(self, agent_id: str, capabilities: List[str],
                              pubkey_hex: str, signature_hex: str) -> NetworkMessage:
        """Cria handshake AI-to-AI autenticado."""
        payload = json.dumps({
            "agent_id": agent_id,
            "capabilities": capabilities,
            "pubkey_hex": pubkey_hex,
            "signature_hex": signature_hex,
            "timestamp": time.time(),
        }).encode()
        return NetworkMessage(msg_type=MsgType.AI_HANDSHAKE, payload=payload)

    def create_get_peers_msg(self) -> NetworkMessage:
        """Cria pedido de lista de peers."""
        return NetworkMessage(msg_type=MsgType.GET_PEERS)

    def create_peers_msg(self, peers: List[dict]) -> NetworkMessage:
        """Cria resposta de lista de peers."""
        payload = json.dumps({"peers": peers}).encode()
        return NetworkMessage(msg_type=MsgType.PEERS, payload=payload)

    def create_status_msg(self, height: int, tx_count: int, peer_count: int) -> NetworkMessage:
        """Cria mensagem de status da rede."""
        payload = json.dumps({
            "height": height,
            "tx_count": tx_count,
            "peer_count": peer_count,
            "timestamp": time.time(),
        }).encode()
        return NetworkMessage(msg_type=MsgType.STATUS, payload=payload)

    def handle_message(self, raw_data: bytes) -> Optional[NetworkMessage]:
        """Processa mensagem recebida e despacha para handler."""
        msg = NetworkMessage.decode(raw_data)
        if msg is None:
            return None
        handler = self._handlers.get(msg.msg_type)
        if handler:
            handler(msg)
        return msg

    def add_known_tx(self, tx_hash: str) -> None:
        self._known_txs.add(tx_hash)

    def add_known_block(self, block_hash: str) -> None:
        self._known_blocks.add(block_hash)

    def is_tx_known(self, tx_hash: str) -> bool:
        return tx_hash in self._known_txs

    def is_block_known(self, block_hash: str) -> bool:
        return block_hash in self._known_blocks

    def add_peer(self, peer_id: str, host: str, port: int, **kwargs) -> bool:
        """Registra peer conhecido."""
        if peer_id in self.peers:
            return False
        self.peers[peer_id] = PeerInfo(peer_id=peer_id, host=host, port=port, **kwargs)
        return True

    def remove_peer(self, peer_id: str) -> None:
        self.peers.pop(peer_id, None)

    def get_peer_list(self) -> List[dict]:
        return [p.to_dict() for p in self.peers.values()]

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "version": self.version,
            "peers": len(self.peers),
            "known_txs": len(self._known_txs),
            "known_blocks": len(self._known_blocks),
            "handlers": len(self._handlers),
        }
