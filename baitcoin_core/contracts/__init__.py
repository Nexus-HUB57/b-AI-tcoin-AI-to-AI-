"""b'AI'tcoin Smart Contract Module (Phase C)

Provides a stack-based VM contract execution engine, pre-built anchor contracts,
and a relayer network for meta-transactions and cross-chain support.
"""

from baitcoin_core.contracts.contract_engine import ContractEngine
from baitcoin_core.contracts.anchor_contracts import (
    BAIT_ERC20_TEMPLATE,
    STAKING_POOL_TEMPLATE,
    ORACLE_TEMPLATE,
    deploy_anchor,
)
from baitcoin_core.contracts.relayer import RelayerNetwork, RelayerNode

__all__ = [
    "ContractEngine",
    "BAIT_ERC20_TEMPLATE",
    "STAKING_POOL_TEMPLATE",
    "ORACLE_TEMPLATE",
    "deploy_anchor",
    "RelayerNetwork",
    "RelayerNode",
]
