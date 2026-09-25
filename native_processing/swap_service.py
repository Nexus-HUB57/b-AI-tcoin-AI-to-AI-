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
        admission = self.sync_store.admit_intent(intent, sender, f"service:{intent.order_id}")
        if admission == "conflict":
            raise ValueError(f"conflicting swap intent: {intent.order_id}")
        if admission == "duplicate" and self.sync_store.get_intent(intent.order_id) is None:
            raise ValueError(f"duplicate swap transport without persisted intent: {intent.order_id}")
        state = self.executor.admit(intent)
        self._sync_status(intent.order_id, state)
        return state

    def process_order(self, order_id: str) -> OrderState:
        state = self.executor.process(order_id)
        self._sync_status(order_id, state)
        return state

    def process_pending(self, limit: int = 100) -> dict[str, str]:
        results: dict[str, str] = {}
        for order_id in self.sync_store.pending_order_ids(limit=limit):
            try:
                self.executor.admit(self._intent_from_store(order_id))
                state = self.executor.process(order_id)
                self._sync_status(order_id, state)
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

    def _sync_status(self, order_id: str, target: OrderState) -> None:
        """Mirror executor jumps through the persisted monotonic state path.

        The executor may observe a deposit and its confirmations in one call.
        The sync store intentionally requires the observable intermediate
        ``btc_observed`` state, so every skipped state is recorded in order.
        """
        current = self.sync_store.get_intent(order_id)
        if current is None:
            raise KeyError(order_id)
        current_status = str(current["status"])
        if current_status == target.value:
            return
        if target in {OrderState.RECONCILING, OrderState.REFUNDED}:
            if current_status != target.value:
                if target == OrderState.REFUNDED and current_status != OrderState.RECONCILING:
                    self.sync_store.set_status(order_id, OrderState.RECONCILING.value)
                self.sync_store.set_status(order_id, target.value)
            return

        path = [
            OrderState.PENDING,
            OrderState.INTENT_VALIDATED,
            OrderState.BTC_OBSERVED,
            OrderState.BTC_CONFIRMED,
            OrderState.BAIT_SUBMITTED,
            OrderState.SETTLED,
        ]
        try:
            start = path.index(OrderState(current_status))
            end = path.index(target)
        except ValueError as exc:
            raise RuntimeError(f"cannot synchronize swap state {current_status} -> {target.value}") from exc
        if end < start:
            raise RuntimeError(f"swap state regression {current_status} -> {target.value}")
        for next_state in path[start + 1 : end + 1]:
            self.sync_store.set_status(order_id, next_state.value)

    def _on_remote_intent(self, intent: SwapIntent, peer_id: str) -> None:
        try:
            state = self.executor.admit(intent)
            self.sync_store.set_status(intent.order_id, state.value)
        except Exception:
            # The sync store already validated signature and identity. An
            # executor rejection remains local and must not tear down P2P.
            return
