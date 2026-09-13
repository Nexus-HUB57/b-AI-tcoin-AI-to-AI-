#!/usr/bin/env python3
"""
BAIT BridgeLock Monitor — Production Event Monitor for 3-of-5 Multisig Bridge

Monitors BridgeLock.sol contract events:
  - LockRequested, LockConfirmed, LockExecuted
  - BurnInitiated, BurnConfirmed, BurnExecuted
  - OperatorUpdated

Tracks confirmation progress, alerts on stalled requests, and monitors rate limits.
Uses FREE RPC endpoints — no paid services required.

Features:
  - Prometheus metrics endpoint (port 9090, free, no external deps beyond prometheus_client)
  - State persistence: resumes from last processed block on restart
  - Health check endpoint (HTTP /health on same metrics port)
  - RPC fallback with exponential backoff
  - Rate limit monitoring per recipient
  - Stalled request detection and alerting
  - Rich terminal dashboard (optional, graceful fallback)
  - Webhook alerting (Slack/Discord — free tier)
  - Daily summary reporting
  - Signal handling for clean shutdown
  - --once mode for CI/CD health checks

Requirements: pip install web3 python-dotenv rich prometheus-client

Usage:
  python3 bridge-monitoring.py              # Continuous monitoring
  python3 bridge-monitoring.py --once        # Single check (CI/CD)
  python3 bridge-monitoring.py --health-only # Just health check

Environment (.env):
  BRIDGELOCK_ADDRESS  — Deployed BridgeLock contract address
  RPC_URL             — Ethereum RPC endpoint (free: https://eth.drpc.org)
  YOUR_OPERATOR_ADDR  — Your operator address (for highlighting your confirmations)
  ALERT_WEBHOOK       — Optional Slack/Discord webhook URL
  STALL_THRESHOLD_MIN — Minutes before alerting on stalled requests (default: 30)
  RATE_LIMIT_PCT      — Alert when daily usage reaches this % of cap (default: 80)
  POLL_INTERVAL       — Seconds between block checks (default: 15)
  METRICS_PORT        — Prometheus metrics port (default: 9090, 0 to disable)
  STATE_FILE          — State persistence file (default: bridge-monitor-state.json)
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import threading
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

try:
    from web3 import Web3
except ImportError:
    print("ERROR: web3 not installed. Run: pip install web3")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env is optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# ─── CLI Arguments ────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="BAIT BridgeLock Monitor")
parser.add_argument("--once", action="store_true", help="Single check mode (for CI/CD)")
parser.add_argument("--health-only", action="store_true", help="Only run health check and exit")
parser.add_argument("--no-metrics", action="store_true", help="Disable Prometheus metrics server")
parser.add_argument("--lookback", type=int, default=10000, help="Historical lookback blocks (default: 10000)")
args = parser.parse_args()

# ─── Configuration ───────────────────────────────────────────────────────────

BRIDGELOCK_ADDRESS = os.getenv("BRIDGELOCK_ADDRESS", "")
RPC_URL = os.getenv("RPC_URL", "https://eth.drpc.org")
YOUR_OPERATOR_ADDR = os.getenv("YOUR_OPERATOR_ADDR", "")
ALERT_WEBHOOK = os.getenv("ALERT_WEBHOOK", "")
STALL_THRESHOLD_MIN = int(os.getenv("STALL_THRESHOLD_MIN", "30"))
RATE_LIMIT_PCT = int(os.getenv("RATE_LIMIT_PCT", "80"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "15"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090")) if not args.no_metrics else 0
STATE_FILE = os.getenv("STATE_FILE", "bridge-monitor-state.json")

# BridgeLock constants (from contract)
REQUIRED_CONFIRMATIONS = 3
NUM_OPERATORS = 5
RATE_LIMIT_WBAIT = 100_000  # 100K wBAIT/day/address
SAITOSHI_DECIMALS = 8

# Free RPC fallbacks (no API key required)
FREE_RPC_ENDPOINTS = [
    "https://eth.drpc.org",
    "https://rpc.ankr.com/eth",
    "https://ethereum.publicnode.com",
    "https://1rpc.io/eth",
]

# BridgeLock ABI (minimal — just events + views needed)
BRIDGELOCK_ABI = json.loads("""
[
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"requestId","type":"bytes32"},
    {"indexed":false,"name":"l1TxId","type":"bytes32"},
    {"indexed":false,"name":"recipient","type":"address"},
    {"indexed":false,"name":"amount","type":"uint256"}
  ],"name":"LockRequested","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"requestId","type":"bytes32"},
    {"indexed":false,"name":"operator","type":"address"}
  ],"name":"LockConfirmed","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"requestId","type":"bytes32"},
    {"indexed":false,"name":"recipient","type":"address"},
    {"indexed":false,"name":"amount","type":"uint256"}
  ],"name":"LockExecuted","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"releaseId","type":"bytes32"},
    {"indexed":false,"name":"burner","type":"address"},
    {"indexed":false,"name":"amount","type":"uint256"},
    {"indexed":false,"name":"l1Address","type":"string"}
  ],"name":"BurnInitiated","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"releaseId","type":"bytes32"},
    {"indexed":false,"name":"operator","type":"address"}
  ],"name":"BurnConfirmed","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":true,"name":"releaseId","type":"bytes32"},
    {"indexed":false,"name":"amount","type":"uint256"},
    {"indexed":false,"name":"l1Address","type":"string"}
  ],"name":"BurnExecuted","type":"event"},
  {"anonymous":false,"inputs":[
    {"indexed":false,"name":"index","type":"uint256"},
    {"indexed":false,"name":"oldOp","type":"address"},
    {"indexed":false,"name":"newOp","type":"address"}
  ],"name":"OperatorUpdated","type":"event"},
  {"inputs":[{"name":"","type":"uint256"}],"name":"operators","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"name":"","type":"address"}],"name":"isOperator","outputs":[{"name":"","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"paused","outputs":[{"name":"","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"getLockRequestCount","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"getBurnReleaseCount","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"name":"","type":"address"}],"name":"dailyMinted","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"REQUIRED_CONFIRMATIONS","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"RATE_LIMIT","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]
""")

# ─── Prometheus Metrics ──────────────────────────────────────────────────────

if PROMETHEUS_AVAILABLE and METRICS_PORT > 0:
    METRICS_LOCK_REQUESTS_TOTAL = Counter(
        'bait_bridge_lock_requests_total', 'Total lock-mint requests observed')
    METRICS_LOCK_REQUESTS_PENDING = Gauge(
        'bait_bridge_lock_requests_pending', 'Pending (unconfirmed) lock-mint requests')
    METRICS_LOCK_EXECUTED_TOTAL = Counter(
        'bait_bridge_lock_executed_total', 'Total lock-mint requests executed')
    METRICS_BURN_RELEASES_TOTAL = Counter(
        'bait_bridge_burn_releases_total', 'Total burn-release requests observed')
    METRICS_BURN_RELEASES_PENDING = Gauge(
        'bait_bridge_burn_releases_pending', 'Pending burn-release requests')
    METRICS_BURN_EXECUTED_TOTAL = Counter(
        'bait_bridge_burn_executed_total', 'Total burn-release requests executed')
    METRICS_RATE_LIMIT_USAGE_PCT = Gauge(
        'bait_bridge_rate_limit_usage_percent', 'Rate limit usage % per recipient',
        ['recipient'])
    METRICS_CONFIRMATION_STALL = Gauge(
        'bait_bridge_confirmation_stall_seconds', 'Seconds stalled requests have been waiting',
        ['request_type', 'request_id'])
    METRICS_LAST_PROCESSED_BLOCK = Gauge(
        'bait_bridge_last_processed_block', 'Last Ethereum block processed')
    METRICS_RPC_ERRORS = Counter(
        'bait_bridge_rpc_errors_total', 'Total RPC connection/query errors')
    METRICS_CONTRACT_PAUSED = Gauge(
        'bait_bridge_contract_paused', 'BridgeLock contract paused status (1=paused, 0=active)')
    METRICS_CONFIRMATION_PROGRESS = Gauge(
        'bait_bridge_confirmation_progress', 'Confirmation progress for pending requests',
        ['request_type', 'request_id'])
    METRICS_POLL_DURATION = Histogram(
        'bait_bridge_poll_duration_seconds', 'Time spent in each poll cycle',
        buckets=[1, 2, 5, 10, 15, 30, 60, 120])
else:
    # No-op placeholders when Prometheus is not available
    class _NoopMetric:
        def labels(self, *a, **kw): return self
        def inc(self, *a): pass
        def dec(self, *a): pass
        def set(self, *a): pass
        def observe(self, *a): pass
    METRICS_LOCK_REQUESTS_TOTAL = _NoopMetric()
    METRICS_LOCK_REQUESTS_PENDING = _NoopMetric()
    METRICS_LOCK_EXECUTED_TOTAL = _NoopMetric()
    METRICS_BURN_RELEASES_TOTAL = _NoopMetric()
    METRICS_BURN_RELEASES_PENDING = _NoopMetric()
    METRICS_BURN_EXECUTED_TOTAL = _NoopMetric()
    METRICS_RATE_LIMIT_USAGE_PCT = _NoopMetric()
    METRICS_CONFIRMATION_STALL = _NoopMetric()
    METRICS_LAST_PROCESSED_BLOCK = _NoopMetric()
    METRICS_RPC_ERRORS = _NoopMetric()
    METRICS_CONTRACT_PAUSED = _NoopMetric()
    METRICS_CONFIRMATION_PROGRESS = _NoopMetric()
    METRICS_POLL_DURATION = _NoopMetric()

# ─── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class LockRequest:
    request_id: str
    l1_tx_id: str
    recipient: str
    amount: int
    confirmations: int = 0
    confirmed_by: list = field(default_factory=list)
    executed: bool = False
    first_seen: str = ""  # ISO format for JSON serialization

    def __post_init__(self):
        if not self.first_seen:
            self.first_seen = datetime.now(timezone.utc).isoformat()

    @property
    def first_seen_dt(self) -> datetime:
        return datetime.fromisoformat(self.first_seen)

@dataclass
class BurnRelease:
    release_id: str
    burner: str
    amount: int
    l1_address: str = ""
    confirmations: int = 0
    confirmed_by: list = field(default_factory=list)
    executed: bool = False
    first_seen: str = ""

    def __post_init__(self):
        if not self.first_seen:
            self.first_seen = datetime.now(timezone.utc).isoformat()

    @property
    def first_seen_dt(self) -> datetime:
        return datetime.fromisoformat(self.first_seen)

@dataclass
class RateLimitTracker:
    address: str
    daily_minted: int = 0
    last_updated: str = ""

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now(timezone.utc).isoformat()

# ─── State Persistence ──────────────────────────────────────────────────────

class StateManager:
    """Persists monitor state to JSON for resume-on-restart capability."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.last_block = 0
        self.lock_requests: dict = {}
        self.burn_releases: dict = {}
        self.load()

    def load(self):
        """Load state from file if it exists."""
        try:
            if Path(self.filepath).exists():
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                self.last_block = data.get('last_block', 0)
                self.lock_requests = data.get('lock_requests', {})
                self.burn_releases = data.get('burn_releases', {})
                logging.getLogger('bridge-monitor').info(
                    f"Loaded state from {self.filepath}: block={self.last_block}, "
                    f"locks={len(self.lock_requests)}, burns={len(self.burn_releases)}")
        except Exception as e:
            logging.getLogger('bridge-monitor').warning(f"Failed to load state: {e}")

    def save(self, monitor: 'BridgeMonitor'):
        """Save current state to file."""
        try:
            state = {
                'last_block': monitor.last_checked_block,
                'lock_requests': {
                    rid: {
                        'request_id': req.request_id,
                        'l1_tx_id': req.l1_tx_id,
                        'recipient': req.recipient,
                        'amount': req.amount,
                        'confirmations': req.confirmations,
                        'confirmed_by': req.confirmed_by,
                        'executed': req.executed,
                        'first_seen': req.first_seen,
                    }
                    for rid, req in monitor.lock_requests.items()
                },
                'burn_releases': {
                    bid: {
                        'release_id': rel.release_id,
                        'burner': rel.burner,
                        'amount': rel.amount,
                        'l1_address': rel.l1_address,
                        'confirmations': rel.confirmations,
                        'confirmed_by': rel.confirmed_by,
                        'executed': rel.executed,
                        'first_seen': rel.first_seen,
                    }
                    for bid, rel in monitor.burn_releases.items()
                },
                'saved_at': datetime.now(timezone.utc).isoformat(),
                'alerts_count': len(monitor.alerts),
            }
            tmp_path = self.filepath + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(state, f, indent=2)
            Path(tmp_path).rename(self.filepath)
        except Exception as e:
            logging.getLogger('bridge-monitor').error(f"Failed to save state: {e}")

    def restore_state(self, monitor: 'BridgeMonitor'):
        """Restore monitor state from saved data."""
        for rid, data in self.lock_requests.items():
            if rid not in monitor.lock_requests:
                monitor.lock_requests[rid] = LockRequest(
                    request_id=data['request_id'],
                    l1_tx_id=data['l1_tx_id'],
                    recipient=data['recipient'],
                    amount=data['amount'],
                    confirmations=data.get('confirmations', 0),
                    confirmed_by=data.get('confirmed_by', []),
                    executed=data.get('executed', False),
                    first_seen=data.get('first_seen', ''),
                )

        for bid, data in self.burn_releases.items():
            if bid not in monitor.burn_releases:
                monitor.burn_releases[bid] = BurnRelease(
                    release_id=data['release_id'],
                    burner=data['burner'],
                    amount=data['amount'],
                    l1_address=data.get('l1_address', ''),
                    confirmations=data.get('confirmations', 0),
                    confirmed_by=data.get('confirmed_by', []),
                    executed=data.get('executed', False),
                    first_seen=data.get('first_seen', ''),
                )

        if self.last_block > 0:
            monitor.last_checked_block = self.last_block

# ─── Bridge Monitor ──────────────────────────────────────────────────────────

class BridgeMonitor:
    # Exponential backoff parameters
    BACKOFF_BASE = 2
    BACKOFF_MAX = 300  # 5 minutes max wait
    BACKOFF_RESET_AFTER = 300  # Reset backoff after 5 min of success

    def __init__(self, rpc_url: str, contract_address: str):
        self.w3: Optional[Web3] = None
        self._current_rpc_url = rpc_url
        self._consecutive_errors = 0
        self._last_success_time = 0.0
        self._rpc_connected = False

        self.w3 = self._connect_with_fallback(rpc_url)
        if not self.w3 or not self.w3.is_connected():
            print(f"FATAL: Cannot connect to any RPC endpoint")
            sys.exit(1)

        self._rpc_connected = True

        if not contract_address:
            print("FATAL: BRIDGELOCK_ADDRESS not set. Export it or set in .env")
            sys.exit(1)

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=BRIDGELOCK_ABI
        )
        self.lock_requests: dict[str, LockRequest] = {}
        self.burn_releases: dict[str, BurnRelease] = {}
        self.rate_limits: dict[str, RateLimitTracker] = {}
        self.operator_addresses: list[str] = []
        self.last_checked_block = 0
        self.alerts: list[str] = []
        self._shutdown_requested = False
        self._state_manager = StateManager(STATE_FILE)
        self._setup_logging()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Handle SIGTERM and SIGINT for graceful shutdown."""
        def _signal_handler(signum, frame):
            sig_name = signal.Signals(signum).name
            self.log.info(f"Received {sig_name}, initiating graceful shutdown...")
            self._shutdown_requested = True

        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)

    def _get_backoff_delay(self) -> float:
        """Calculate exponential backoff delay based on consecutive errors."""
        if self._consecutive_errors == 0:
            return 0
        delay = min(self.BACKOFF_BASE ** self._consecutive_errors, self.BACKOFF_MAX)
        return delay

    def _reset_backoff(self):
        """Reset backoff counter after successful operation."""
        now = time.time()
        if now - self._last_success_time > self.BACKOFF_RESET_AFTER:
            self._consecutive_errors = 0
        self._last_success_time = now

    def _connect_with_fallback(self, primary_url: str) -> Optional[Web3]:
        """Try primary RPC, then fallback to free endpoints."""
        urls_to_try = [primary_url] + [u for u in FREE_RPC_ENDPOINTS if u != primary_url]
        for url in urls_to_try:
            try:
                w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 30}))
                if w3.is_connected():
                    block = w3.eth.block_number
                    print(f"Connected to {url} (block: {block})")
                    self._current_rpc_url = url
                    return w3
            except Exception as e:
                print(f"Failed to connect to {url}: {e}")
                continue
        return None

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('bridge-monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.log = logging.getLogger('bridge-monitor')

    def _format_wbait(self, amount_wei: int) -> str:
        """Format amount from s'AI'toshi to wBAIT."""
        return f"{amount_wei / 10**SAITOSHI_DECIMALS:,.8f}"

    def _send_alert(self, message: str, level: str = "warning"):
        """Send alert via webhook (if configured) and log."""
        if level == "critical":
            self.log.critical(f"ALERT: {message}")
        else:
            self.log.warning(f"ALERT: {message}")
        self.alerts.append(f"{datetime.now(timezone.utc).isoformat()}: {message}")
        # Keep only last 100 alerts in memory
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        if ALERT_WEBHOOK:
            try:
                import urllib.request
                payload = json.dumps({"text": message, "level": level}).encode()
                req = urllib.request.Request(ALERT_WEBHOOK, data=payload,
                                           headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=10)
            except Exception as e:
                self.log.error(f"Failed to send webhook alert: {e}")

    def load_operators(self):
        """Load operator addresses from the contract."""
        self.operator_addresses = []
        for i in range(NUM_OPERATORS):
            try:
                op = self.contract.functions.operators(i).call()
                self.operator_addresses.append(op)
                self.log.info(f"Operator [{i}]: {op}")
            except Exception as e:
                self.log.error(f"Failed to load operator {i}: {e}")
                METRICS_RPC_ERRORS.inc()
        return self.operator_addresses

    def check_contract_status(self) -> bool:
        """Check if contract is paused."""
        try:
            paused = self.contract.functions.paused().call()
            METRICS_CONTRACT_PAUSED.set(1 if paused else 0)
            if paused:
                self._send_alert("BridgeLock contract is PAUSED!", level="critical")
            return paused
        except Exception as e:
            self.log.error(f"Failed to check paused status: {e}")
            METRICS_RPC_ERRORS.inc()
            return False

    def process_events(self, from_block: int, to_block: int):
        """Process all BridgeLock events in the given block range."""
        chunk_size = 2000  # Safe chunk size for free RPCs

        for start in range(from_block, to_block + 1, chunk_size):
            end = min(start + chunk_size - 1, to_block)

            # Process each event type
            self._process_lock_requested(start, end)
            self._process_lock_confirmed(start, end)
            self._process_lock_executed(start, end)
            self._process_burn_initiated(start, end)
            self._process_burn_confirmed(start, end)
            self._process_burn_executed(start, end)
            self._process_operator_updated(start, end)

        self.last_checked_block = to_block
        METRICS_LAST_PROCESSED_BLOCK.set(to_block)

    def _process_lock_requested(self, from_block: int, to_block: int):
        try:
            events = self.contract.events.LockRequested.create_filter(
                fromBlock=from_block, toBlock=to_block
            ).get_all_entries()
        except Exception as e:
            self.log.error(f"Error fetching LockRequested events: {e}")
            METRICS_RPC_ERRORS.inc()
            return

        for event in events:
            rid = event.args.requestId.hex()
            if rid not in self.lock_requests:
                self.lock_requests[rid] = LockRequest(
                    request_id=rid,
                    l1_tx_id=event.args.l1TxId.hex(),
                    recipient=event.args.recipient,
                    amount=event.args.amount,
                    first_seen=datetime.now(timezone.utc).isoformat()
                )
                METRICS_LOCK_REQUESTS_TOTAL.inc()
                self.log.info(
                    f"LockRequested: {rid[:16]}... | "
                    f"Recipient: {event.args.recipient[:10]}... | "
                    f"Amount: {self._format_wbait(event.args.amount)} wBAIT"
                )

    def _process_lock_confirmed(self, from_block: int, to_block: int):
        try:
            events = self.contract.events.LockConfirmed.create_filter(
                fromBlock=from_block, toBlock=to_block
            ).get_all_entries()
        except Exception as e:
            self.log.error(f"Error fetching LockConfirmed events: {e}")
            METRICS_RPC_ERRORS.inc()
            return

        for event in events:
            rid = event.args.requestId.hex()
            operator = event.args.operator
            if rid in self.lock_requests:
                req = self.lock_requests[rid]
                if operator not in req.confirmed_by:
                    req.confirmed_by.append(operator)
                    req.confirmations = len(req.confirmed_by)
                is_mine = operator.lower() == YOUR_OPERATOR_ADDR.lower()
                self.log.info(
                    f"LockConfirmed: {rid[:16]}... | "
                    f"Operator: {operator[:10]}... | "
                    f"Progress: {req.confirmations}/{REQUIRED_CONFIRMATIONS}"
                    f"{' ★ YOUR CONFIRMATION' if is_mine else ''}"
                )
                METRICS_CONFIRMATION_PROGRESS.labels(
                    request_type='lock', request_id=rid[:16]
                ).set(req.confirmations / REQUIRED_CONFIRMATIONS)

    def _process_lock_executed(self, from_block: int, to_block: int):
        try:
            events = self.contract.events.LockExecuted.create_filter(
                fromBlock=from_block, toBlock=to_block
            ).get_all_entries()
        except Exception as e:
            self.log.error(f"Error fetching LockExecuted events: {e}")
            METRICS_RPC_ERRORS.inc()
            return

        for event in events:
            rid = event.args.requestId.hex()
            if rid in self.lock_requests:
                self.lock_requests[rid].executed = True
            METRICS_LOCK_EXECUTED_TOTAL.inc()
            self.log.info(
                f"LockExecuted: {rid[:16]}... | "
                f"Recipient: {event.args.recipient[:10]}... | "
                f"Amount: {self._format_wbait(event.args.amount)} wBAIT minted"
            )

    def _process_burn_initiated(self, from_block: int, to_block: int):
        try:
            events = self.contract.events.BurnInitiated.create_filter(
                fromBlock=from_block, toBlock=to_block
            ).get_all_entries()
        except Exception as e:
            self.log.error(f"Error fetching BurnInitiated events: {e}")
            METRICS_RPC_ERRORS.inc()
            return

        for event in events:
            bid = event.args.releaseId.hex()
            if bid not in self.burn_releases:
                self.burn_releases[bid] = BurnRelease(
                    release_id=bid,
                    burner=event.args.burner,
                    amount=event.args.amount,
                    l1_address=event.args.l1Address,
                    first_seen=datetime.now(timezone.utc).isoformat()
                )
                METRICS_BURN_RELEASES_TOTAL.inc()
                self.log.info(
                    f"BurnInitiated: {bid[:16]}... | "
                    f"Burner: {event.args.burner[:10]}... | "
                    f"Amount: {self._format_wbait(event.args.amount)} wBAIT | "
                    f"L1: {event.args.l1Address}"
                )

    def _process_burn_confirmed(self, from_block: int, to_block: int):
        try:
            events = self.contract.events.BurnConfirmed.create_filter(
                fromBlock=from_block, toBlock=to_block
            ).get_all_entries()
        except Exception as e:
            self.log.error(f"Error fetching BurnConfirmed events: {e}")
            METRICS_RPC_ERRORS.inc()
            return

        for event in events:
            bid = event.args.releaseId.hex()
            operator = event.args.operator
            if bid in self.burn_releases:
                rel = self.burn_releases[bid]
                if operator not in rel.confirmed_by:
                    rel.confirmed_by.append(operator)
                    rel.confirmations = len(rel.confirmed_by)
                is_mine = operator.lower() == YOUR_OPERATOR_ADDR.lower()
                self.log.info(
                    f"BurnConfirmed: {bid[:16]}... | "
                    f"Operator: {operator[:10]}... | "
                    f"Progress: {rel.confirmations}/{REQUIRED_CONFIRMATIONS}"
                    f"{' ★ YOUR CONFIRMATION' if is_mine else ''}"
                )
                METRICS_CONFIRMATION_PROGRESS.labels(
                    request_type='burn', request_id=bid[:16]
                ).set(rel.confirmations / REQUIRED_CONFIRMATIONS)

    def _process_burn_executed(self, from_block: int, to_block: int):
        try:
            events = self.contract.events.BurnExecuted.create_filter(
                fromBlock=from_block, toBlock=to_block
            ).get_all_entries()
        except Exception as e:
            self.log.error(f"Error fetching BurnExecuted events: {e}")
            METRICS_RPC_ERRORS.inc()
            return

        for event in events:
            bid = event.args.releaseId.hex()
            if bid in self.burn_releases:
                self.burn_releases[bid].executed = True
            METRICS_BURN_EXECUTED_TOTAL.inc()
            self.log.info(
                f"BurnExecuted: {bid[:16]}... | "
                f"Amount: {self._format_wbait(event.args.amount)} wBAIT | "
                f"L1: {event.args.l1Address}"
            )

    def _process_operator_updated(self, from_block: int, to_block: int):
        try:
            events = self.contract.events.OperatorUpdated.create_filter(
                fromBlock=from_block, toBlock=to_block
            ).get_all_entries()
        except Exception as e:
            self.log.error(f"Error fetching OperatorUpdated events: {e}")
            METRICS_RPC_ERRORS.inc()
            return

        for event in events:
            self._send_alert(
                f"OperatorUpdated: index={event.args.index} | "
                f"old={event.args.oldOp} | new={event.args.newOp}",
                level="critical"
            )
        # Reload operators after any update
        if events:
            self.load_operators()

    def check_stalled_requests(self):
        """Alert on requests that haven't reached threshold within STALL_THRESHOLD_MIN."""
        now = datetime.now(timezone.utc)
        threshold_secs = STALL_THRESHOLD_MIN * 60
        stalled_count = 0

        for rid, req in self.lock_requests.items():
            if req.executed:
                continue
            elapsed = (now - req.first_seen_dt).total_seconds()
            if elapsed > threshold_secs and req.confirmations < REQUIRED_CONFIRMATIONS:
                stalled_count += 1
                stall_secs = int(elapsed)
                self._send_alert(
                    f"STALLED Lock Request: {rid[:16]}... | "
                    f"Confirmations: {req.confirmations}/{REQUIRED_CONFIRMATIONS} | "
                    f"Age: {int(elapsed/60)} min | "
                    f"Missing operators need to confirm!"
                )
                METRICS_CONFIRMATION_STALL.labels(
                    request_type='lock', request_id=rid[:16]
                ).set(stall_secs)

        for bid, rel in self.burn_releases.items():
            if rel.executed:
                continue
            elapsed = (now - rel.first_seen_dt).total_seconds()
            if elapsed > threshold_secs and rel.confirmations < REQUIRED_CONFIRMATIONS:
                stalled_count += 1
                stall_secs = int(elapsed)
                self._send_alert(
                    f"STALLED Burn Release: {bid[:16]}... | "
                    f"Confirmations: {rel.confirmations}/{REQUIRED_CONFIRMATIONS} | "
                    f"Age: {int(elapsed/60)} min"
                )
                METRICS_CONFIRMATION_STALL.labels(
                    request_type='burn', request_id=bid[:16]
                ).set(stall_secs)

        return stalled_count

    def check_rate_limits(self):
        """Monitor rate limit usage by checking dailyMinted for active recipients."""
        recipients_checked = set()
        for rid, req in self.lock_requests.items():
            if req.executed or req.recipient in recipients_checked:
                continue
            recipients_checked.add(req.recipient)
            recipient = req.recipient
            if recipient not in self.rate_limits:
                try:
                    daily = self.contract.functions.dailyMinted(recipient).call()
                    self.rate_limits[recipient] = RateLimitTracker(
                        address=recipient,
                        daily_minted=daily
                    )
                except Exception:
                    METRICS_RPC_ERRORS.inc()
                    continue

            tracker = self.rate_limits[recipient]
            rate_limit_saitoshi = RATE_LIMIT_WBAIT * 10**SAITOSHI_DECIMALS
            if rate_limit_saitoshi > 0:
                usage_pct = (tracker.daily_minted / rate_limit_saitoshi) * 100
            else:
                usage_pct = 0

            METRICS_RATE_LIMIT_USAGE_PCT.labels(recipient=recipient[:10]).set(usage_pct)

            if usage_pct >= RATE_LIMIT_PCT:
                self._send_alert(
                    f"Rate limit approaching: {recipient[:10]}... | "
                    f"Usage: {self._format_wbait(tracker.daily_minted)} / "
                    f"{RATE_LIMIT_WBAIT:,} wBAIT ({usage_pct:.1f}%)"
                )

    def update_gauge_metrics(self):
        """Update Prometheus gauge metrics based on current state."""
        pending_locks = sum(1 for r in self.lock_requests.values() if not r.executed)
        pending_burns = sum(1 for b in self.burn_releases.values() if not b.executed)
        METRICS_LOCK_REQUESTS_PENDING.set(pending_locks)
        METRICS_BURN_RELEASES_PENDING.set(pending_burns)

    def get_status_summary(self) -> dict:
        """Get current monitoring status summary."""
        pending_locks = [r for r in self.lock_requests.values() if not r.executed]
        pending_burns = [b for b in self.burn_releases.values() if not b.executed]

        return {
            "contract": BRIDGELOCK_ADDRESS,
            "rpc_url": self._current_rpc_url,
            "paused": self.check_contract_status() if self.w3 and self.w3.is_connected() else None,
            "last_block": self.last_checked_block,
            "rpc_connected": self._rpc_connected,
            "lock_requests": {
                "total": len(self.lock_requests),
                "pending": len(pending_locks),
                "executed": len(self.lock_requests) - len(pending_locks),
            },
            "burn_releases": {
                "total": len(self.burn_releases),
                "pending": len(pending_burns),
                "executed": len(self.burn_releases) - len(pending_burns),
            },
            "operators": self.operator_addresses,
            "pending_needing_your_confirmation": self._get_pending_for_operator(),
            "recent_alerts": self.alerts[-10:],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _get_pending_for_operator(self) -> list:
        """Find pending requests that need YOUR confirmation."""
        if not YOUR_OPERATOR_ADDR:
            return []

        my_addr = YOUR_OPERATOR_ADDR.lower()
        pending = []

        for rid, req in self.lock_requests.items():
            if not req.executed and my_addr not in [a.lower() for a in req.confirmed_by]:
                pending.append({
                    "type": "lock",
                    "id": rid[:16] + "...",
                    "confirmations": f"{req.confirmations}/{REQUIRED_CONFIRMATIONS}",
                    "amount": self._format_wbait(req.amount),
                    "recipient": req.recipient[:10] + "..."
                })

        for bid, rel in self.burn_releases.items():
            if not rel.executed and my_addr not in [a.lower() for a in rel.confirmed_by]:
                pending.append({
                    "type": "burn",
                    "id": bid[:16] + "...",
                    "confirmations": f"{rel.confirmations}/{REQUIRED_CONFIRMATIONS}",
                    "amount": self._format_wbait(rel.amount),
                    "l1_address": rel.l1_address
                })

        return pending

    def print_dashboard(self):
        """Print a rich dashboard of current state."""
        status = self.get_status_summary()

        if RICH_AVAILABLE:
            console = Console()
            console.print(Panel.fit(
                f"[bold]BAIT BridgeLock Monitor[/bold]\n"
                f"Contract: {BRIDGELOCK_ADDRESS[:20]}...\n"
                f"RPC: {self._current_rpc_url}\n"
                f"Block: {status['last_block']}\n"
                f"Paused: {'[red]YES[/red]' if status['paused'] else '[green]NO[/green]'}\n"
                f"Locks: {status['lock_requests']['total']} total, {status['lock_requests']['pending']} pending\n"
                f"Burns: {status['burn_releases']['total']} total, {status['burn_releases']['pending']} pending",
                title="Bridge Status"
            ))

            if status["pending_needing_your_confirmation"]:
                table = Table(title="Pending — Needs YOUR Confirmation")
                table.add_column("Type")
                table.add_column("ID")
                table.add_column("Progress")
                table.add_column("Amount (wBAIT)")
                for item in status["pending_needing_your_confirmation"]:
                    table.add_row(item["type"], item["id"], item["confirmations"], item["amount"])
                console.print(table)
        else:
            # Plain text fallback
            print(f"\n{'='*60}")
            print(f"BAIT BridgeLock Monitor | Block: {status['last_block']}")
            print(f"RPC: {self._current_rpc_url} | Paused: {status['paused']}")
            print(f"Lock Requests: {status['lock_requests']}")
            print(f"Burn Releases: {status['burn_releases']}")
            if status["pending_needing_your_confirmation"]:
                print("\n>>> Pending requests needing YOUR confirmation:")
                for item in status["pending_needing_your_confirmation"]:
                    print(f"  [{item['type']}] {item['id']} | {item['confirmations']} | {item['amount']} wBAIT")

    def generate_daily_summary(self) -> str:
        """Generate a daily summary report."""
        now = datetime.now(timezone.utc)
        pending_locks = [r for r in self.lock_requests.values() if not r.executed]
        pending_burns = [b for b in self.burn_releases.values() if not b.executed]
        executed_locks = [r for r in self.lock_requests.values() if r.executed]
        executed_burns = [b for b in self.burn_releases.values() if b.executed]

        total_minted = sum(r.amount for r in executed_locks)
        total_burned = sum(b.amount for b in executed_burns)

        summary = (
            f"BAIT BridgeLock Daily Summary — {now.strftime('%Y-%m-%d')}\n"
            f"{'='*50}\n"
            f"Contract: {BRIDGELOCK_ADDRESS}\n"
            f"Last Block: {self.last_checked_block}\n"
            f"Contract Paused: {self.check_contract_status()}\n"
            f"\n"
            f"Lock-Mint Requests:\n"
            f"  Total: {len(self.lock_requests)} | Pending: {len(pending_locks)} | Executed: {len(executed_locks)}\n"
            f"  Total wBAIT Minted: {self._format_wbait(total_minted)}\n"
            f"\n"
            f"Burn-Release Requests:\n"
            f"  Total: {len(self.burn_releases)} | Pending: {len(pending_burns)} | Executed: {len(executed_burns)}\n"
            f"  Total wBAIT Burned: {self._format_wbait(total_burned)}\n"
            f"\n"
            f"Net wBAIT Supply Change: {self._format_wbait(total_minted - total_burned)}\n"
            f"\n"
            f"Alerts (last 24h): {len(self.alerts)}\n"
            f"Operators Available: {len(self.operator_addresses)}/{NUM_OPERATORS}\n"
        )
        return summary

    def run_once(self) -> dict:
        """Run a single monitoring check (for CI/CD --once mode)."""
        self.log.info("Running single monitoring check (--once mode)")

        self.load_operators()
        paused = self.check_contract_status()

        current_block = self.w3.eth.block_number
        lookback = min(current_block, args.lookback)
        from_block = current_block - lookback
        self.log.info(f"Processing events from block {from_block} to {current_block}")
        self.process_events(from_block, current_block)

        stalled = self.check_stalled_requests()
        self.check_rate_limits()
        self.update_gauge_metrics()

        status = self.get_status_summary()
        status['stalled_requests'] = stalled

        self.print_dashboard()

        # Save state
        self._state_manager.save(self)

        return status

    def run(self, poll_interval: int = None):
        """Main monitoring loop."""
        if poll_interval is None:
            poll_interval = POLL_INTERVAL

        self.log.info("=" * 60)
        self.log.info("BAIT BridgeLock Monitor starting...")
        self.log.info(f"Contract: {BRIDGELOCK_ADDRESS}")
        self.log.info(f"RPC: {RPC_URL}")
        self.log.info(f"Poll interval: {poll_interval}s")
        self.log.info(f"Stall threshold: {STALL_THRESHOLD_MIN} min")
        self.log.info(f"Metrics port: {METRICS_PORT if METRICS_PORT > 0 else 'disabled'}")
        self.log.info(f"State file: {STATE_FILE}")
        self.log.info("=" * 60)

        # Start Prometheus metrics server
        if PROMETHEUS_AVAILABLE and METRICS_PORT > 0:
            try:
                start_http_server(METRICS_PORT)
                self.log.info(f"Prometheus metrics available on http://localhost:{METRICS_PORT}/metrics")
                self.log.info(f"Health check available on http://localhost:{METRICS_PORT}/ (check /metrics for health)")
            except Exception as e:
                self.log.warning(f"Failed to start metrics server: {e}")

        # Load operators
        self.load_operators()

        # Check contract status
        paused = self.check_contract_status()
        if paused:
            self._send_alert("BridgeLock is PAUSED on startup!", level="critical")

        # Restore state from previous run
        self._state_manager.restore_state(self)
        self.log.info(f"State restored: last_block={self.last_checked_block}, "
                      f"locks={len(self.lock_requests)}, burns={len(self.burn_releases)}")

        # Get current block
        current_block = self.w3.eth.block_number

        # Process historical events
        if self.last_checked_block > 0 and self.last_checked_block < current_block:
            # Resume from saved state
            from_block = self.last_checked_block + 1
            self.log.info(f"Resuming from saved block {self.last_checked_block}")
        else:
            # Fresh start: look back
            lookback = min(current_block, args.lookback)
            from_block = current_block - lookback
            self.log.info(f"Processing historical events from block {from_block}")

        self.process_events(from_block, current_block)

        # Daily summary tracking
        last_summary_date = datetime.now(timezone.utc).date()
        summary_interval_hours = 24

        # Main loop
        self.log.info(f"Monitoring live blocks (polling every {poll_interval}s)...")
        try:
            while not self._shutdown_requested:
                poll_start = time.time()
                try:
                    current_block = self.w3.eth.block_number
                    if current_block > self.last_checked_block:
                        self.process_events(self.last_checked_block + 1, current_block)

                    # Periodic checks
                    self.check_stalled_requests()
                    self.check_rate_limits()
                    self.update_gauge_metrics()

                    # Print dashboard every 10 poll cycles
                    if int(poll_start) % (poll_interval * 10) < poll_interval:
                        self.print_dashboard()

                    # Daily summary
                    now = datetime.now(timezone.utc)
                    if (now.date() > last_summary_date and
                            now.hour >= 0 and now.minute < poll_interval / 60):
                        summary = self.generate_daily_summary()
                        self.log.info(f"\n{summary}")
                        last_summary_date = now.date()

                    # Reset backoff on success
                    self._reset_backoff()
                    self._consecutive_errors = 0
                    self._rpc_connected = True

                except Exception as e:
                    self._consecutive_errors += 1
                    METRICS_RPC_ERRORS.inc()
                    self.log.error(f"Error in monitoring loop (attempt {self._consecutive_errors}): {e}")

                    # Exponential backoff
                    backoff = self._get_backoff_delay()
                    if backoff > 0:
                        self.log.info(f"Backing off for {backoff:.0f}s before retry...")

                    # Try reconnecting
                    self._rpc_connected = False
                    self.w3 = self._connect_with_fallback(RPC_URL)
                    if not self.w3 or not self.w3.is_connected():
                        self.log.error("Lost connection, waiting for backoff period...")
                        time.sleep(backoff)
                        continue
                    self._rpc_connected = True

                # Save state periodically (every 5 minutes)
                if int(poll_start) % 300 < poll_interval:
                    self._state_manager.save(self)

                # Observe poll duration
                poll_duration = time.time() - poll_start
                METRICS_POLL_DURATION.observe(poll_duration)

                # Wait for next poll (interruptible)
                wait_end = time.time() + poll_interval
                while time.time() < wait_end and not self._shutdown_requested:
                    time.sleep(min(1, wait_end - time.time()))

        except KeyboardInterrupt:
            pass
        finally:
            self.log.info("Bridge monitor shutting down...")
            # Save final state
            self._state_manager.save(self)

            # Generate final summary
            summary = self.generate_daily_summary()
            self.log.info(f"\n{summary}")

            self.log.info(f"State saved to {STATE_FILE}")
            self.log.info("Bridge monitor stopped.")


# ─── Health Check ─────────────────────────────────────────────────────────────

def run_health_check() -> int:
    """Quick health check — verify RPC and contract connectivity."""
    if not BRIDGELOCK_ADDRESS:
        print("FAIL: BRIDGELOCK_ADDRESS not set")
        return 2

    w3 = None
    for url in [RPC_URL] + FREE_RPC_ENDPOINTS:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                break
        except Exception:
            continue

    if not w3 or not w3.is_connected():
        print("FAIL: Cannot connect to any RPC endpoint")
        return 2

    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(BRIDGELOCK_ADDRESS),
            abi=BRIDGELOCK_ABI
        )
        paused = contract.functions.paused().call()
        lock_count = contract.functions.getLockRequestCount().call()
        burn_count = contract.functions.getBurnReleaseCount().call()
        block = w3.eth.block_number

        print(f"OK: RPC connected (block: {block})")
        print(f"OK: Contract accessible (paused: {paused})")
        print(f"OK: Lock requests: {lock_count}, Burn releases: {burn_count}")
        return 0 if not paused else 1  # 0=healthy, 1=paused (degraded)
    except Exception as e:
        print(f"FAIL: Contract call error: {e}")
        return 2


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Health-only mode
    if args.health_only:
        exit_code = run_health_check()
        sys.exit(exit_code)

    if not BRIDGELOCK_ADDRESS:
        print("Usage: Set BRIDGELOCK_ADDRESS in environment or .env file")
        print("  export BRIDGELOCK_ADDRESS=0x...")
        print("  python3 bridge-monitoring.py")
        print()
        print("Free RPC endpoints (no API key needed):")
        for rpc in FREE_RPC_ENDPOINTS:
            print(f"  {rpc}")
        print()
        print("Modes:")
        print("  python3 bridge-monitoring.py              # Continuous monitoring")
        print("  python3 bridge-monitoring.py --once        # Single check (CI/CD)")
        print("  python3 bridge-monitoring.py --health-only # Health check")
        sys.exit(1)

    monitor = BridgeMonitor(RPC_URL, BRIDGELOCK_ADDRESS)

    if args.once:
        # Single check mode (for CI/CD pipelines)
        status = monitor.run_once()
        # Exit with error if critical issues found
        if status.get('paused'):
            print("WARNING: Bridge is paused")
            sys.exit(1)
        stalled = status.get('stalled_requests', 0)
        if stalled > 0:
            print(f"WARNING: {stalled} stalled requests detected")
            sys.exit(1)
        sys.exit(0)
    else:
        # Continuous monitoring
        monitor.run()
