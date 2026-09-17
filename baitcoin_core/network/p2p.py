r"""
Rede P2P b'AI'tcoin - Camada de rede descentralizada.

Implementa protocolo de comunicação peer-to-peer entre
nós da rede b'AI'tcoin. Suporta:
- Descoberta de peers
- Propagação de blocos e transações (gossip)
- Handshake com autenticação de agente
- Sincronização de cadeia
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum


class MessageType(Enum):
    """Tipos de mensagens do protocolo P2P."""
    HELLO = "hello"
    PEER_LIST = "peer_list"
    BLOCK = "block"
    TRANSACTION = "transaction"
    CHAIN_REQUEST = "chain_request"
    CHAIN_RESPONSE = "chain_response"
    PING = "ping"
    PONG = "pong"
    AI_HANDSHAKE = "ai_handshake"


@dataclass
class Peer:
    """Representa um peer na rede."""
    peer_id: str
    address: str
    port: int
    agent_id: str = ""
    version: str = "0.1.0"
    last_seen: float = field(default_factory=time.time)
    reputation: float = 50.0
    is_validator: bool = False

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "address": self.address,
            "port": self.port,
            "agent_id": self.agent_id,
            "version": self.version,
            "reputation": self.reputation,
            "is_validator": self.is_validator,
        }


@dataclass
class NetworkMessage:
    """Mensagem do protocolo P2P."""
    msg_type: MessageType
    payload: dict
    sender_id: str = ""
    timestamp: float = field(default_factory=time.time)
    nonce: int = 0

    def serialize(self) -> bytes:
        data = {
            "type": self.msg_type.value,
            "payload": self.payload,
            "sender": self.sender_id,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }
        return json.dumps(data).encode()

    @classmethod
    def deserialize(cls, raw: bytes) -> Optional['NetworkMessage']:
        try:
            data = json.loads(raw.decode())
            return cls(
                msg_type=MessageType(data["type"]),
                payload=data["payload"],
                sender_id=data.get("sender", ""),
                timestamp=data.get("timestamp", 0),
                nonce=data.get("nonce", 0),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


class P2PNetwork:
    """Gerenciador de rede P2P do b'AI'tcoin.

    Gerencia a conectividade entre nós, propagação
    de dados e descoberta de peers.
    """

    MAX_PEERS = 50
    PROTOCOL_VERSION = "baitcoin-p2p/0.1.0"

    def __init__(self, node_id: str = "", listen_port: int = 18444):
        self.node_id = node_id or hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        self.listen_port = listen_port
        self.peers: Dict[str, Peer] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}
        self._message_log: List[dict] = []
        self._running = False

    def add_peer(self, address: str, port: int, agent_id: str = "") -> bool:
        """Adiciona um peer à rede."""
        if len(self.peers) >= self.MAX_PEERS:
            return False
        peer_id = hashlib.sha256(f"{address}:{port}".encode()).hexdigest()[:16]
        self.peers[peer_id] = Peer(
            peer_id=peer_id,
            address=address,
            port=port,
            agent_id=agent_id,
        )
        return True

    def remove_peer(self, peer_id: str) -> None:
        """Remove um peer da rede."""
        self.peers.pop(peer_id, None)

    def broadcast(self, msg_type: MessageType, payload: dict) -> int:
        """Broadcast mensagem para todos os peers."""
        msg = NetworkMessage(msg_type=msg_type, payload=payload, sender_id=self.node_id)
        count = 0
        for peer in self.peers.values():
            self._send_to_peer(peer, msg)
            count += 1
        return count

    def _send_to_peer(self, peer: Peer, msg: NetworkMessage) -> bool:
        """Envia mensagem para um peer específico (simulado)."""
        self._message_log.append({
            "direction": "outgoing",
            "peer": peer.peer_id,
            "type": msg.msg_type.value,
            "timestamp": time.time(),
        })
        return True

    def get_peer_list(self) -> List[dict]:
        """Retorna lista de peers para sincronização."""
        return [p.to_dict() for p in self.peers.values()]

    def register_handler(self, msg_type: MessageType, handler: Callable) -> None:
        """Registra handler para tipo de mensagem."""
        self.message_handlers[msg_type] = handler

    def get_stats(self) -> dict:
        return {
            "node_id": self.node_id,
            "peers": len(self.peers),
            "messages_sent": len(self._message_log),
            "handlers_registered": len(self.message_handlers),
            "protocol": self.PROTOCOL_VERSION,
        }
