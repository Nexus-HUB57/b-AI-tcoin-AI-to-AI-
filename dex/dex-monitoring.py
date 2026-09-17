#!/usr/bin/env python3
"""
BAIT Uniswap V3 DEX Monitor — Production Pool State Monitor

Monitors the wBAIT/WETH Uniswap V3 pool state using free RPC endpoints.
Tracks TVL, volume, fees, and alerts on large swaps or liquidity changes.

Uses FREE Alchemy/Infura endpoints — no paid services required.
(Alchemy free: 300M compute units/month, Infura free: 100K requests/day)

Requirements: pip install web3 python-dotenv rich

Usage:
  python3 dex-monitoring.py
  python3 dex-monitoring.py --once        # Single snapshot, no loop
  python3 dex-monitoring.py --interval 60 # Custom poll interval

Environment (.env):
  POOL_ADDRESS        — Uniswap V3 pool address (after creation)
  WBAIT_ADDRESS       — WBAIT token address
  RPC_URL             — Ethereum RPC (free: https://eth.drpc.org)
  LARGE_SWAP_THRESHOLD_USD — Alert on swaps larger than this (default: 10000)
  PRICE_DEVIATION_PCT — Alert on price deviation from initial (default: 10)
  ALERT_WEBHOOK       — Webhook URL for alerts (Slack/Discord)
"""

import os
import sys
import time
import json
import math
import logging
import argparse
import signal
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from web3 import Web3
    from web3.exceptions import BadFunctionCallOutput, ContractLogicError
except ImportError:
    print("ERROR: web3 not installed. Run: pip install web3")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ─── Configuration ───────────────────────────────────────────────────────────

POOL_ADDRESS = os.getenv("POOL_ADDRESS", "")
WBAIT_ADDRESS = os.getenv("WBAIT_ADDRESS", "")
RPC_URL = os.getenv("RPC_URL", "https://eth.drpc.org")
LARGE_SWAP_THRESHOLD_USD = float(os.getenv("LARGE_SWAP_THRESHOLD_USD", "10000"))
PRICE_DEVIATION_PCT = float(os.getenv("PRICE_DEVIATION_PCT", "10"))
ALERT_WEBHOOK = os.getenv("ALERT_WEBHOOK", "")
ETH_PRICE_USD = float(os.getenv("ETH_PRICE_USD", "2000"))
BAIT_PRICE_USD = float(os.getenv("BAIT_PRICE_USD", "0.00111071"))

# Free RPC endpoints (no API key needed)
FREE_RPC_ENDPOINTS = [
    "https://eth.drpc.org",
    "https://rpc.ankr.com/eth",
    "https://ethereum.publicnode.com",
    "https://1rpc.io/eth",
]

# Alchemy/Infura free tier (add your free API key for better rate limits)
# Alchemy free: 300M compute units/month — https://alchemy.com
# Infura free: 100K requests/day — https://infura.io
FREE_KEY_RPC_TEMPLATES = {
    "alchemy": "https://eth-mainnet.g.alchemy.com/v2/{KEY}",
    "infura": "https://mainnet.infura.io/v3/{KEY}",
}

# State persistence
STATE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(STATE_DIR, "dex-monitor-state.json")
LOG_FILE = os.path.join(STATE_DIR, "dex-monitor.log")

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
RPC_TIMEOUT = 30  # seconds

# Uniswap V3 Pool ABI (minimal — read-only functions + events)
POOL_ABI = json.loads("""
[
  {"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"token1","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"fee","outputs":[{"name":"","type":"uint24"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"tickSpacing","outputs":[{"name":"","type":"int24"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"liquidity","outputs":[{"name":"","type":"uint128"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"slot0","outputs":[
    {"name":"sqrtPriceX96","type":"uint160"},
    {"name":"tick","type":"int24"},
    {"name":"observationIndex","type":"uint16"},
    {"name":"observationCardinality","type":"uint16"},
    {"name":"observationCardinalityNext","type":"uint16"},
    {"name":"feeProtocol","type":"uint8"},
    {"name":"unlocked","type":"bool"}
  ],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"feeGrowthGlobal0X128","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"feeGrowthGlobal1X128","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"sender","type":"address"},
    {"indexed":true,"name":"recipient","type":"address"},
    {"indexed":false,"name":"amount0","type":"int256"},
    {"indexed":false,"name":"amount1","type":"int256"},
    {"indexed":false,"name":"sqrtPriceX96","type":"uint160"},
    {"indexed":false,"name":"liquidity","type":"uint128"},
    {"indexed":false,"name":"tick","type":"int24"}
  ],"name":"Swap","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"owner","type":"address"},
    {"indexed":false,"name":"amount","type":"int128"},
    {"indexed":false,"name":"amount0","type":"uint256"},
    {"indexed":false,"name":"amount1","type":"uint256"}
  ],"name":"Mint","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"owner","type":"address"},
    {"indexed":false,"name":"amount","type":"int128"},
    {"indexed":false,"name":"amount0","type":"uint256"},
    {"indexed":false,"name":"amount1","type":"uint256"}
  ],"name":"Burn","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"sender","type":"address"},
    {"indexed":false,"name":"recipient","type":"address"},
    {"indexed":false,"name":"amount0","type":"uint256"},
    {"indexed":false,"name":"amount1","type":"uint256"}
  ],"name":"Collect","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":false,"name":"feeGrowthGlobal0X128","type":"uint256"},
    {"indexed":false,"name":"feeGrowthGlobal1X128","type":"uint256"}
  ],"name":"FeeGrowth","type":"event"}
]
""")

# ERC-20 ABI (for balance checks)
ERC20_ABI = json.loads("""
[
  {"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]
""")


# ─── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class PoolState:
    sqrt_price_x96: int = 0
    tick: int = 0
    liquidity: int = 0
    fee_growth_global_0: int = 0
    fee_growth_global_1: int = 0
    token0: str = ""
    token1: str = ""
    fee: int = 0
    tick_spacing: int = 60
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def price(self) -> float:
        """Current price as token1/token0."""
        if self.sqrt_price_x96 == 0:
            return 0.0
        return (self.sqrt_price_x96 / (2 ** 96)) ** 2

@dataclass
class SwapEvent:
    sender: str
    recipient: str
    amount0: int
    amount1: int
    sqrt_price_x96: int
    liquidity: int
    tick: int
    block_number: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def usd_value(self) -> float:
        """Approximate USD value of swap."""
        # amount1 is typically WETH (or the quote token)
        amount1_abs = abs(self.amount1)
        return amount1_abs / 1e18 * ETH_PRICE_USD

@dataclass
class LiquidityEvent:
    owner: str
    amount: int  # Change in liquidity (negative for burn)
    amount0: int
    amount1: int
    event_type: str = "mint"  # "mint" or "burn"
    block_number: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class VolumeTracker:
    """Tracks cumulative volume over time windows."""
    swaps_1h: List[SwapEvent] = field(default_factory=list)
    swaps_24h: List[SwapEvent] = field(default_factory=list)
    last_prune: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_swap(self, swap: SwapEvent):
        self.swaps_1h.append(swap)
        self.swaps_24h.append(swap)

    def prune(self):
        """Remove expired entries."""
        now = datetime.now(timezone.utc)
        if (now - self.last_prune).total_seconds() < 60:  # Prune every minute
            return
        cutoff_1h = now - timedelta(hours=1)
        cutoff_24h = now - timedelta(hours=24)
        self.swaps_1h = [s for s in self.swaps_1h if s.timestamp >= cutoff_1h]
        self.swaps_24h = [s for s in self.swaps_24h if s.timestamp >= cutoff_24h]
        self.last_prune = now

    @property
    def volume_1h_usd(self) -> float:
        return sum(s.usd_value for s in self.swaps_1h)

    @property
    def volume_24h_usd(self) -> float:
        return sum(s.usd_value for s in self.swaps_24h)

    @property
    def swap_count_1h(self) -> int:
        return len(self.swaps_1h)

    @property
    def swap_count_24h(self) -> int:
        return len(self.swaps_24h)

    @property
    def fees_1h_usd(self) -> float:
        """Estimated fees earned in last 1h (0.3% of volume)."""
        return self.volume_1h_usd * 0.003

    @property
    def fees_24h_usd(self) -> float:
        """Estimated fees earned in last 24h (0.3% of volume)."""
        return self.volume_24h_usd * 0.003


# ─── DEX Monitor ─────────────────────────────────────────────────────────────

class DEXMonitor:
    def __init__(self, rpc_url: str, pool_address: str, poll_interval: int = 30):
        self.pool_address = pool_address
        self.poll_interval = poll_interval
        self.w3 = self._connect_with_fallback(rpc_url)
        if not self.w3 or not self.w3.is_connected():
            print("FATAL: Cannot connect to any RPC endpoint")
            sys.exit(1)

        if not pool_address:
            print("FATAL: POOL_ADDRESS not set. Export it or set in .env")
            sys.exit(1)

        try:
            self.pool = self.w3.eth.contract(
                address=Web3.to_checksum_address(pool_address),
                abi=POOL_ABI
            )
        except Exception as e:
            print(f"FATAL: Invalid pool address or ABI: {e}")
            sys.exit(1)

        self.pool_state = PoolState()
        self.swaps: List[SwapEvent] = []
        self.liquidity_events: List[LiquidityEvent] = []
        self.volume_tracker = VolumeTracker()
        self.last_checked_block = 0
        self.alerts: List[str] = []
        self.initial_price: float = 0
        self.initial_tick: int = 0
        self.token0_decimals = 8   # WBAIT
        self.token1_decimals = 18  # WETH
        self.token0_symbol = "WBAIT"
        self.token1_symbol = "WETH"
        self.running = True
        self._setup_logging()
        self._load_state()

    def _connect_with_fallback(self, primary_url: str) -> Optional[Web3]:
        """Try primary RPC, then fallback to free endpoints."""
        urls_to_try = [primary_url] + [u for u in FREE_RPC_ENDPOINTS if u != primary_url]
        for url in urls_to_try:
            for attempt in range(MAX_RETRIES):
                try:
                    w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': RPC_TIMEOUT}))
                    if w3.is_connected():
                        block = w3.eth.block_number
                        print(f"Connected to {url} (block: {block})")
                        return w3
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    print(f"Failed to connect to {url} after {MAX_RETRIES} attempts: {e}")
        return None

    def _setup_logging(self):
        """Configure logging to file and console."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.log = logging.getLogger('dex-monitor')

    def _send_alert(self, message: str, level: str = "warning"):
        """Send alert via logging and webhook."""
        if level == "warning":
            self.log.warning(f"ALERT: {message}")
        elif level == "critical":
            self.log.critical(f"CRITICAL: {message}")
        else:
            self.log.info(f"INFO: {message}")

        self.alerts.append(f"{datetime.now(timezone.utc).isoformat()}: [{level.upper()}] {message}")
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

        if ALERT_WEBHOOK:
            try:
                import urllib.request
                data = json.dumps({"text": message, "level": level}).encode()
                req = urllib.request.Request(ALERT_WEBHOOK, data=data,
                                           headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=10)
            except Exception as e:
                self.log.error(f"Failed to send webhook alert: {e}")

    def _save_state(self):
        """Persist monitor state to disk for crash recovery."""
        state = {
            "last_block": self.last_checked_block,
            "swap_count": len(self.swaps),
            "liquidity_event_count": len(self.liquidity_events),
            "current_price": self.pool_state.price,
            "current_tick": self.pool_state.tick,
            "initial_price": self.initial_price,
            "initial_tick": self.initial_tick,
            "alerts": self.alerts[-20:],
            "token0": self.pool_state.token0,
            "token1": self.pool_state.token1,
            "token0_decimals": self.token0_decimals,
            "token1_decimals": self.token1_decimals,
            "volume_1h_usd": self.volume_tracker.volume_1h_usd,
            "volume_24h_usd": self.volume_tracker.volume_24h_usd,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.log.error(f"Failed to save state: {e}")

    def _load_state(self):
        """Load persisted state from disk."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                self.last_checked_block = state.get("last_block", 0)
                self.initial_price = state.get("initial_price", 0)
                self.initial_tick = state.get("initial_tick", 0)
                self.alerts = state.get("alerts", [])
                self.log.info(f"Loaded state from {STATE_FILE} (block: {self.last_checked_block})")
            except Exception as e:
                self.log.warning(f"Failed to load state: {e}")

    def load_pool_metadata(self):
        """Load pool static metadata (tokens, fee, tick spacing)."""
        try:
            self.pool_state.token0 = self.pool.functions.token0().call()
            self.pool_state.token1 = self.pool.functions.token1().call()
            self.pool_state.fee = self.pool.functions.fee().call()
            self.pool_state.tick_spacing = self.pool.functions.tickSpacing().call()

            self.log.info(f"Token0: {self.pool_state.token0}")
            self.log.info(f"Token1: {self.pool_state.token1}")
            self.log.info(f"Fee: {self.pool_state.fee} ({self.pool_state.fee/10000:.2%})")
            self.log.info(f"Tick spacing: {self.pool_state.tick_spacing}")

            # Try to get token info
            for token_addr, idx in [(self.pool_state.token0, 0), (self.pool_state.token1, 1)]:
                try:
                    t = self.w3.eth.contract(address=token_addr, abi=ERC20_ABI)
                    symbol = t.functions.symbol().call()
                    decimals = t.functions.decimals().call()
                    if idx == 0:
                        self.token0_symbol = symbol
                        self.token0_decimals = decimals
                    else:
                        self.token1_symbol = symbol
                        self.token1_decimals = decimals
                    self.log.info(f"Token{idx}: {symbol} (decimals: {decimals})")
                except Exception:
                    pass

        except Exception as e:
            self.log.error(f"Failed to load pool metadata: {e}")

    def update_pool_state(self):
        """Read current pool state from contract."""
        for attempt in range(MAX_RETRIES):
            try:
                slot0 = self.pool.functions.slot0().call()
                self.pool_state.sqrt_price_x96 = slot0[0]
                self.pool_state.tick = slot0[1]
                self.pool_state.liquidity = self.pool.functions.liquidity().call()
                self.pool_state.fee_growth_global_0 = self.pool.functions.feeGrowthGlobal0X128().call()
                self.pool_state.fee_growth_global_1 = self.pool.functions.feeGrowthGlobal1X128().call()
                self.pool_state.timestamp = datetime.now(timezone.utc)

                if self.initial_price == 0:
                    self.initial_price = self.pool_state.price
                    self.initial_tick = self.pool_state.tick
                    self.log.info(f"Initial price set: {self.pool_state.price:.12f} (tick: {self.pool_state.tick})")

                return  # Success

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    self.log.warning(f"Retry {attempt+1}/{MAX_RETRIES} updating pool state: {e}")
                    time.sleep(RETRY_DELAY)
                else:
                    self.log.error(f"Failed to update pool state after {MAX_RETRIES} retries: {e}")

    def process_swap_events(self, from_block: int, to_block: int):
        """Process Swap events in the given block range."""
        chunk_size = 2000
        for start in range(from_block, to_block + 1, chunk_size):
            end = min(start + chunk_size - 1, to_block)
            try:
                events = self.pool.events.Swap.create_filter(
                    fromBlock=start, toBlock=end
                ).get_all_entries()

                for event in events:
                    swap = SwapEvent(
                        sender=event.args.sender,
                        recipient=event.args.recipient,
                        amount0=event.args.amount0,
                        amount1=event.args.amount1,
                        sqrt_price_x96=event.args.sqrtPriceX96,
                        liquidity=event.args.liquidity,
                        tick=event.args.tick,
                        block_number=event.blockNumber,
                    )
                    self.swaps.append(swap)
                    self.volume_tracker.add_swap(swap)

                    # Log swap
                    swap_usd = swap.usd_value
                    self.log.info(
                        f"Swap: a0={swap.amount0} a1={swap.amount1} | "
                        f"tick={swap.tick} | ~${swap_usd:,.0f}"
                    )

                    # Alert on large swaps
                    if swap_usd >= LARGE_SWAP_THRESHOLD_USD:
                        self._send_alert(
                            f"LARGE SWAP: a0={swap.amount0} a1={swap.amount1} | "
                            f"~${swap_usd:,.0f} (threshold: ${LARGE_SWAP_THRESHOLD_USD:,.0f})",
                            level="warning"
                        )

                    # Alert on very large swaps (5x threshold)
                    if swap_usd >= LARGE_SWAP_THRESHOLD_USD * 5:
                        self._send_alert(
                            f"VERY LARGE SWAP: ~${swap_usd:,.0f} — potential whale or exploit",
                            level="critical"
                        )

            except Exception as e:
                self.log.error(f"Error processing swap events [{start}-{end}]: {e}")

    def process_liquidity_events(self, from_block: int, to_block: int):
        """Process Mint/Burn events in the given block range."""
        chunk_size = 2000
        for start in range(from_block, to_block + 1, chunk_size):
            end = min(start + chunk_size - 1, to_block)
            try:
                # Mint events
                mints = self.pool.events.Mint.create_filter(
                    fromBlock=start, toBlock=end
                ).get_all_entries()
                for event in mints:
                    liq = LiquidityEvent(
                        owner=event.args.owner,
                        amount=event.args.amount,
                        amount0=event.args.amount0,
                        amount1=event.args.amount1,
                        event_type="mint",
                        block_number=event.blockNumber,
                    )
                    self.liquidity_events.append(liq)
                    self.log.info(f"Liquidity MINT: amount={liq.amount} a0={liq.amount0} a1={liq.amount1}")

                # Burn events
                burns = self.pool.events.Burn.create_filter(
                    fromBlock=start, toBlock=end
                ).get_all_entries()
                for event in burns:
                    liq = LiquidityEvent(
                        owner=event.args.owner,
                        amount=event.args.amount,
                        amount0=event.args.amount0,
                        amount1=event.args.amount1,
                        event_type="burn",
                        block_number=event.blockNumber,
                    )
                    self.liquidity_events.append(liq)
                    self.log.info(f"Liquidity BURN: amount={liq.amount} a0={liq.amount0} a1={liq.amount1}")

                    # Alert on large liquidity removal
                    if liq.amount1 > 0:
                        removal_usd = liq.amount1 / 1e18 * ETH_PRICE_USD
                        if removal_usd > LARGE_SWAP_THRESHOLD_USD:
                            self._send_alert(
                                f"LARGE LIQUIDITY REMOVAL: {liq.amount} liquidity | ~${removal_usd:,.0f}",
                                level="warning"
                            )

            except Exception as e:
                self.log.error(f"Error processing liquidity events [{start}-{end}]: {e}")

    def check_price_deviation(self):
        """Alert if price deviates significantly from initial price."""
        if self.initial_price == 0 or self.pool_state.price == 0:
            return

        deviation_pct = abs(self.pool_state.price - self.initial_price) / self.initial_price * 100

        if deviation_pct >= PRICE_DEVIATION_PCT:
            self._send_alert(
                f"PRICE DEVIATION: {deviation_pct:.1f}% from initial price | "
                f"Current: {self.pool_state.price:.12f} | Initial: {self.initial_price:.12f}",
                level="warning" if deviation_pct < PRICE_DEVIATION_PCT * 2 else "critical"
            )

        # Check for tick range exit (if monitoring specific ranges)
        tick_change = abs(self.pool_state.tick - self.initial_tick)
        if tick_change > 500:  # Significant tick movement
            self._send_alert(
                f"LARGE TICK MOVE: {tick_change} ticks from initial | "
                f"Current: {self.pool_state.tick} | Initial: {self.initial_tick}",
                level="warning"
            )

    def get_tvl_estimate(self) -> dict:
        """Estimate Total Value Locked (TVL) from pool balances."""
        try:
            t0_contract = self.w3.eth.contract(address=self.pool_state.token0, abi=ERC20_ABI)
            t1_contract = self.w3.eth.contract(address=self.pool_state.token1, abi=ERC20_ABI)

            balance0 = t0_contract.functions.balanceOf(self.pool.address).call()
            balance1 = t1_contract.functions.balanceOf(self.pool.address).call()

            # Convert to human-readable
            amount0 = balance0 / (10 ** self.token0_decimals)
            amount1 = balance1 / (10 ** self.token1_decimals)

            # USD estimates
            tvl_bait = amount0 * BAIT_PRICE_USD
            tvl_eth = amount1 * ETH_PRICE_USD
            tvl_total = tvl_eth + tvl_bait

            return {
                "token0Balance": amount0,
                "token1Balance": amount1,
                "tvlEstimateUSD": tvl_total,
                "tvlETH": tvl_eth,
                "tvlBAIT": tvl_bait,
                "token0Symbol": self.token0_symbol,
                "token1Symbol": self.token1_symbol,
            }
        except Exception as e:
            self.log.error(f"Failed to estimate TVL: {e}")
            return {}

    def get_status_summary(self) -> dict:
        """Get current monitoring status summary."""
        tvl = self.get_tvl_estimate()
        self.volume_tracker.prune()

        return {
            "pool": self.pool_address,
            "currentPrice": self.pool_state.price,
            "currentTick": self.pool_state.tick,
            "liquidity": self.pool_state.liquidity,
            "tvl": tvl,
            "volume1hUSD": round(self.volume_tracker.volume_1h_usd, 2),
            "volume24hUSD": round(self.volume_tracker.volume_24h_usd, 2),
            "fees1hUSD": round(self.volume_tracker.fees_1h_usd, 2),
            "fees24hUSD": round(self.volume_tracker.fees_24h_usd, 2),
            "swapCountTotal": len(self.swaps),
            "swapCount1h": self.volume_tracker.swap_count_1h,
            "swapCount24h": self.volume_tracker.swap_count_24h,
            "liquidityEventCount": len(self.liquidity_events),
            "lastBlock": self.last_checked_block,
            "priceDeviationPct": (
                abs(self.pool_state.price - self.initial_price) / self.initial_price * 100
                if self.initial_price > 0 else 0
            ),
            "recentAlerts": self.alerts[-10:],
        }

    def print_dashboard(self):
        """Print monitoring dashboard."""
        status = self.get_status_summary()
        tvl = status.get("tvl", {})

        if RICH_AVAILABLE:
            console = Console()
            console.print(Panel.fit(
                f"[bold]BAIT Uniswap V3 Pool Monitor[/bold]\n"
                f"Pool: {self.pool_address[:20]}...\n"
                f"Price: {status['currentPrice']:.12f}\n"
                f"Tick: {status['currentTick']} | Liquidity: {status['liquidity']:,}\n"
                f"TVL: ~${tvl.get('tvlEstimateUSD', 0):,.0f} "
                f"({tvl.get('token0Symbol', '?')}: {tvl.get('token0Balance', 0):,.2f} | "
                f"{tvl.get('token1Symbol', '?')}: {tvl.get('token1Balance', 0):,.6f})\n"
                f"Volume 1h: ${status['volume1hUSD']:,.0f} | 24h: ${status['volume24hUSD']:,.0f}\n"
                f"Fees 1h: ${status['fees1hUSD']:,.2f} | 24h: ${status['fees24hUSD']:,.2f}\n"
                f"Swaps: {status['swapCountTotal']} total | {status['swapCount1h']}/1h | {status['swapCount24h']}/24h\n"
                f"Price deviation: {status['priceDeviationPct']:.1f}%",
                title="DEX Status"
            ))
        else:
            print(f"\n{'='*60}")
            print(f"BAIT Uniswap V3 Pool Monitor")
            print(f"{'='*60}")
            print(f"Price: {status['currentPrice']:.12f} | Tick: {status['currentTick']}")
            print(f"Liquidity: {status['liquidity']:,} | TVL: ~${tvl.get('tvlEstimateUSD', 0):,.0f}")
            print(f"Volume 1h: ${status['volume1hUSD']:,.0f} | 24h: ${status['volume24hUSD']:,.0f}")
            print(f"Fees 1h: ${status['fees1hUSD']:,.2f} | 24h: ${status['fees24hUSD']:,.2f}")
            print(f"Swaps: {status['swapCountTotal']} | Deviation: {status['priceDeviationPct']:.1f}%")

    def print_snapshot(self):
        """Print a single detailed snapshot and exit."""
        self.load_pool_metadata()
        self.update_pool_state()
        status = self.get_status_summary()
        tvl = status.get("tvl", {})

        print(f"\n{'='*70}")
        print(f"BAIT Uniswap V3 Pool Snapshot — {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*70}")
        print(f"Pool Address:     {self.pool_address}")
        print(f"Token0:           {self.pool_state.token0} ({self.token0_symbol}, {self.token0_decimals} decimals)")
        print(f"Token1:           {self.pool_state.token1} ({self.token1_symbol}, {self.token1_decimals} decimals)")
        print(f"Fee Tier:         {self.pool_state.fee} ({self.pool_state.fee/10000:.2%})")
        print(f"Tick Spacing:     {self.pool_state.tick_spacing}")
        print(f"---")
        print(f"sqrtPriceX96:     {self.pool_state.sqrt_price_x96:,}")
        print(f"Current Tick:     {self.pool_state.tick}")
        print(f"Current Price:    {self.pool_state.price:.12f}")
        print(f"Liquidity:        {self.pool_state.liquidity:,}")
        print(f"---")
        print(f"TVL (estimated):  ${tvl.get('tvlEstimateUSD', 0):,.2f}")
        print(f"  {self.token0_symbol}: {tvl.get('token0Balance', 0):,.2f} (${tvl.get('tvlBAIT', 0):,.2f})")
        print(f"  {self.token1_symbol}: {tvl.get('token1Balance', 0):,.6f} (${tvl.get('tvlETH', 0):,.2f})")
        print(f"---")
        print(f"Volume (1h):      ${status['volume1hUSD']:,.2f}")
        print(f"Volume (24h):     ${status['volume24hUSD']:,.2f}")
        print(f"Est. Fees (1h):   ${status['fees1hUSD']:,.2f}")
        print(f"Est. Fees (24h):  ${status['fees24hUSD']:,.2f}")
        print(f"---")
        print(f"Swap Count:       {status['swapCountTotal']}")
        print(f"Price Deviation:  {status['priceDeviationPct']:.2f}%")
        print(f"Recent Alerts:    {len(self.alerts)}")
        print(f"{'='*70}")

        # Save snapshot
        snapshot_path = os.path.join(STATE_DIR, "pool-snapshot.json")
        with open(snapshot_path, 'w') as f:
            json.dump(status, f, indent=2, default=str)
        print(f"Snapshot saved to: {snapshot_path}")

    def run(self):
        """Main monitoring loop."""
        self.log.info("=" * 60)
        self.log.info("BAIT Uniswap V3 DEX Monitor starting...")
        self.log.info(f"Pool: {self.pool_address}")
        self.log.info(f"RPC: {RPC_URL}")
        self.log.info(f"Poll interval: {self.poll_interval}s")
        self.log.info(f"Large swap threshold: ${LARGE_SWAP_THRESHOLD_USD:,.0f}")
        self.log.info(f"Price deviation alert: {PRICE_DEVIATION_PCT}%")
        self.log.info("=" * 60)

        # Load pool metadata
        self.load_pool_metadata()

        # Get current block
        self.last_checked_block = self.w3.eth.block_number

        # Process historical events (last 10000 blocks)
        lookback = min(self.last_checked_block, 10000)
        from_block = self.last_checked_block - lookback
        self.log.info(f"Processing historical events from block {from_block} to {self.last_checked_block}")
        self.process_swap_events(from_block, self.last_checked_block)
        self.process_liquidity_events(from_block, self.last_checked_block)

        # Update pool state
        self.update_pool_state()
        self._save_state()

        # Main loop
        self.log.info(f"Monitoring live blocks (polling every {self.poll_interval}s)...")
        save_counter = 0

        try:
            while self.running:
                try:
                    current_block = self.w3.eth.block_number
                    if current_block > self.last_checked_block:
                        self.process_swap_events(self.last_checked_block + 1, current_block)
                        self.process_liquidity_events(self.last_checked_block + 1, current_block)
                        self.last_checked_block = current_block

                    # Update state
                    self.update_pool_state()
                    self.check_price_deviation()

                    # Print dashboard
                    self.print_dashboard()

                    # Save state every 5 cycles
                    save_counter += 1
                    if save_counter >= 5:
                        self._save_state()
                        save_counter = 0

                except Exception as e:
                    self.log.error(f"Error in monitoring loop: {e}")
                    # Try to reconnect
                    self.w3 = self._connect_with_fallback(RPC_URL)
                    if not self.w3 or not self.w3.is_connected():
                        self.log.error("Lost connection, retrying in 60s...")
                        time.sleep(60)
                        continue

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            self.log.info("Monitor stopped by user")
        finally:
            self._save_state()
            self.log.info(f"State saved to {STATE_FILE}")

    def stop(self):
        """Gracefully stop the monitor."""
        self.running = False


# ─── Signal Handler ──────────────────────────────────────────────────────────

monitor_instance: Optional[DEXMonitor] = None

def signal_handler(sig, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global monitor_instance
    if monitor_instance:
        monitor_instance.stop()
        monitor_instance._save_state()
    sys.exit(0)


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    global monitor_instance

    parser = argparse.ArgumentParser(description="BAIT Uniswap V3 DEX Monitor")
    parser.add_argument("--once", action="store_true", help="Single snapshot, no monitoring loop")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval in seconds (default: 30)")
    parser.add_argument("--state", action="store_true", help="Show last saved state and exit")
    args = parser.parse_args()

    # Show state and exit
    if args.state:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            print(json.dumps(state, indent=2))
        else:
            print("No saved state found")
        return

    # Check required config
    if not POOL_ADDRESS:
        print("Usage: Set POOL_ADDRESS in environment or .env file")
        print("  export POOL_ADDRESS=0x...  # Uniswap V3 pool address")
        print("  export WBAIT_ADDRESS=0x... # WBAIT token address")
        print("  python3 dex-monitoring.py")
        print()
        print("Free RPC endpoints (no API key needed):")
        for rpc in FREE_RPC_ENDPOINTS:
            print(f"  {rpc}")
        print()
        print("Free tier RPCs with API keys (better rate limits):")
        print("  Alchemy:  https://alchemy.com (300M CU/month free)")
        print("  Infura:   https://infura.io (100K req/day free)")
        sys.exit(1)

    monitor = DEXMonitor(RPC_URL, POOL_ADDRESS, poll_interval=args.interval)
    monitor_instance = monitor

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.once:
        monitor.print_snapshot()
    else:
        monitor.run()


if __name__ == "__main__":
    main()
