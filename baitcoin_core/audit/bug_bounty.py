r"""
Bug Bounty Program Infrastructure -- Phase 21.

Provides the backend logic for the b'AI'tcoin bug bounty program including:

1. **Severity-based reward tiers** -- Critical/High/Medium/Low with BAIT payouts
2. **Submission intake** -- Structured vulnerability reports with evidence
3. **Triaging engine** -- Automated severity classification + duplicate detection
4. **Leaderboard** -- Hunter rankings by resolved reports
5. **Program policy** -- Scope, rules, response SLA, safe harbor
6. **REST API integration** -- Endpoints for submission, status, leaderboard

Reward Table (BAIT):
    CRITICAL: 50,000 BAIT ($50-500 range at launch)
    HIGH:     10,000 BAIT
    MEDIUM:    2,000 BAIT
    LOW:        500 BAIT
    INFO:       100 BAIT (acknowledgment only)

Response SLA:
    CRITICAL: 4 hours acknowledgment, 48 hours triage
    HIGH:     24 hours acknowledgment, 72 hours triage
    MEDIUM:   48 hours acknowledgment, 1 week triage
    LOW:      1 week acknowledgment, 2 weeks triage

Usage::

    from baitcoin_core.audit.bug_bounty import BugBountyManager

    bounty = BugBountyManager()
    report = bounty.submit(
        hunter="security_researcher_01",
        title="Replay attack on transaction signing",
        severity="HIGH",
        description="Transactions can be replayed because...",
        evidence={"poc": "...", "steps": [...]},
        affected_components=["baitcoin_wallet", "baitcoin_api"],
    )
    print(bounty.get_leaderboard())

"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ── Reward Table ────────────────────────────────────────────────────────────

REWARD_TABLE: Dict[str, int] = {
    "CRITICAL": 50_000,
    "HIGH": 10_000,
    "MEDIUM": 2_000,
    "LOW": 500,
    "INFO": 100,
}

# ── Response SLA (seconds) ─────────────────────────────────────────────────

RESPONSE_SLA: Dict[str, Dict[str, int]] = {
    "CRITICAL": {"ack": 4 * 3600, "triage": 48 * 3600},
    "HIGH": {"ack": 24 * 3600, "triage": 72 * 3600},
    "MEDIUM": {"ack": 48 * 3600, "triage": 7 * 24 * 3600},
    "LOW": {"ack": 7 * 24 * 3600, "triage": 14 * 24 * 3600},
    "INFO": {"ack": 7 * 24 * 3600, "triage": 14 * 24 * 3600},
}

# ── Scope definition ───────────────────────────────────────────────────────

IN_SCOPE: List[Dict[str, str]] = [
    {"component": "baitcoin_core", "description": "Blockchain, consensus (zkML), cryptography (Schnorr), P2P network"},
    {"component": "baitcoin_token", "description": "BAIT token, tokenomics, halving schedule, governance"},
    {"component": "baitcoin_bank", "description": "Staking, lending, vaults (DeFi primitives)"},
    {"component": "baitcoin_ai", "description": "Agent protocol, marketplace, oracle price feeds"},
    {"component": "baitcoin_wallet", "description": "Key management, transaction signing, paper wallet"},
    {"component": "baitcoin_api", "description": "REST API server, authentication, rate limiting"},
    {"component": "baitcoin_explorer", "description": "Blockch'AI'in explorer, search, analytics"},
    {"component": "baitcoin_memory", "description": "WAL persistence, snapshots, state recovery"},
    {"component": "baitcoin_bridge", "description": "Cross-chain bridge logic, Merkle proofs, AMM pool"},
    {"component": "baitcoin_sdk", "description": "Client SDK, mobile SDK, wallet SDK"},
    {"component": "smart_contracts", "description": "Contract VM engine, anchor contracts, relayer"},
]

OUT_OF_SCOPE: List[str] = [
    "Social engineering attacks",
    "Physical attacks on infrastructure",
    "Denial of service (rate limiting is in scope)",
    "Third-party services (HostGator, GitHub, DNS providers)",
    "Information disclosure through public GitHub repos (known limitation)",
    "Issues already reported or known",
]


class ReportStatus(str, Enum):
    """Lifecycle of a bug bounty report."""
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    TRIAGING = "triaging"
    CONFIRMED = "confirmed"
    FIXING = "fixing"
    FIXED = "fixed"
    DUPLICATE = "duplicate"
    NOT_APPLICABLE = "not_applicable"
    REWARDED = "rewarded"
    CLOSED = "closed"


class ReportSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class BugBountyReport:
    """A single vulnerability report submitted by a bug bounty hunter."""
    report_id: str
    hunter: str
    title: str
    severity: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    affected_components: List[str] = field(default_factory=list)
    status: str = ReportStatus.SUBMITTED.value
    reward_bait: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    acknowledged_at: Optional[float] = None
    triaged_at: Optional[float] = None
    fixed_at: Optional[float] = None
    rewarded_at: Optional[float] = None
    duplicate_of: str = ""
    internal_notes: str = ""
    assignee: str = ""

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.updated_at == 0.0:
            self.updated_at = self.created_at

    @property
    def fingerprint(self) -> str:
        """Content-based fingerprint for duplicate detection."""
        content = f"{self.title}|{self.severity}|{'|'.join(sorted(self.affected_components))}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @property
    def is_sla_breached(self) -> Dict[str, bool]:
        """Check if response SLA is breached."""
        now = time.time()
        sla = RESPONSE_SLA.get(self.severity, RESPONSE_SLA["MEDIUM"])
        breached = {}
        if self.acknowledged_at is None:
            breached["ack"] = (now - self.created_at) > sla["ack"]
        else:
            breached["ack"] = (self.acknowledged_at - self.created_at) > sla["ack"]
        if self.triaged_at is None and self.status in (ReportStatus.SUBMITTED.value, ReportStatus.ACKNOWLEDGED.value):
            breached["triage"] = (now - self.created_at) > sla["triage"]
        elif self.triaged_at is not None:
            breached["triage"] = (self.triaged_at - self.created_at) > sla["triage"]
        else:
            breached["triage"] = False
        return breached

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "hunter": self.hunter,
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "affected_components": self.affected_components,
            "status": self.status,
            "reward_bait": self.reward_bait,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "acknowledged_at": self.acknowledged_at,
            "triaged_at": self.triaged_at,
            "fixed_at": self.fixed_at,
            "rewarded_at": self.rewarded_at,
            "duplicate_of": self.duplicate_of,
            "fingerprint": self.fingerprint,
            "sla_breached": self.is_sla_breached,
            "assignee": self.assignee,
        }


@dataclass
class HunterProfile:
    """A bug bounty hunter's profile and stats."""
    hunter_id: str
    display_name: str = ""
    total_reports: int = 0
    total_rewards_bait: int = 0
    confirmed_reports: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    joined_at: float = 0.0
    is_verified: bool = False

    def __post_init__(self):
        if self.joined_at == 0.0:
            self.joined_at = time.time()
        if not self.display_name:
            self.display_name = self.hunter_id

    @property
    def rank_points(self) -> int:
        """Calculate leaderboard ranking points."""
        return (
            self.critical_count * 100
            + self.high_count * 25
            + self.medium_count * 5
            + self.low_count * 1
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hunter_id": self.hunter_id,
            "display_name": self.display_name,
            "total_reports": self.total_reports,
            "total_rewards_bait": self.total_rewards_bait,
            "confirmed_reports": self.confirmed_reports,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "rank_points": self.rank_points,
            "joined_at": self.joined_at,
            "is_verified": self.is_verified,
        }


class BugBountyManager:
    """Manages the b'AI'tcoin bug bounty program.

    Handles report submission, triaging, rewarding, and leaderboard.
    All state is in-memory (persist to WAL via daemon integration).
    """

    def __init__(self, max_bounty_pool: int = 2_100_000):
        """Initialize the bug bounty manager.

        Args:
            max_bounty_pool: Maximum total BAIT allocated for bounties (10% of supply = 2.1M).
        """
        self.max_bounty_pool = max_bounty_pool
        self.reports: Dict[str, BugBountyReport] = {}
        self.hunters: Dict[str, HunterProfile] = {}
        self.total_rewards_paid: int = 0
        self._report_counter: int = 0
        self._fingerprints_seen: Set[str] = set()

    # ── Submission ────────────────────────────────────────────────────────────

    def submit(
        self,
        hunter: str,
        title: str,
        severity: str,
        description: str,
        evidence: Optional[Dict[str, Any]] = None,
        affected_components: Optional[List[str]] = None,
    ) -> BugBountyReport:
        """Submit a new vulnerability report.

        Args:
            hunter: Hunter identifier.
            title: Short title of the vulnerability.
            severity: CRITICAL, HIGH, MEDIUM, LOW, or INFO.
            description: Detailed description of the vulnerability.
            evidence: Optional dict with PoC, screenshots, steps to reproduce.
            affected_components: List of affected module names.

        Returns:
            The created BugBountyReport.
        """
        self._report_counter += 1
        report_id = f"BAIT-BUG-{self._report_counter:05d}"

        # Validate severity
        sev = severity.upper()
        if sev not in ReportSeverity.__members__:
            sev = "MEDIUM"

        report = BugBountyReport(
            report_id=report_id,
            hunter=hunter,
            title=title,
            severity=sev,
            description=description,
            evidence=evidence or {},
            affected_components=affected_components or [],
        )

        # Track fingerprint for duplicate detection
        self._fingerprints_seen.add(report.fingerprint)

        # Store
        self.reports[report_id] = report

        # Update hunter profile
        if hunter not in self.hunters:
            self.hunters[hunter] = HunterProfile(hunter_id=hunter)
        self.hunters[hunter].total_reports += 1

        # Auto-acknowledge if within SLA
        self._auto_acknowledge(report)

        logger.info(f"Bug bounty report {report_id} submitted by {hunter}: [{sev}] {title}")
        return report

    def _auto_acknowledge(self, report: BugBountyReport) -> None:
        """Auto-acknowledge reports within SLA."""
        report.acknowledged_at = time.time()
        report.status = ReportStatus.ACKNOWLEDGED.value
        report.updated_at = time.time()

    # ── Triaging ──────────────────────────────────────────────────────────────

    def check_duplicate(self, report_id: str) -> Optional[str]:
        """Check if a report is a duplicate of an existing one.

        Returns the ID of the original report if duplicate, None otherwise.
        """
        report = self.reports.get(report_id)
        if not report:
            return None

        for existing_id, existing in self.reports.items():
            if existing_id == report_id:
                continue
            if existing.fingerprint == report.fingerprint:
                return existing_id
        return None

    def triage(self, report_id: str, action: str, assignee: str = "", notes: str = "") -> BugBountyReport:
        """Triaging a report: confirm, mark duplicate, or reject.

        Args:
            report_id: The report to triage.
            action: One of 'confirm', 'duplicate', 'reject'.
            assignee: Optional assignee for confirmed reports.
            notes: Internal notes.

        Returns:
            The updated report.
        """
        report = self.reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        report.updated_at = time.time()
        report.triaged_at = time.time()
        report.internal_notes = notes
        report.assignee = assignee

        if action == "confirm":
            report.status = ReportStatus.CONFIRMED.value
        elif action == "duplicate":
            dup_id = self.check_duplicate(report_id)
            report.status = ReportStatus.DUPLICATE.value
            report.duplicate_of = dup_id or "unknown"
        elif action == "reject":
            report.status = ReportStatus.NOT_APPLICABLE.value
        else:
            raise ValueError(f"Unknown triage action: {action}")

        logger.info(f"Report {report_id} triaged: {action} by {assignee}")
        return report

    # ── Resolution & Rewards ─────────────────────────────────────────────────

    def mark_fixing(self, report_id: str) -> BugBountyReport:
        """Mark a confirmed report as being fixed."""
        report = self._get_report(report_id)
        report.status = ReportStatus.FIXING.value
        report.updated_at = time.time()
        return report

    def mark_fixed(self, report_id: str, fix_hash: str = "") -> BugBountyReport:
        """Mark a report as fixed with optional commit hash."""
        report = self._get_report(report_id)
        report.status = ReportStatus.FIXED.value
        report.fixed_at = time.time()
        report.updated_at = time.time()
        if fix_hash:
            report.internal_notes += f"\nFix commit: {fix_hash}"
        return report

    def reward(self, report_id: str, bonus_bait: int = 0) -> BugBountyReport:
        """Issue bounty reward for a fixed report.

        Args:
            report_id: The fixed report to reward.
            bonus_bait: Additional bonus BAIT on top of severity base.

        Returns:
            The updated report with reward.
        """
        report = self._get_report(report_id)
        if report.status not in (ReportStatus.FIXED.value, ReportStatus.CONFIRMED.value):
            raise ValueError(f"Cannot reward report in status: {report.status}")

        base_reward = REWARD_TABLE.get(report.severity, 0)
        # Deduplicate reward: if this is a duplicate, no reward
        if report.status == ReportStatus.DUPLICATE.value:
            report.reward_bait = 0
        else:
            report.reward_bait = base_reward + bonus_bait

        # Check pool limit
        if self.total_rewards_paid + report.reward_bait > self.max_bounty_pool:
            logger.warning(f"Bounty pool exhausted! Cannot pay {report.reward_bait} BAIT")
            report.reward_bait = 0
        else:
            self.total_rewards_paid += report.reward_bait

        report.rewarded_at = time.time()
        report.status = ReportStatus.REWARDED.value
        report.updated_at = time.time()

        # Update hunter stats
        hunter = self.hunters.get(report.hunter)
        if hunter:
            hunter.total_rewards_bait += report.reward_bait
            hunter.confirmed_reports += 1
            if report.severity == "CRITICAL":
                hunter.critical_count += 1
            elif report.severity == "HIGH":
                hunter.high_count += 1
            elif report.severity == "MEDIUM":
                hunter.medium_count += 1
            elif report.severity == "LOW":
                hunter.low_count += 1

        logger.info(f"Report {report_id} rewarded: {report.reward_bait} BAIT to {report.hunter}")
        return report

    # ── Queries ──────────────────────────────────────────────────────────────

    def _get_report(self, report_id: str) -> BugBountyReport:
        report = self.reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        return report

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a report by ID."""
        report = self.reports.get(report_id)
        return report.to_dict() if report else None

    def list_reports(
        self,
        hunter: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List reports with optional filters."""
        results = []
        for report in self.reports.values():
            if hunter and report.hunter != hunter:
                continue
            if severity and report.severity != severity.upper():
                continue
            if status and report.status != status:
                continue
            results.append(report.to_dict())
        # Sort by created_at descending
        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results[offset:offset + limit]

    def get_leaderboard(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get hunter leaderboard sorted by rank points."""
        hunters = sorted(
            [h.to_dict() for h in self.hunters.values()],
            key=lambda x: x["rank_points"],
            reverse=True,
        )
        return hunters[:limit]

    # ── Program Info ─────────────────────────────────────────────────────────

    def get_program_info(self) -> Dict[str, Any]:
        """Get bug bounty program information."""
        severity_breakdown = {s: 0 for s in ReportSeverity}
        status_breakdown = {s.value: 0 for s in ReportStatus}
        for report in self.reports.values():
            if report.severity in severity_breakdown:
                severity_breakdown[report.severity] += 1
            if report.status in status_breakdown:
                status_breakdown[report.status] += 1

        return {
            "program_name": "b'AI'tcoin Bug Bounty Program",
            "version": "1.0.0",
            "reward_currency": "BAIT",
            "reward_table": REWARD_TABLE,
            "response_sla_hours": {
                k: {kk: vv // 3600 for kk, vv in v.items()}
                for k, v in RESPONSE_SLA.items()
            },
            "max_bounty_pool": self.max_bounty_pool,
            "total_rewards_paid": self.total_rewards_paid,
            "remaining_pool": self.max_bounty_pool - self.total_rewards_paid,
            "total_reports": len(self.reports),
            "total_hunters": len(self.hunters),
            "severity_breakdown": severity_breakdown,
            "status_breakdown": status_breakdown,
            "in_scope": IN_SCOPE,
            "out_of_scope": OUT_OF_SCOPE,
            "safe_harbor": (
                "b'AI'tcoin commits to safe harbor for good-faith security research. "
                "We will not pursue legal action against researchers who follow our rules. "
                "Reports must be submitted through official channels before any public disclosure."
            ),
            "submission_url": "https://www.mybait.org/api/api/v1/bug-bounty/submit",
            "leaderboard_url": "https://www.mybait.org/api/api/v1/bug-bounty/leaderboard",
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manager state."""
        return {
            "total_reports": len(self.reports),
            "total_hunters": len(self.hunters),
            "total_rewards_paid": self.total_rewards_paid,
            "remaining_pool": self.max_bounty_pool - self.total_rewards_paid,
            "max_bounty_pool": self.max_bounty_pool,
        }
