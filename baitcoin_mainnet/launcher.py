r"""
Mainnet Launch Controller -- Phase 22.

Orchestrates the final steps for launching the b'AI'tcoin mainnet:

1. **Genesis Block Configuration** -- Final genesis parameters with
   pre-allocated addresses for team, ecosystem fund, and bug bounty pool.
2. **Network Bootstrapping** -- Seed node configuration, DNS bootstrap,
   peer discovery initialization.
3. **Health Monitoring** -- Real-time metrics collection, alerting
   thresholds, incident escalation.
4. **Incident Response** -- Automated runbook execution for common
   failure modes (chain split, high orphan rate, mempool bloat, etc.).
5. **Launch Checklist** -- Final verification before going live.
6. **Post-Launch Metrics** -- KPI tracking against Go Live criteria.

Usage::

    from baitcoin_mainnet.launcher import MainnetLauncher

    launcher = MainnetLauncher()
    launcher.prepare_genesis()
    launcher.bootstrap_network()
    launcher.start_monitoring()
    # Blocks are now being mined on mainnet

"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Mainnet Constants ────────────────────────────────────────────────────────

MAINNET_MAGIC: bytes = b'\xba\x49\x74\x01'  # Network magic for mainnet (different from testnet)
MAINNET_VERSION: str = "1.0.0"
MAINNET_PORT: int = 18445
MAINNET_P2P_PORT: int = 18446

# Genesis Block Allocation
GENESIS_PREMINE: int = 2_100_000 * 100_000_000  # 2.1M BAIT (10% of 21M) for ecosystem
ALLOCATION = {
    "ecosystem_fund": {
        "amount_bait": 1_050_000,
        "description": "Ecosystem development fund (5% of supply)",
        "vesting_months": 48,
        "address": "bAI1qecosystemfund0000000000000000000000",
    },
    "team": {
        "amount_bait": 630_000,
        "description": "Team and advisors (3% of supply)",
        "vesting_months": 36,
        "address": "bAI1qteamadvisors00000000000000000000000",
    },
    "bug_bounty_pool": {
        "amount_bait": 210_000,
        "description": "Bug bounty program pool (1% of supply)",
        "vesting_months": 0,
        "address": "bAI1qbugbountypool00000000000000000000000",
    },
    "community_grants": {
        "amount_bait": 210_000,
        "description": "Community grants and incentives (1% of supply)",
        "vesting_months": 24,
        "address": "bAI1qcommunitygrants0000000000000000000000",
    },
}

# Seed Nodes (to be replaced with actual deployment IPs)
DEFAULT_SEED_NODES: List[Dict[str, Any]] = [
    {"host": "seed1.mybait.org", "port": MAINNET_P2P_PORT, "location": "US-East"},
    {"host": "seed2.mybait.org", "port": MAINNET_P2P_PORT, "location": "US-West"},
    {"host": "seed3.mybait.org", "port": MAINNET_P2P_PORT, "location": "EU-West"},
    {"host": "seed4.mybait.org", "port": MAINNET_P2P_PORT, "location": "EU-Central"},
    {"host": "seed5.mybait.org", "port": MAINNET_P2P_PORT, "location": "AP-Southeast"},
]

# Health Check Thresholds
HEALTH_THRESHOLDS = {
    "max_orphan_rate": 0.01,          # <1% orphan blocks
    "min_peer_count": 5,             # At least 5 connected peers
    "max_block_propagation_s": 5.0,  # Block propagation <5s
    "min_uptime_pct": 99.9,          # 99.9% uptime target
    "max_mempool_size": 10000,       # Max 10K unconfirmed txs
    "max_block_time_variance_s": 10, # ±10s from 30s target
}

# Alert Severity
ALERT_THRESHOLD = {
    "CRITICAL": 0.05,   # Alert at 5% threshold breach
    "WARNING": 0.10,    # Warn at 10%
    "INFO": 0.20,       # Info at 20%
}


class LaunchPhase(str, Enum):
    PREPARATION = "preparation"
    GENESIS = "genesis"
    BOOTSTRAP = "bootstrap"
    VALIDATION = "validation"
    LIVE = "live"
    MONITORING = "monitoring"


class IncidentSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class HealthMetric:
    """A single health metric data point."""
    name: str
    value: float
    threshold: float
    unit: str = ""
    healthy: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "threshold": self.threshold,
            "unit": self.unit,
            "healthy": self.healthy,
        }


@dataclass
class Alert:
    """A monitoring alert."""
    alert_id: str
    severity: str
    metric_name: str
    message: str
    value: float
    threshold: float
    created_at: float = 0.0
    acknowledged: bool = False
    resolved: bool = False
    runbook: str = ""

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity,
            "metric_name": self.metric_name,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "created_at": self.created_at,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "runbook": self.runbook,
        }


@dataclass
class IncidentRunbook:
    """Automated runbook for incident response."""
    incident_type: str
    severity: IncidentSeverity
    description: str
    detection_criteria: List[str]
    auto_actions: List[str]
    manual_steps: List[str]
    escalation_contact: str = ""
    max_response_time_s: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_type": self.incident_type,
            "severity": self.severity.value,
            "description": self.description,
            "detection_criteria": self.detection_criteria,
            "auto_actions": self.auto_actions,
            "manual_steps": self.manual_steps,
            "escalation_contact": self.escalation_contact,
            "max_response_time_s": self.max_response_time_s,
        }


# ── Incident Runbooks ───────────────────────────────────────────────────────

INCIDENT_RUNBOOKS: List[IncidentRunbook] = [
    IncidentRunbook(
        incident_type="chain_split",
        severity=IncidentSeverity.CRITICAL,
        description="Blockchain has forked into two competing chains",
        detection_criteria=[
            "Multiple chain tips detected",
            "Orphan rate exceeds 1%",
            "Peers report conflicting best blocks",
        ],
        auto_actions=[
            "Pause new block production",
            "Log all chain tips with full state",
            "Notify all connected peers of pause",
            "Snapshot current state to WAL",
        ],
        manual_steps=[
            "1. Identify the longest valid chain",
            "2. Verify consensus rules on both chains",
            "3. Determine root cause (network partition, consensus bug)",
            "4. Coordinate reorg to canonical chain",
            "5. Resume block production",
        ],
        escalation_contact="oncall@mybait.org",
        max_response_time_s=900,  # 15 min
    ),
    IncidentRunbook(
        incident_type="high_orphan_rate",
        severity=IncidentSeverity.HIGH,
        description="Orphan block rate exceeds acceptable threshold",
        detection_criteria=[
            "Orphan rate > 1% in last 100 blocks",
            "Block propagation time > 5 seconds",
            "Peers reporting missing blocks",
        ],
        auto_actions=[
            "Increase peer connection count",
            "Enable compact block relay",
            "Log network latency to all peers",
        ],
        manual_steps=[
            "1. Check network connectivity between nodes",
            "2. Verify block propagation times",
            "3. Review peer quality and connectivity",
            "4. Consider adjusting block size or relay strategy",
        ],
        escalation_contact="oncall@mybait.org",
        max_response_time_s=3600,  # 1 hour
    ),
    IncidentRunbook(
        incident_type="mempool_bloat",
        severity=IncidentSeverity.MEDIUM,
        description="Mempool size exceeds healthy threshold",
        detection_criteria=[
            "Mempool size > 10,000 transactions",
            "Transaction inclusion time > 2 blocks",
            "Fee market shows unusual spikes",
        ],
        auto_actions=[
            "Increase mining priority for high-fee transactions",
            "Log mempool composition by type",
            "Enable dynamic fee estimation",
        ],
        manual_steps=[
            "1. Analyze mempool composition",
            "2. Check for spam patterns",
            "3. Consider increasing block size limit",
            "4. Adjust fee market parameters",
        ],
        escalation_contact="oncall@mybait.org",
        max_response_time_s=7200,  # 2 hours
    ),
    IncidentRunbook(
        incident_type="consensus_failure",
        severity=IncidentSeverity.CRITICAL,
        description="Consensus engine has produced an invalid state",
        detection_criteria=[
            "Block validation failure rate > 0",
            "zkML proof verification returning false positives",
            "Difficulty adjustment out of bounds",
        ],
        auto_actions=[
            "Halt block production immediately",
            "Snapshot full state",
            "Log all consensus parameters",
            "Notify all connected peers",
        ],
        manual_steps=[
            "1. Identify the specific consensus failure",
            "2. Roll back to last known good state",
            "3. Fix consensus logic",
            "4. Deploy hotfix via CI/CD",
            "5. Coordinate network restart",
        ],
        escalation_contact="oncall@mybait.org",
        max_response_time_s=300,  # 5 min
    ),
    IncidentRunbook(
        incident_type="peer_disconnect",
        severity=IncidentSeverity.LOW,
        description="Significant number of peers disconnected",
        detection_criteria=[
            "Connected peer count < 5",
            "Multiple connection failures in short period",
            "Peer addresses returning connection refused",
        ],
        auto_actions=[
            "Reconnect to all known seed nodes",
            "Rediscover peers via DHT",
            "Log connection error details",
        ],
        manual_steps=[
            "1. Check seed node availability",
            "2. Verify network firewall rules",
            "3. Check DNS resolution for seed hosts",
            "4. Restart P2P listener if needed",
        ],
        escalation_contact="infra@mybait.org",
        max_response_time_s=1800,  # 30 min
    ),
]


class MainnetLauncher:
    """Orchestrates the b'AI'tcoin mainnet launch.

    Manages genesis configuration, network bootstrapping, health monitoring,
    incident response, and post-launch KPI tracking.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.phase = LaunchPhase.PREPARATION
        self.genesis_config: Dict[str, Any] = {}
        self.seed_nodes: List[Dict[str, Any]] = list(DEFAULT_SEED_NODES)
        self.health_metrics: Dict[str, HealthMetric] = {}
        self.alerts: List[Alert] = []
        self.runbooks: Dict[str, IncidentRunbook] = {rb.incident_type: rb for rb in INCIDENT_RUNBOOKS}
        self._alert_counter: int = 0
        self._launch_time: Optional[float] = None
        self._block_times: List[float] = []
        self._total_blocks_post_launch: int = 0
        self._total_txs_post_launch: int = 0

    # ── 1. Genesis Configuration ─────────────────────────────────────────────

    def prepare_genesis(self) -> Dict[str, Any]:
        """Prepare mainnet genesis block configuration.

        Sets up:
        - Network parameters (magic, version, ports)
        - Token parameters (supply, decimals, halving)
        - Pre-mine allocation for ecosystem fund, team, bounties
        - Initial difficulty target
        - Seed node list
        """
        self.phase = LaunchPhase.GENESIS

        self.genesis_config = {
            "network": {
                "name": "b'AI'tcoin Mainnet",
                "magic": MAINNET_MAGIC.hex(),
                "version": MAINNET_VERSION,
                "api_port": MAINNET_PORT,
                "p2p_port": MAINNET_P2P_PORT,
            },
            "token": {
                "symbol": "BAIT",
                "decimals": 8,
                "max_supply": 21_000_000,
                "initial_reward": 50,
                "halving_interval": 210_000,
                "block_time_target_s": 30,
            },
            "consensus": {
                "algorithm": "zkML + PoUW",
                "initial_difficulty": self.config.get("initial_difficulty", 16),
                "difficulty_adjustment_interval": 2016,
                "max_target": "0x00ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            },
            "premine_allocation": ALLOCATION,
            "premine_total_bait": sum(a["amount_bait"] for a in ALLOCATION.values()),
            "mining_supply_bait": 21_000_000 - sum(a["amount_bait"] for a in ALLOCATION.values()),
            "seed_nodes": self.seed_nodes,
            "genesis_timestamp": time.time(),
        }

        logger.info(f"Genesis config prepared: {self.genesis_config['token']}")
        logger.info(f"Pre-mine: {self.genesis_config['premine_total_bait']:,} BAIT across {len(ALLOCATION)} allocations")
        logger.info(f"Mining supply: {self.genesis_config['mining_supply_bait']:,} BAIT")
        return self.genesis_config

    # ── 2. Network Bootstrapping ────────────────────────────────────────────

    def bootstrap_network(self, num_seed_nodes: int = 5) -> Dict[str, Any]:
        """Configure network bootstrapping.

        Args:
            num_seed_nodes: Number of seed nodes to configure.
        """
        self.phase = LaunchPhase.BOOTSTRAP

        active_seeds = self.seed_nodes[:num_seed_nodes]
        bootstrap_info = {
            "seed_nodes": active_seeds,
            "dns_seeds": [
                f"seed{n}.mybait.org" for n in range(1, num_seed_nodes + 1)
            ],
            "min_connections": 8,
            "max_connections": 50,
            "peer_discovery": "kademlia_dht",
            "network_magic": MAINNET_MAGIC.hex(),
        }

        logger.info(f"Network bootstrap: {len(active_seeds)} seed nodes configured")
        return bootstrap_info

    # ── 3. Launch Checklist ─────────────────────────────────────────────────

    def run_launch_checklist(self, **kwargs: Any) -> Dict[str, Any]:
        """Run final pre-launch verification checklist.

        Args:
            **kwargs: Dynamic checks passed from the running system.

        Returns:
            Checklist results with pass/fail per item.
        """
        self.phase = LaunchPhase.VALIDATION
        checks: List[Dict[str, Any]] = [
            {
                "id": "LC-001",
                "category": "Security",
                "description": "All L2 modules promoted to L1",
                "status": "pass" if kwargs.get("l2_promoted") else "fail",
                "required": True,
            },
            {
                "id": "LC-002",
                "category": "Security",
                "description": "Transaction signatures verified during block inclusion",
                "status": "pass" if kwargs.get("sig_verification") else "fail",
                "required": True,
            },
            {
                "id": "LC-003",
                "category": "Security",
                "description": "External security audit completed with no critical findings",
                "status": "pass" if kwargs.get("external_audit_clean") else "fail",
                "required": True,
            },
            {
                "id": "LC-004",
                "category": "Performance",
                "description": "Fee market operational",
                "status": "pass" if kwargs.get("fee_market") else "fail",
                "required": True,
            },
            {
                "id": "LC-005",
                "category": "Performance",
                "description": "Load tested at target TPS",
                "status": "pass" if kwargs.get("load_tested") else "fail",
                "required": True,
            },
            {
                "id": "LC-006",
                "category": "Performance",
                "description": "Mining difficulty provides meaningful security",
                "status": "pass" if kwargs.get("difficulty_ok") else "fail",
                "required": True,
            },
            {
                "id": "LC-007",
                "category": "Network",
                "description": "Public testnet running 30+ days with 5+ independent nodes",
                "status": "pass" if kwargs.get("testnet_stable") else "fail",
                "required": True,
            },
            {
                "id": "LC-008",
                "category": "Network",
                "description": "Smart contracts deployed and audited on testnet",
                "status": "pass" if kwargs.get("contracts_deployed") else "fail",
                "required": True,
            },
            {
                "id": "LC-009",
                "category": "Operations",
                "description": "Incident response runbooks written",
                "status": "pass" if len(self.runbooks) >= 5 else "fail",
                "required": True,
            },
            {
                "id": "LC-010",
                "category": "Operations",
                "description": "Address format unified across all modules",
                "status": "pass" if kwargs.get("address_unified") else "fail",
                "required": True,
            },
            {
                "id": "LC-011",
                "category": "Operations",
                "description": "Genesis block parameters configured",
                "status": "pass" if self.genesis_config else "fail",
                "required": True,
            },
            {
                "id": "LC-012",
                "category": "Operations",
                "description": "Seed nodes configured and reachable",
                "status": "pass" if len(self.seed_nodes) >= 5 else "fail",
                "required": True,
            },
        ]

        passed = all(c["status"] == "pass" for c in checks)
        result = {
            "timestamp": time.time(),
            "phase": self.phase.value,
            "checks": checks,
            "passed": passed,
            "pass_count": sum(1 for c in checks if c["status"] == "pass"),
            "fail_count": sum(1 for c in checks if c["status"] == "fail"),
            "total": len(checks),
        }

        logger.info(f"Launch checklist: {result['pass_count']}/{result['total']} passed")
        return result

    # ── 4. Go Live ───────────────────────────────────────────────────────────

    def go_live(self) -> Dict[str, Any]:
        """Transition to LIVE phase."""
        self.phase = LaunchPhase.LIVE
        self._launch_time = time.time()

        return {
            "status": "MAINNET_LIVE",
            "phase": self.phase.value,
            "launch_timestamp": self._launch_time,
            "genesis_config": self.genesis_config,
            "seed_nodes": self.seed_nodes,
            "message": "b'AI'tcoin mainnet is now live. Blocks are being produced every ~30 seconds.",
        }

    # ── 5. Health Monitoring ────────────────────────────────────────────────

    def start_monitoring(self) -> Dict[str, Any]:
        """Start the monitoring subsystem."""
        self.phase = LaunchPhase.MONITORING
        return {
            "status": "monitoring_active",
            "thresholds": HEALTH_THRESHOLDS,
            "runbooks_available": list(self.runbooks.keys()),
        }

    def record_block(self, block_time_s: float, tx_count: int) -> None:
        """Record a mined block for health tracking.

        Args:
            block_time_s: Time taken to mine this block.
            tx_count: Number of transactions in the block.
        """
        self._block_times.append(block_time_s)
        self._total_blocks_post_launch += 1
        self._total_txs_post_launch += tx_count
        # Keep only last 100 block times
        if len(self._block_times) > 100:
            self._block_times = self._block_times[-100:]

    def check_health(self, **metrics: Any) -> Dict[str, Any]:
        """Evaluate system health against thresholds.

        Args:
            **metrics: Current system metrics.
                - orphan_rate: float (0-1)
                - peer_count: int
                - block_propagation_s: float
                - mempool_size: int
                - uptime_pct: float

        Returns:
            Health report with metrics and any alerts.
        """
        health_report: Dict[str, Any] = {
            "timestamp": time.time(),
            "phase": self.phase.value,
            "metrics": [],
            "alerts": [],
            "overall_healthy": True,
        }

        # Check each metric
        metric_checks = [
            ("orphan_rate", metrics.get("orphan_rate", 0), HEALTH_THRESHOLDS["max_orphan_rate"], "rate"),
            ("peer_count", metrics.get("peer_count", 0), HEALTH_THRESHOLDS["min_peer_count"], "count", True),
            ("block_propagation_s", metrics.get("block_propagation_s", 0), HEALTH_THRESHOLDS["max_block_propagation_s"], "seconds"),
            ("mempool_size", metrics.get("mempool_size", 0), HEALTH_THRESHOLDS["max_mempool_size"], "count"),
        ]

        for name, value, threshold, unit, *invert in metric_checks:
            is_lower_bound = bool(invert and invert[0])
            healthy = (value >= threshold) if is_lower_bound else (value <= threshold)
            hm = HealthMetric(name=name, value=value, threshold=threshold, unit=unit, healthy=healthy)
            health_report["metrics"].append(hm.to_dict())
            self.health_metrics[name] = hm

            if not healthy:
                health_report["overall_healthy"] = False
                self._create_alert(name, value, threshold, is_lower_bound)

        health_report["alerts"] = [a.to_dict() for a in self.alerts[-10:]]
        return health_report

    def _create_alert(self, metric_name: str, value: float, threshold: float, is_lower_bound: bool) -> Alert:
        """Create a monitoring alert."""
        self._alert_counter += 1
        severity = "HIGH" if metric_name in ("orphan_rate", "consensus_failure") else "MEDIUM"
        direction = "below" if is_lower_bound else "exceeds"

        alert = Alert(
            alert_id=f"BAIT-ALERT-{self._alert_counter:05d}",
            severity=severity,
            metric_name=metric_name,
            message=f"{metric_name} ({value}) {direction} threshold ({threshold})",
            value=value,
            threshold=threshold,
            runbook=self._get_runbook_for_metric(metric_name),
        )
        self.alerts.append(alert)
        logger.warning(f"Alert {alert.alert_id}: {alert.message}")
        return alert

    def _get_runbook_for_metric(self, metric_name: str) -> str:
        """Find the appropriate runbook for a metric alert."""
        runbook_map = {
            "orphan_rate": "high_orphan_rate",
            "peer_count": "peer_disconnect",
            "block_propagation_s": "high_orphan_rate",
            "mempool_size": "mempool_bloat",
        }
        rb_type = runbook_map.get(metric_name, "")
        return rb_type

    # ── 6. Post-Launch KPIs ─────────────────────────────────────────────────

    def get_post_launch_kpis(self) -> Dict[str, Any]:
        """Get post-launch KPI metrics against Go Live criteria."""
        if not self._launch_time:
            return {"error": "Mainnet not yet launched"}

        elapsed_h = (time.time() - self._launch_time) / 3600
        avg_block_time = (sum(self._block_times) / len(self._block_times)) if self._block_times else 0
        tx_per_block = (self._total_txs_post_launch / self._total_blocks_post_launch) if self._total_blocks_post_launch > 0 else 0

        return {
            "uptime_hours": round(elapsed_h, 2),
            "total_blocks": self._total_blocks_post_launch,
            "total_transactions": self._total_txs_post_launch,
            "avg_block_time_s": round(avg_block_time, 2),
            "tx_per_block": round(tx_per_block, 2),
            "active_alerts": sum(1 for a in self.alerts if not a.resolved),
            "resolved_alerts": sum(1 for a in self.alerts if a.resolved),
            "go_live_criteria": {
                "blocks_every_30s": "PASS" if 25 <= avg_block_time <= 35 else "CHECK",
                "50_nodes_week1": "PENDING" if elapsed_h < 168 else "CHECK",
                "1000_tx_48h": "PASS" if self._total_txs_post_launch >= 1000 else "PENDING",
                "zero_critical_72h": "PASS" if not any(a.severity == "CRITICAL" and not a.resolved for a in self.alerts) else "FAIL",
            },
            "phase": self.phase.value,
        }

    # ── 7. Runbook Access ───────────────────────────────────────────────────

    def get_runbook(self, incident_type: str) -> Optional[Dict[str, Any]]:
        """Get incident response runbook by type."""
        rb = self.runbooks.get(incident_type)
        return rb.to_dict() if rb else None

    def list_runbooks(self) -> List[Dict[str, Any]]:
        """List all available incident runbooks."""
        return [rb.to_dict() for rb in self.runbooks.values()]

    # ── Status ──────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize launcher state."""
        return {
            "phase": self.phase.value,
            "genesis_configured": bool(self.genesis_config),
            "seed_nodes": len(self.seed_nodes),
            "active_alerts": sum(1 for a in self.alerts if not a.resolved),
            "total_alerts": len(self.alerts),
            "runbooks": len(self.runbooks),
            "launch_time": self._launch_time,
            "post_launch_kpis": self.get_post_launch_kpis() if self._launch_time else None,
        }
