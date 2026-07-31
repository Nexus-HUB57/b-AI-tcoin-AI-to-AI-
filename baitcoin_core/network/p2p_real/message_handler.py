r"""Message Handler - Processa mensagens P2P recebidas.

Dispacha mensagens para callbacks registrados e gerencia
o fluxo de dados entre peers.
"""
import json
import time
from typing import Callable, Dict, List, Optional, Any
from baitcoin_core.network.p2p_real.protocol import MsgType, NetworkMessage


class MessageHandler:
    r"""Gerencia handlers para mensagens P2P.

    Cada tipo de mensagem pode ter múltiplos callbacks registrados.
    Mensagens são processadas em ordem de chegada.
    """

    def __init__(self):
        self._callbacks: Dict[MsgType, List[Callable]] = {}
        self._global_callbacks: List[Callable] = []
        self._stats = {
            "received": 0,
            "processed": 0,
            "errors": 0,
            "by_type": {},
        }

    def on(self, msg_type: MsgType) -> Callable:
        r"""Decorador para registrar handler."""
        def decorator(fn: Callable) -> Callable:
            if msg_type not in self._callbacks:
                self._callbacks[msg_type] = []
            self._callbacks[msg_type].append(fn)
            return fn
        return decorator

    def on_any(self, fn: Callable) -> None:
        r"""Registra callback para qualquer mensagem."""
        self._global_callbacks.append(fn)

    def handle(self, msg: NetworkMessage, peer_id: str = "") -> bool:
        r"""Processa uma mensagem recebida."""
        self._stats["received"] += 1
        try:
            # Global handlers
            for cb in self._global_callbacks:
                try:
                    cb(msg, peer_id)
                except Exception:
                    pass

            # Type-specific handlers
            callbacks = self._callbacks.get(msg.msg_type, [])
            for cb in callbacks:
                try:
                    payload = self._parse_payload(msg)
                    cb(payload, peer_id)
                except Exception as e:
                    self._stats["errors"] += 1

            self._stats["processed"] += 1

            # Track stats per type
            type_name = msg.msg_type.name
            self._stats["by_type"][type_name] = self._stats["by_type"].get(type_name, 0) + 1

            return True
        except Exception:
            self._stats["errors"] += 1
            return False

    def _parse_payload(self, msg: NetworkMessage) -> Any:
        r"""Tenta fazer parse JSON do payload."""
        try:
            return json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return msg.payload

    def get_stats(self) -> dict:
        return dict(self._stats)
