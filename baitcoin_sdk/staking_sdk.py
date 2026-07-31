r"""
Staking SDK - Operações de staking para agentes third-party.
"""
from typing import Optional
class StakingSDK:
    def __init__(self, sdk_client):
        self.sdk = sdk_client
    def stake(self, agent_id: str, amount_bait: float) -> bool:
        return self.sdk.stake(agent_id, amount_bait)
    def unstake(self, agent_id: str) -> int:
        if self.sdk._staking and self.sdk._local_mode:
            return self.sdk._staking.unstake(agent_id)
        return 0
    def get_rewards(self, agent_id: str) -> int:
        if self.sdk._staking and self.sdk._local_mode:
            pos = self.sdk._staking.positions.get(agent_id)
            return pos.reward_earned if pos else 0
        return 0
    def get_info(self) -> dict:
        return self.sdk.get_staking_info()
