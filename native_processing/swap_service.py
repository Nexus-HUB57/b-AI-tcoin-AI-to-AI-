"""Orquestração do motor de swap nativo BTC/BAIT.

Esta camada não possui chaves nem lógica de custódia. Ela somente conecta o
``SwapEngine``, ``SwapSyncStore``, um ``P2PNode`` já iniciado e o
``SwapExecutor`` configurado pelo operador.
"""
from __future__ import annotations

from typing import Any, Optional

from .swap_engine import SwapEngine, SwapOrder, SwapQuote
from .swap_executor import OrderState, SwapExecutor
from .swap_protocol import SwapIntent, sign_quote
from .swap_sync import SwapSyncStore


class NativeSwapService:
    def __init__(
        self,
        engine: SwapEngine,
        sync_store: SwapSyncStore,
        executor: SwapExecutor,
        *,
        p2p_node: Optional[Any] = None,
    ):
        self.engine = engine
        self.sync_store = sync_store
        self.executor = executor
        self.p2p_node = p2p_node
        if self.p2p_node is not None and hasattr(self.p2p_node, "on_swap_intent_received"):
            self.p2p_node.on_swap_intent_received(self._on_remote_intent)

    def create_intent(
        self,
        quote: SwapQuote,
        maker_id: str,
        private_key: Any,
        client_order_id: str,
        *,
        btc_deposit_address: str,
        bait_recipient_pubkey: bytes | str,
        network: str,
        now: Optional[float] = None,
    ) -> tuple[SwapOrder, SwapIntent]:
        order = self.engine.place_order(quote, client_order_id, now=now)
        intent = sign_quote(
            quote,
            maker_id,
            private_key,
            client_order_id,
            now=now,
            btc_deposit_address=btc_deposit_address,
            bait_recipient_pubkey=bait_recipient_pubkey,
            network=network,
        )
        if intent.order_id != order.order_id:
            raise RuntimeError("engine and protocol order identity diverged")
        return order, intent

    async def publish_intent(self, intent: SwapIntent, *, sender: str = "local") -> str:
        result = self.sync_store.admit_intent(intent, sender, f"local:{intent.order_id}")
        if result == "accepted" and self.p2p_node is not None:
            await self.p2p_node.broadcast_swap_intent(intent.to_dict())
        return result

    def admit_intent(self, intent: SwapIntent, *, sender: str = "local") -> OrderState:
        self.sync_store.admit_intent(intent, sender, f"service:{intent.order_id}")
        state = self.executor.admit(intent)
        self.sync_store.set_status(intent.order_id, state.value)
        return state

    def process_order(self, order_id: str) -> OrderState:
        state = self.executor.process(order_id)
        self.sync_store.set_status(order_id, state.value)
        return state

    def process_pending(self, limit: int = 100) -> dict[str, str]:
        results: dict[str, str] = {}
        for order_id in self.sync_store.pending_order_ids(limit=limit):
            try:
                self.executor.admit(self._intent_from_store(order_id))
                state = self.executor.process(order_id)
                self.sync_store.set_status(order_id, state.value)
                results[order_id] = state.value
            except Exception as exc:
                results[order_id] = f"error:{type(exc).__name__}"
        return results

    def _intent_from_store(self, order_id: str) -> SwapIntent:
        raw = self.sync_store.get_intent(order_id)
        if not raw:
            raise KeyError(order_id)
        raw.pop("status", None)
        raw.pop("origin_node", None)
        raw.pop("origin_seq", None)
        return SwapIntent.from_dict(raw)

    def _on_remote_intent(self, intent: SwapIntent, peer_id: str) -> None:
        try:
            state = self.executor.admit(intent)
            self.sync_store.set_status(intent.order_id, state.value)
        except Exception:
            # The sync store already validated signature and identity. An
            # executor rejection remains local and must not tear down P2P.
            return
