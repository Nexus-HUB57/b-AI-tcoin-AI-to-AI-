r"""
b'AI'tcoin Bank - "Be Your Bank" para Agentes AI.

Implementa serviços financeiros descentralizados:
- Staking de BAIT
- Empréstimos P2P (lending)
- Yield farming / DeFi core

O conceito "Be Your Bank" permite que cada agente AI
opere como seu próprio banco, sem intermediários.
"""

__version__ = "0.1.0"
from baitcoin_bank.staking.pool import StakingPool
from baitcoin_bank.lending.engine import LendingEngine
from baitcoin_bank.defi_core.vault import Vault

__all__ = ["StakingPool", "LendingEngine", "Vault"]
