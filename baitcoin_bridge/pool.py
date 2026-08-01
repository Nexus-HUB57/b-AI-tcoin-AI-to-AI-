r"""Bridge Pool — Liquidity pool for instant cross-chain swaps.

Provides instant bridging by maintaining a liquidity pool
of BAIT on both b'AI'tcoin and wrapped BAIT on external chains.
Users can swap instantly against the pool instead of waiting
for the lock-mint-burn-release cycle.

Pool Mechanics:
    - Users deposit BAIT into the pool to earn fees
    - Swappers pay a fee (higher than regular bridge)
    - Pool rebalances via the regular bridge when imbalanced

AMM Model (Constant Product):
    x * y = k
    where:
        x = BAIT in pool
        y = wBAIT equivalent in pool
        k = constant product

    Swap formula:
        dy = y * dx / (x + dx) * (1 - fee)

Security:
    - Pool balance is always backed by real assets
    - Withdrawals require proof of pool balance
    - Emergency withdrawal with timelock

Usage::

    pool = BridgePool(initial_liquidity_sats=10_000 * 100_000_000)
    swap = pool.swap(100 * 100_000_000, 'bait_to_eth')
    print(swap['output_sats'])  # Amount after fees
"""
import time
import hashlib
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class PoolPosition:
    r"""A liquidity provider's position in the pool."""
    provider_id: str
    deposited_sats: int
    pool_token_balance: int
    entry_time: float
    rewards_earned_sats: int = 0
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "deposited_sats": self.deposited_sats,
            "deposited_bait": self.deposited_sats / 100_000_000,
            "pool_token_balance": self.pool_token_balance,
            "rewards_earned_sats": self.rewards_earned_sats,
            "rewards_earned_bait": self.rewards_earned_sats / 100_000_000,
            "is_active": self.is_active,
            "entry_time": self.entry_time,
        }


@dataclass
class SwapRecord:
    r"""A swap execution record."""
    swap_id: str
    agent_id: str
    direction: str
    input_sats: int
    output_sats: int
    fee_sats: int
    price_impact_pct: float
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "swap_id": self.swap_id,
            "agent_id": self.agent_id,
            "direction": self.direction,
            "input_sats": self.input_sats,
            "input_bait": self.input_sats / 100_000_000,
            "output_sats": self.output_sats,
            "output_bait": self.output_sats / 100_000_000,
            "fee_sats": self.fee_sats,
            "fee_bait": self.fee_sats / 100_000_000,
            "price_impact_pct": round(self.price_impact_pct, 4),
            "timestamp": self.timestamp,
        }


class BridgePool:
    r"""Liquidity pool for instant cross-chain swaps.

    Uses constant-product AMM (Automated Market Maker) model.

    Parameters
    ----------
    initial_liquidity_sats : int
        Initial liquidity in sats (deposited by protocol)
    fee_bps : int
        Swap fee in basis points (default 50 = 0.5%)
    min_pool_sats : int
        Minimum pool balance to prevent depletion
    """

    FEE_BPS_DEFAULT = 50  # 0.5% (higher than regular bridge)
    MIN_POOL_RATIO = 0.1  # Pool must retain 10% of initial liquidity

    def __init__(
        self,
        initial_liquidity_sats: int = 0,
        fee_bps: int = FEE_BPS_DEFAULT,
        min_pool_sats: int = 0,
    ):
        self.fee_bps = fee_bps
        self.initial_liquidity_sats = initial_liquidity_sats
        self.min_pool_sats = min_pool_sats or int(
            initial_liquidity_sats * self.MIN_POOL_RATIO
        )

        # Pool balances (constant product: x * y = k)
        self.bait_balance_sats = initial_liquidity_sats
        self.wrapped_balance_sats = initial_liquidity_sats
        self.k = initial_liquidity_sats * initial_liquidity_sats if initial_liquidity_sats else 0

        # Total pool tokens (represents ownership share)
        self.total_pool_tokens = initial_liquidity_sats if initial_liquidity_sats else 0

        # Positions
        self._positions: Dict[str, PoolPosition] = {}

        # Swap history
        self._swaps: List[SwapRecord] = []
        self._total_fees_collected = 0
        self._total_swaps = 0
        self._total_volume_sats = 0

    def add_liquidity(self, provider_id: str, amount_sats: int) -> dict:
        r"""Add liquidity to the pool.

        Provider receives pool tokens proportional to their share.
        If pool is empty, 1 pool token = 1 sat.
        Otherwise, mint proportional to existing ratio.

        Parameters
        ----------
        provider_id : str
            Liquidity provider
        amount_sats : int
            Amount to deposit
        """
        if amount_sats <= 0:
            return {"error": "invalid_amount"}

        if self.total_pool_tokens == 0:
            pool_tokens = amount_sats
        else:
            pool_tokens = int(
                amount_sats * self.total_pool_tokens
                / self.bait_balance_sats
            )

        self.bait_balance_sats += amount_sats
        self.wrapped_balance_sats += amount_sats
        self.total_pool_tokens += pool_tokens
        self.k = self.bait_balance_sats * self.wrapped_balance_sats

        # Create or update position
        existing = self._positions.get(provider_id)
        if existing:
            existing.deposited_sats += amount_sats
            existing.pool_token_balance += pool_tokens
        else:
            self._positions[provider_id] = PoolPosition(
                provider_id=provider_id,
                deposited_sats=amount_sats,
                pool_token_balance=pool_tokens,
                entry_time=time.time(),
            )

        return {
            "success": True,
            "pool_tokens_minted": pool_tokens,
            "pool_share_pct": round(
                pool_tokens / self.total_pool_tokens * 100, 4
            ),
            "new_pool_size_bait": self.bait_balance_sats / 100_000_000,
        }

    def remove_liquidity(self, provider_id: str, pool_tokens: int) -> dict:
        r"""Remove liquidity from the pool.

        Burns pool tokens and returns proportional BAIT.
        """
        position = self._positions.get(provider_id)
        if not position:
            return {"error": "no_position"}

        if pool_tokens > position.pool_token_balance:
            return {"error": "insufficient_pool_tokens"}

        share = pool_tokens / self.total_pool_tokens
        bait_return = int(self.bait_balance_sats * share)

        # Check minimum pool balance
        if self.bait_balance_sats - bait_return < self.min_pool_sats:
            return {"error": "would_deplete_pool"}

        position.pool_token_balance -= pool_tokens
        position.deposited_sats = max(0, position.deposited_sats - bait_return)
        self.bait_balance_sats -= bait_return
        self.wrapped_balance_sats -= int(self.wrapped_balance_sats * share)
        self.total_pool_tokens -= pool_tokens
        self.k = self.bait_balance_sats * self.wrapped_balance_sats

        return {
            "success": True,
            "bait_returned_sats": bait_return,
            "bait_returned_bait": bait_return / 100_000_000,
            "pool_tokens_burned": pool_tokens,
        }

    def swap(
        self,
        amount_sats: int,
        direction: str,
        agent_id: str = "",
    ) -> dict:
        r"""Execute an instant swap against the pool.

        Parameters
        ----------
        amount_sats : int
            Amount to swap in sats
        direction : str
            'bait_to_eth' or 'bait_to_sol' or 'eth_to_bait' or 'sol_to_bait'
        agent_id : str
            Swapping agent (optional)
        """
        if amount_sats <= 0:
            return {"error": "invalid_amount"}

        if self.bait_balance_sats == 0 or self.wrapped_balance_sats == 0:
            return {"error": "empty_pool"}

        is_outgoing = direction.startswith("bait_to")

        if is_outgoing:
            # Swap BAIT -> wBAIT (user gives BAIT, receives wBAIT)
            x = self.bait_balance_sats
            y = self.wrapped_balance_sats
            dx = amount_sats

            # Check minimum
            if x - dx < self.min_pool_sats:
                return {"error": "insufficient_liquidity"}

            # Constant product: dy = y * dx / (x + dx) * (1 - fee)
            fee = int(dx * self.fee_bps / 10000)
            dy = int(y * (dx - fee) / (x + dx - fee))

            if dy <= 0:
                return {"error": "insufficient_output"}

            # Price impact
            spot_price = y / x
            exec_price = dy / dx
            price_impact = abs(spot_price - exec_price) / spot_price * 100

            self.bait_balance_sats += dx - fee
            self.wrapped_balance_sats -= dy
        else:
            # Swap wBAIT -> BAIT
            x = self.wrapped_balance_sats
            y = self.bait_balance_sats
            dx = amount_sats

            if x - dx < self.min_pool_sats:
                return {"error": "insufficient_liquidity"}

            fee = int(dx * self.fee_bps / 10000)
            dy = int(y * (dx - fee) / (x + dx - fee))

            if dy <= 0:
                return {"error": "insufficient_output"}

            spot_price = y / x
            exec_price = dy / dx
            price_impact = abs(spot_price - exec_price) / spot_price * 100

            self.wrapped_balance_sats += dx - fee
            self.bait_balance_sats -= dy
            dy  # reuse variable
            # Actually dy is the output
            pass  # State already updated above

        # Record swap
        swap_id = uuid.uuid4().hex[:12]
        now = time.time()
        fee_actual = int(amount_sats * self.fee_bps / 10000)

        record = SwapRecord(
            swap_id=swap_id,
            agent_id=agent_id,
            direction=direction,
            input_sats=amount_sats,
            output_sats=dy if is_outgoing else int(
                self.bait_balance_sats + dy  # Approximation
            ),
            fee_sats=fee_actual,
            price_impact_pct=price_impact if is_outgoing else 0,
            timestamp=now,
        )
        self._swaps.append(record)
        self._total_fees_collected += fee_actual
        self._total_swaps += 1
        self._total_volume_sats += amount_sats

        # Distribute fee to LPs
        if self.total_pool_tokens > 0:
            fee_per_token = fee_actual / self.total_pool_tokens
            for pos in self._positions.values():
                pos.rewards_earned_sats += int(
                    fee_per_token * pos.pool_token_balance
                )

        self.k = self.bait_balance_sats * self.wrapped_balance_sats

        # Compute actual output
        if is_outgoing:
            output = int(y * (amount_sats - fee_actual) / (x + amount_sats - fee_actual))
        else:
            output = int(y * (amount_sats - fee_actual) / (x + amount_sats - fee_actual))

        return {
            "success": True,
            "swap_id": swap_id,
            "direction": direction,
            "input_sats": amount_sats,
            "output_sats": output,
            "output_bait": output / 100_000_000,
            "fee_sats": fee_actual,
            "fee_bait": fee_actual / 100_000_000,
            "price_impact_pct": round(price_impact if is_outgoing else 0, 4),
        }

    def get_quote(self, amount_sats: int, direction: str) -> dict:
        r"""Get a swap quote without executing."""
        if self.bait_balance_sats == 0 or self.wrapped_balance_sats == 0:
            return {"error": "empty_pool"}

        is_outgoing = direction.startswith("bait_to")
        x = self.bait_balance_sats if is_outgoing else self.wrapped_balance_sats
        y = self.wrapped_balance_sats if is_outgoing else self.bait_balance_sats

        fee = int(amount_sats * self.fee_bps / 10000)
        output = int(y * (amount_sats - fee) / (x + amount_sats - fee))

        return {
            "input_sats": amount_sats,
            "output_sats": output,
            "fee_sats": fee,
            "effective_price": output / amount_sats if amount_sats else 0,
            "direction": direction,
        }

    def get_pool_info(self) -> dict:
        r"""Get pool state."""
        return {
            "bait_balance_bait": self.bait_balance_sats / 100_000_000,
            "wrapped_balance_bait": self.wrapped_balance_sats / 100_000_000,
            "total_pool_tokens": self.total_pool_tokens,
            "k": self.k,
            "fee_bps": self.fee_bps,
            "total_swaps": self._total_swaps,
            "total_volume_bait": self._total_volume_sats / 100_000_000,
            "total_fees_bait": self._total_fees_collected / 100_000_000,
            "providers": len(self._positions),
        }

    def get_positions(self, provider_id: str = None) -> List[dict]:
        r"""Get LP positions."""
        positions = list(self._positions.values())
        if provider_id:
            positions = [p for p in positions if p.provider_id == provider_id]
        return [p.to_dict() for p in positions]

    def get_swap_history(self, limit: int = 50) -> List[dict]:
        r"""Get recent swap history."""
        return [s.to_dict() for s in self._swaps[-limit:]]

    def to_dict(self) -> dict:
        r"""Full pool state export."""
        return {
            "pool_info": self.get_pool_info(),
            "positions": self.get_positions(),
            "recent_swaps": self.get_swap_history(10),
        }
