r"""MobileStaking — Staking operations for mobile SDK.

Provides staking operations optimized for mobile UX:
    - Stake BAIT with configurable lock periods
    - Unstake and claim rewards
    - View active positions with APY calculations
    - Staking calculator for projected returns

The mobile staking UX emphasizes clarity:
    - All amounts displayed in BAIT (not sats)
    - APY shown with projected earnings
    - Lock period shown in human-readable format
    - Reward estimates updated in real-time

Usage::

    sdk = BaitcoinMobileSDK()
    result = sdk.staking.stake("agent_1", 100.0, lock_days=30)
    positions = sdk.staking.get_positions("agent_1")
    estimate = sdk.staking.calculate_rewards(100.0, 365)
"""
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class MobileStakeInfo:
    r"""Mobile-optimized stake position display."""
    position_id: str
    agent_id: str
    amount_bait: float
    reward_earned_bait: float
    apy: float
    start_time: float
    lock_period_days: float
    unlock_time: float
    is_active: bool
    state: str

    def to_dict(self) -> dict:
        return {
            "position_id": self.position_id,
            "agent_id": self.agent_id,
            "amount_bait": round(self.amount_bait, 8),
            "reward_earned_bait": round(self.reward_earned_bait, 8),
            "apy": self.apy,
            "start_time": self.start_time,
            "lock_period_days": self.lock_period_days,
            "unlock_time": self.unlock_time,
            "is_active": self.is_active,
            "state": self.state,
            "days_remaining": max(0, (self.unlock_time - time.time()) / 86400),
        }


class MobileStaking:
    r"""Mobile staking operations."""

    DEFAULT_APY = 0.07  # 7%
    MIN_STAKE_BAIT = 100.0
    LOCK_PERIODS = {
        "flexible": 0,
        "30_days": 30,
        "90_days": 90,
        "180_days": 180,
        "365_days": 365,
    }

    def __init__(self, sdk: 'BaitcoinMobileSDK'):
        self._sdk = sdk
        self._local_positions: Dict[str, List[MobileStakeInfo]] = {}

    def stake(
        self,
        agent_id: str,
        amount_bait: float,
        lock_days: float = 0,
    ) -> dict:
        r"""Stake BAIT tokens.

        Parameters
        ----------
        agent_id : str
            Staking agent
        amount_bait : float
            Amount to stake in BAIT
        lock_days : float
            Lock period in days (0 = flexible)

        Returns
        -------
        dict
            Stake result with position details
        """
        if amount_bait < self.MIN_STAKE_BAIT:
            return {
                "success": False,
                "error": "below_minimum",
                "minimum_bait": self.MIN_STAKE_BAIT,
            }

        now = time.time()
        lock_seconds = lock_days * 86400
        position_id = f"stake_{agent_id}_{int(now)}"

        # Remote call (best-effort, don't fail on connection error)
        if not self._sdk._local_mode:
            self._sdk._request("POST", "/api/v1/staking/stake", {
                "agent_id": agent_id,
                "amount_bait": amount_bait,
                "lock_period": int(lock_seconds),
            })

        # Track locally for mobile display
        position = MobileStakeInfo(
            position_id=position_id,
            agent_id=agent_id,
            amount_bait=amount_bait,
            reward_earned_bait=0.0,
            apy=self.DEFAULT_APY,
            start_time=now,
            lock_period_days=lock_days,
            unlock_time=now + lock_seconds,
            is_active=True,
            state="active",
        )

        if agent_id not in self._local_positions:
            self._local_positions[agent_id] = []
        self._local_positions[agent_id].append(position)

        return {
            "success": True,
            "position": position.to_dict(),
        }

    def unstake(self, agent_id: str, position_id: str) -> dict:
        r"""Unstake from a position."""
        positions = self._local_positions.get(agent_id, [])
        for pos in positions:
            if pos.position_id == position_id:
                pos.is_active = False
                pos.state = "unstaking"

        if not self._sdk._local_mode:
            return self._sdk._request("POST", "/api/v1/staking/unstake", {
                "agent_id": agent_id,
                "position_id": position_id,
            })
        return {"success": True}

    def claim_rewards(self, agent_id: str) -> dict:
        r"""Claim staking rewards for all active positions."""
        total_rewards = 0.0
        for pos in self._local_positions.get(agent_id, []):
            if pos.is_active:
                total_rewards += pos.reward_earned_bait
                pos.reward_earned_bait = 0.0

        if not self._sdk._local_mode:
            return self._sdk._request("POST", "/api/v1/staking/claim", {
                "agent_id": agent_id,
            })
        return {
            "success": True,
            "rewards_bait": round(total_rewards, 8),
        }

    def get_positions(self, agent_id: str) -> List[dict]:
        r"""Get all staking positions for an agent."""
        positions = self._local_positions.get(agent_id, [])
        if not self._sdk._local_mode:
            resp = self._sdk._request(
                "GET", f"/api/v1/staking/positions/{agent_id}"
            )
            if not resp.get("error"):
                return resp.get("positions", [])
        return [p.to_dict() for p in positions]

    def calculate_rewards(
        self,
        amount_bait: float,
        days: int,
        apy: float = None,
    ) -> dict:
        r"""Calculate projected staking rewards.

        Simple compound interest model:
            rewards = amount * (1 + APY/365)^days - amount

        Parameters
        ----------
        amount_bait : float
            Staking amount
        days : int
            Staking duration in days
        apy : float
            Annual percentage yield (default 7%)

        Returns
        -------
        dict
            Projected rewards with daily breakdown
        """
        apy = apy or self.DEFAULT_APY
        daily_rate = apy / 365

        # Compound: final = P * (1 + r)^n
        final_amount = amount_bait * ((1 + daily_rate) ** days)
        rewards = final_amount - amount_bait

        # Monthly breakdown
        monthly = []
        for m in range(1, 13):
            d = min(m * 30, days)
            monthly_rewards = amount_bait * ((1 + daily_rate) ** d) - amount_bait
            monthly.append({
                "month": m,
                "days": d,
                "projected_rewards_bait": round(monthly_rewards, 8),
                "total_value_bait": round(amount_bait + monthly_rewards, 8),
            })

        return {
            "principal_bait": amount_bait,
            "apy": apy,
            "days": days,
            "projected_rewards_bait": round(rewards, 8),
            "final_value_bait": round(final_amount, 8),
            "daily_reward_bait": round(rewards / max(1, days), 8),
            "monthly_projection": monthly,
        }

    def get_staking_info(self) -> dict:
        r"""Get global staking information."""
        if not self._sdk._local_mode:
            resp = self._sdk._request("GET", "/api/v1/staking")
            if not resp.get("error"):
                return resp
        return {
            "apy": self.DEFAULT_APY,
            "min_stake_bait": self.MIN_STAKE_BAIT,
            "lock_periods": self.LOCK_PERIODS,
            "total_positions": sum(
                len(positions) for positions in self._local_positions.values()
            ),
        }
