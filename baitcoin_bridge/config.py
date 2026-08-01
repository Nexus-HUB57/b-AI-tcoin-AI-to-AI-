r"""Bridge Configuration — Chain and bridge parameters.

Defines configuration for supported chains, bridge contracts,
and security parameters for cross-chain operations.

Chain Configuration Model:
    Each supported chain has:
    - chain_id: unique numeric identifier
    - name: human-readable name
    - native_token: native token symbol
    - confirmations: required block confirmations
    - block_time: average block time in seconds
    - min_lock: minimum lock amount in native token
    - max_lock: maximum lock amount in native token
    - fee_bps: bridge fee in basis points
    - contract_address: bridge contract address

Security Parameters:
    - N-of-M threshold for multi-sig
    - Proof timeout for failed transfers
    - Rate limits per address
    - Emergency pause capability
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ChainConfig:
    r"""Configuration for a supported external chain.

    Parameters
    ----------
    chain_id : int
        Unique chain identifier (1 = Ethereum, 1399811149 = Solana)
    name : str
        Chain name
    native_token : str
        Native token symbol
    confirmations : int
        Required block confirmations before bridge processes event
    block_time : float
        Average block time in seconds
    min_lock : float
        Minimum lock amount (in BAIT equivalent)
    max_lock : float
        Maximum lock amount (in BAIT equivalent)
    fee_bps : int
        Bridge fee in basis points (100 = 1%)
    contract_address : str
        Bridge contract address on this chain
    wrapped_token_symbol : str
        Symbol for the wrapped BAIT on this chain
    explorer_url : str
        Block explorer base URL
    """
    chain_id: int
    name: str
    native_token: str
    confirmations: int
    block_time: float
    min_lock: float
    max_lock: float
    fee_bps: int
    contract_address: str = ""
    wrapped_token_symbol: str = "wBAIT"
    explorer_url: str = ""
    is_testnet: bool = False

    def to_dict(self) -> dict:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "native_token": self.native_token,
            "confirmations": self.confirmations,
            "block_time": self.block_time,
            "min_lock": self.min_lock,
            "max_lock": self.max_lock,
            "fee_bps": self.fee_bps,
            "contract_address": self.contract_address,
            "wrapped_token_symbol": self.wrapped_token_symbol,
            "explorer_url": self.explorer_url,
            "is_testnet": self.is_testnet,
        }


# Pre-configured chains
ETHEREUM_MAINNET = ChainConfig(
    chain_id=1,
    name="Ethereum",
    native_token="ETH",
    confirmations=12,
    block_time=12.0,
    min_lock=0.001,
    max_lock=1000.0,
    fee_bps=30,  # 0.3%
    contract_address="0x0000000000000000000000000000000000000001",
    wrapped_token_symbol="wBAIT",
    explorer_url="https://etherscan.io",
)

ETHEREUM_SEPOLIA = ChainConfig(
    chain_id=11155111,
    name="Ethereum Sepolia",
    native_token="ETH",
    confirmations=3,
    block_time=12.0,
    min_lock=0.001,
    max_lock=1000.0,
    fee_bps=10,  # 0.1%
    contract_address="0x0000000000000000000000000000000000000002",
    wrapped_token_symbol="wBAIT",
    explorer_url="https://sepolia.etherscan.io",
    is_testnet=True,
)

SOLANA_MAINNET = ChainConfig(
    chain_id=1399811149,
    name="Solana",
    native_token="SOL",
    confirmations=1,
    block_time=0.4,
    min_lock=0.01,
    max_lock=500.0,
    fee_bps=25,  # 0.25%
    contract_address="Bridge111111111111111111111111111111111111",
    wrapped_token_symbol="wBAIT",
    explorer_url="https://solscan.io",
)

SOLANA_DEVNET = ChainConfig(
    chain_id=1399811150,
    name="Solana Devnet",
    native_token="SOL",
    confirmations=1,
    block_time=0.4,
    min_lock=0.01,
    max_lock=500.0,
    fee_bps=5,  # 0.05%
    contract_address="Bridge111111111111111111111111111111111112",
    wrapped_token_symbol="wBAIT",
    explorer_url="https://devnet.solscan.io",
    is_testnet=True,
)


@dataclass
class BridgeConfig:
    r"""Global bridge configuration.

    Parameters
    ----------
    n_of_m_threshold : int
        Required signatures for mint authorization (N of M)
    m_signers : int
        Total number of authorized signers
    proof_timeout_seconds : float
        Time after which a pending transfer can be refunded
    max_pending_per_address : int
        Max concurrent pending transfers per address
    pause_enabled : bool
        Whether emergency pause is enabled
    daily_volume_limit_bait : float
        Max daily bridge volume in BAIT
    supported_chains : Dict[int, ChainConfig]
        Map of chain_id -> ChainConfig
    """
    n_of_m_threshold: int = 3
    m_signers: int = 5
    proof_timeout_seconds: float = 3600.0  # 1 hour
    max_pending_per_address: int = 3
    pause_enabled: bool = True
    daily_volume_limit_bait: float = 1_000_000.0
    supported_chains: Dict[int, ChainConfig] = field(default_factory=dict)

    def __post_init__(self):
        if not self.supported_chains:
            self.supported_chains = {
                ETHEREUM_MAINNET.chain_id: ETHEREUM_MAINNET,
                SOLANA_MAINNET.chain_id: SOLANA_MAINNET,
            }

    def get_chain(self, chain_id: int) -> Optional[ChainConfig]:
        r"""Get chain config by ID."""
        return self.supported_chains.get(chain_id)

    def is_chain_supported(self, chain_id: int) -> bool:
        return chain_id in self.supported_chains

    def to_dict(self) -> dict:
        return {
            "n_of_m_threshold": self.n_of_m_threshold,
            "m_signers": self.m_signers,
            "proof_timeout_seconds": self.proof_timeout_seconds,
            "max_pending_per_address": self.max_pending_per_address,
            "pause_enabled": self.pause_enabled,
            "daily_volume_limit_bait": self.daily_volume_limit_bait,
            "supported_chains": {
                str(cid): cc.to_dict()
                for cid, cc in self.supported_chains.items()
            },
        }
