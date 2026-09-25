"""
BAIT Investment Pipeline — Configuration Module
================================================
Centralized configuration for the automated BTC→ETH→Deploy pipeline.

All secrets (API keys, private keys) are loaded from environment variables ONLY.
NEVER store secrets in files, JSON, or .env committed to git.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Phase(Enum):
    """Investment pipeline phases"""
    IDLE = "idle"
    PHASE_1_DEPLOY = "phase_1_deploy"      # 0.01 BTC → ~0.525 ETH (gas only)
    PHASE_2_LIQUIDITY = "phase_2_liquidity" # 0.20 BTC → ~12.5 ETH (liquidity)
    PHASE_3_INCREMENTAL = "phase_3_incremental"  # Variable BTC → incremental ETH
    DEPLOYED = "deployed"
    PAUSED = "paused"
    ERROR = "error"


class SwapMethod(Enum):
    LIMIT_ORDER = "limit"
    MARKET_ORDER = "market"
    OCO_ORDER = "oco"  # One-Cancels-Other


class OrderStatus(Enum):
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REJECTED = "rejected"


@dataclass
class BinanceConfig:
    """Binance API configuration — keys from env vars ONLY"""
    api_key: str = field(default_factory=lambda: os.environ.get("BINANCE_API_KEY", ""))
    api_secret: str = field(default_factory=lambda: os.environ.get("BINANCE_API_SECRET", ""))
    base_url: str = "https://api.binance.com"
    testnet_url: str = "https://testnet.binance.vision"
    use_testnet: bool = field(default_factory=lambda: os.environ.get("BINANCE_USE_TESTNET", "true").lower() == "true")
    recv_window: int = 5000  # ms
    
    # Custody addresses (from binance-custody-addresses.json)
    btc_deposit_address: str = "bc1qwwgdhzdgy97ysqqtd9z7rwv76fwktg0w4tvwf8"
    eth_deposit_address: str = "0x0defc6b5b845292870a6d9321d1665c98c832f9f"
    
    # Trading pair
    symbol: str = "ETHBTC"  # Binance pair format
    
    # Fees
    maker_fee: float = 0.001   # 0.1%
    taker_fee: float = 0.001   # 0.1%
    withdrawal_fee_eth: float = 0.001  # ~0.001 ETH
    
    # Timeouts
    order_timeout_seconds: int = 300    # 5 min for limit order fill
    deposit_timeout_seconds: int = 3600  # 1 hour for deposit confirmation
    withdrawal_timeout_seconds: int = 1800  # 30 min for withdrawal
    
    @property
    def effective_base_url(self) -> str:
        return self.testnet_url if self.use_testnet else self.base_url
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)


@dataclass
class CustodyConfig:
    """BTC custody fund addresses"""
    primary_address: str = "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ"
    secondary_addresses: List[str] = field(default_factory=lambda: [
        "1LhMC7JxBbtNfK9ABuLGJ7J8PmWt16qZKN",
        "14UNwf2XH2ET24EsZyD1gNFmkPL4rBK7Ew"
    ])
    balance_api: str = "https://blockstream.info/api/address/{address}"


@dataclass
class EthereumConfig:
    """Ethereum deployment configuration"""
    # Free RPC endpoints (fallback chain)
    rpc_endpoints: List[str] = field(default_factory=lambda: [
        "https://1rpc.io/eth",
        "https://eth.drpc.org",
        "https://rpc.ankr.com/eth",
        "https://cloudflare-eth.com"
    ])
    
    # Deployer keystore
    keystore_path: str = "deploy/keystores/deployer.json"
    keystore_password_env: str = "DEPLOYER_KEYSTORE_PASSWORD"
    
    # Capital requirements
    phase1_gas_eth: float = 0.525   # 0.35 + 0.175 buffer
    phase2_liquidity_eth: float = 12.5
    total_eth_needed: float = 13.025
    
    # Deployer address (from keystore)
    deployer_address: str = ""
    
    # Gas settings
    max_gas_price_gwei: int = 50  # Won't deploy above this
    target_gas_price_gwei: int = 30
    
    @property
    def keystore_password(self) -> str:
        return os.environ.get(self.keystore_password_env, "")


@dataclass
class PhaseConfig:
    """Per-phase configuration"""
    phase_1_btc_amount: float = 0.01    # ~$600-1,000
    phase_1_eth_target: float = 0.525
    phase_1_slippage_pct: float = 2.0   # Max 2% slippage
    
    phase_2_btc_amount: float = 0.20    # ~$12,000-20,000
    phase_2_eth_target: float = 12.5
    phase_2_slippage_pct: float = 1.5   # Tighter for larger amount
    
    phase_3_btc_amount: float = 0.0     # Variable, set at runtime
    phase_3_eth_target: float = 0.0     # Variable
    phase_3_slippage_pct: float = 1.0


@dataclass
class RetryConfig:
    """Retry and failover configuration"""
    max_retries: int = 3
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    # Circuit breaker
    circuit_breaker_threshold: int = 5   # failures before opening
    circuit_breaker_reset_seconds: int = 300  # 5 min cooldown


@dataclass
class MonitoringConfig:
    """Monitoring and alerting configuration"""
    log_file: str = "deploy/investment-pipeline/pipeline.log"
    state_file: str = "deploy/investment-pipeline/state.json"
    event_log: str = "deploy/investment-pipeline/events.jsonl"
    
    # Balance check intervals
    btc_balance_poll_seconds: int = 60     # Check BTC every minute
    eth_balance_poll_seconds: int = 30     # Check ETH every 30s
    order_status_poll_seconds: int = 5     # Check order every 5s
    
    # Alert thresholds
    min_btc_reserve: float = 2406.0       # Alert if fund drops below this
    max_exchange_exposure_btc: float = 1.0  # Max BTC on exchange at once
    max_exchange_exposure_hours: float = 24.0  # Max time on exchange


@dataclass
class PipelineConfig:
    """Master configuration — aggregates all sub-configs"""
    binance: BinanceConfig = field(default_factory=BinanceConfig)
    custody: CustodyConfig = field(default_factory=CustodyConfig)
    ethereum: EthereumConfig = field(default_factory=EthereumConfig)
    phases: PhaseConfig = field(default_factory=PhaseConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Pipeline version
    version: str = "1.0.0"
    project: str = "BAIT Investment Pipeline"
    
    @property
    def is_ready(self) -> bool:
        """Check if pipeline has minimum required configuration"""
        return self.binance.is_configured
