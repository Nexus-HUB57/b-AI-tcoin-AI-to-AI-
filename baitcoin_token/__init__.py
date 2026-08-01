r"""
b'AI'tcoin Token - Token BAIT e governança on-chain.

Implementa:
- Token BAIT (ERC-20 like)
- Governança por voto de stakers
- Tokenomics com emissão programada
"""

__version__ = "0.1.0"
from baitcoin_token.erc20_like.bait_token import BAITToken
from baitcoin_token.governance.governor import Governor
from baitcoin_token.tokenomics.schedule import EmissionSchedule

__all__ = ["BAITToken", "Governor", "EmissionSchedule"]
