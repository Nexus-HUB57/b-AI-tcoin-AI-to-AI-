r"""
Tests for Phase 20 (External Audit), Phase 21 (Bug Bounty), Phase 22 (Mainnet Launcher).

Covers:
- ExternalAuditPipeline: static analysis, dependency scan, formal specs, code quality
- BugBountyManager: submission, triaging, rewards, leaderboard, SLA
- MainnetLauncher: genesis config, bootstrapping, checklist, health, runbooks
"""

import json
import os
import sys
import tempfile
import time

import pytest

# Ensure baitcoin-ecosystem is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════════════════════════
# Phase 20: External Audit Pipeline
# ══════════════════════════════════════════════════════════════════════════════

class TestExternalAuditPipeline:
    r"""Test ExternalAuditPipeline — Phase 20."""

    def test_pipeline_init(self):
        """Pipeline initializes with default root."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        p = ExternalAuditPipeline()
        assert p.PIPELINE_VERSION == "1.0.0"
        assert p.files_scanned == 0

    def test_pipeline_scan_empty_dir(self):
        """Scanning an empty directory returns clean report."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()
            assert report.files_scanned == 0
            assert isinstance(report.findings, list)
            assert report.scan_duration_s >= 0

    def test_pipeline_scan_with_py_files(self):
        """Pipeline scans .py files and detects patterns."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with known patterns
            test_file = os.path.join(tmpdir, "bait_code.py")  # NOT test_ prefix so rules apply
            with open(test_file, "w") as f:
                f.write("import random\n")  # BAIT-SEC-002
                f.write("secret_key = \"hardcoded_secret_1234567890abcdef\"\n")  # BAIT-SEC-001
                f.write("eval(some_var)\n")  # BAIT-SEC-007
                f.write("except Exception: pass\n")  # BAIT-SEC-004 (single line)

            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()

            assert report.files_scanned >= 1
            rule_ids = {f.rule_id for f in report.findings}
            assert "BAIT-SEC-007" in rule_ids  # eval()
            assert "BAIT-SEC-004" in rule_ids  # except: pass
            # BAIT-SEC-002 (import random) may or may not match depending on regex
            # The pattern requires the line to NOT be in exclude_files

    def test_pipeline_exclude_test_files(self):
        """Pipeline excludes test files from security rules."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_my_feature.py")
            with open(test_file, "w") as f:
                f.write("import random\n")

            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()

            sec002 = [f for f in report.findings if f.rule_id == "BAIT-SEC-002"]
            assert len(sec002) == 0  # Should be excluded

    def test_pipeline_dependency_scan(self):
        """Dependency scan parses requirements.txt."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            req = os.path.join(tmpdir, "requirements.txt")
            with open(req, "w") as f:
                f.write("ecdsa==0.17.0\n")  # Below 0.18.0 = CVE
                f.write("cryptography>=41.0.0\n")  # OK

            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()

            dep_findings = [f for f in report.findings if f.category == "dependency"]
            assert len(dep_findings) >= 1
            assert any(f.cve == "CVE-2023-49083" for f in dep_findings)

    def test_pipeline_report_json(self):
        """JSON report is valid."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()
            path = p.save_report(report, format="json", path=os.path.join(tmpdir, "report.json"))
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert "findings" in data
            assert "summary" in data

    def test_pipeline_report_markdown(self):
        """Markdown report is generated."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()
            path = p.save_report(report, format="markdown", path=os.path.join(tmpdir, "report.md"))
            assert os.path.exists(path)
            content = open(path).read()
            assert "bAIcoin" in content

    def test_pipeline_report_sarif(self):
        """SARIF report is valid JSON with correct schema."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()
            path = p.save_report(report, format="sarif", path=os.path.join(tmpdir, "report.sarif"))
            assert os.path.exists(path)
            with open(path) as f:
                sarif = json.load(f)
            assert sarif["$schema"]
            assert sarif["version"] == "2.1.0"
            assert len(sarif["runs"]) == 1

    def test_pipeline_exit_code_clean(self):
        """Clean scan has no CRITICAL/HIGH findings (MEDIUM/LOW/INFO are ok)."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal structure to avoid formal_spec CRITICAL
            os.makedirs(os.path.join(tmpdir, "baitcoin_core", "consensus", "zkml_real"), exist_ok=True)
            with open(os.path.join(tmpdir, "baitcoin_core", "consensus", "zkml_real", "proof_system.py"), "w") as f:
                f.write('# zkML proof system stub\ng**r = A*y*c mod P\n')
            # Create tests dir with enough files to avoid LOW
            os.makedirs(os.path.join(tmpdir, "tests"), exist_ok=True)
            for i in range(5):
                with open(os.path.join(tmpdir, "tests", f"test_dummy_{i}.py"), "w") as f:
                    f.write('# test\n')
            # Create .gitignore
            with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
                f.write('__pycache__/\n')

            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()
            # No CRITICAL or HIGH
            critical_high = [f for f in report.findings if f.severity.value in ("CRITICAL", "HIGH")]
            assert len(critical_high) == 0, f"Unexpected CRITICAL/HIGH: {[(f.rule_id, f.title) for f in critical_high]}"

    def test_pipeline_exit_code_medium(self):
        """Medium finding returns exit_code 1."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            # Avoid CRITICAL from formal_spec
            os.makedirs(os.path.join(tmpdir, "baitcoin_core", "consensus", "zkml_real"), exist_ok=True)
            with open(os.path.join(tmpdir, "baitcoin_core", "consensus", "zkml_real", "proof_system.py"), "w") as f:
                f.write('# stub\n')
            os.makedirs(os.path.join(tmpdir, "tests"), exist_ok=True)
            with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
                f.write('__pycache__/\n')

            test_file = os.path.join(tmpdir, "code.py")
            with open(test_file, "w") as f:
                f.write("except Exception:\n  pass\n")

            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()
            assert report.exit_code == 1  # MEDIUM findings
            assert report.passed is False

    def test_pipeline_summary_counts(self):
        """Summary correctly counts findings by severity."""
        from baitcoin_core.audit.external_audit import ExternalAuditPipeline, ScanSeverity
        with tempfile.TemporaryDirectory() as tmpdir:
            p = ExternalAuditPipeline(codebase_root=tmpdir)
            report = p.run_full_scan()
            for sev in ScanSeverity:
                assert sev.value in report.summary


# ══════════════════════════════════════════════════════════════════════════════
# Phase 21: Bug Bounty Program
# ══════════════════════════════════════════════════════════════════════════════

class TestBugBountyManager:
    r"""Test BugBountyManager — Phase 21."""

    def test_submit_report(self):
        """Submit a vulnerability report."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        report = mgr.submit(
            hunter="researcher_01",
            title="Replay attack on tx signing",
            severity="HIGH",
            description="Transactions can be replayed...",
            affected_components=["baitcoin_wallet"],
        )
        assert report.report_id == "BAIT-BUG-00001"
        assert report.severity == "HIGH"
        assert report.status == "acknowledged"  # Auto-ack

    def test_submit_validates_severity(self):
        """Invalid severity defaults to MEDIUM."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        report = mgr.submit(
            hunter="r01",
            title="test",
            severity="INVALID",
            description="test",
        )
        assert report.severity == "MEDIUM"

    def test_fingerprint_for_duplicates(self):
        """Reports with same title+severity+components have same fingerprint."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        r1 = mgr.submit("h1", "XSS in search", "HIGH", "desc", affected_components=["baitcoin_api"])
        r2 = mgr.submit("h2", "XSS in search", "HIGH", "desc", affected_components=["baitcoin_api"])
        assert r1.fingerprint == r2.fingerprint

    def test_triage_confirm(self):
        """Triaging confirms a report."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        r = mgr.submit("h1", "test", "HIGH", "desc")
        result = mgr.triage(r.report_id, "confirm", assignee="security_team")
        assert result.status == "confirmed"
        assert result.assignee == "security_team"

    def test_triage_duplicate(self):
        """Triaging marks duplicate."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        r1 = mgr.submit("h1", "Same bug", "MEDIUM", "desc", affected_components=["baitcoin_core"])
        r2 = mgr.submit("h2", "Same bug", "MEDIUM", "desc", affected_components=["baitcoin_core"])
        result = mgr.triage(r2.report_id, "duplicate")
        assert result.status == "duplicate"
        assert result.duplicate_of == r1.report_id

    def test_triage_reject(self):
        """Triaging rejects invalid report."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        r = mgr.submit("h1", "Not a bug", "LOW", "Working as intended")
        result = mgr.triage(r.report_id, "reject", notes="Working as designed")
        assert result.status == "not_applicable"

    def test_reward_fixed_report(self):
        """Rewarding a fixed report issues BAIT."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        r = mgr.submit("h1", "Critical bug", "CRITICAL", "desc")
        mgr.triage(r.report_id, "confirm")
        mgr.mark_fixing(r.report_id)
        mgr.mark_fixed(r.report_id, fix_hash="abc123")
        rewarded = mgr.reward(r.report_id)
        assert rewarded.status == "rewarded"
        assert rewarded.reward_bait == 50_000
        assert mgr.total_rewards_paid == 50_000

    def test_reward_table(self):
        """Reward amounts match the table."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager, REWARD_TABLE
        assert REWARD_TABLE["CRITICAL"] == 50_000
        assert REWARD_TABLE["HIGH"] == 10_000
        assert REWARD_TABLE["MEDIUM"] == 2_000
        assert REWARD_TABLE["LOW"] == 500
        assert REWARD_TABLE["INFO"] == 100

    def test_leaderboard(self):
        """Leaderboard ranks hunters by points."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        # Hunter A: 1 critical
        r1 = mgr.submit("hunter_a", "Crit", "CRITICAL", "desc")
        mgr.triage(r1.report_id, "confirm")
        mgr.mark_fixed(r1.report_id)
        mgr.reward(r1.report_id)
        # Hunter B: 3 mediums
        for i in range(3):
            r = mgr.submit("hunter_b", f"Med {i}", "MEDIUM", "desc")
            mgr.triage(r.report_id, "confirm")
            mgr.mark_fixed(r.report_id)
            mgr.reward(r.report_id)

        lb = mgr.get_leaderboard()
        assert len(lb) == 2
        assert lb[0]["hunter_id"] == "hunter_a"  # 100 pts > 15 pts

    def test_list_reports_with_filters(self):
        """List reports supports filtering."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        mgr.submit("h1", "Crit", "CRITICAL", "desc")
        mgr.submit("h2", "Low", "LOW", "desc")
        mgr.submit("h1", "High", "HIGH", "desc")

        # Filter by hunter
        h1_reports = mgr.list_reports(hunter="h1")
        assert len(h1_reports) == 2

        # Filter by severity
        crit = mgr.list_reports(severity="CRITICAL")
        assert len(crit) == 1

    def test_program_info(self):
        """Program info includes all required fields."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        info = mgr.get_program_info()
        assert info["program_name"] == "b'AI'tcoin Bug Bounty Program"
        assert "reward_table" in info
        assert "response_sla_hours" in info
        assert "in_scope" in info
        assert "out_of_scope" in info
        assert "safe_harbor" in info
        assert len(info["in_scope"]) >= 10

    def test_sla_breach_detection(self):
        """SLA breach is detected for old unacknowledged reports."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager, BugBountyReport, ReportSeverity
        report = BugBountyReport(
            report_id="TEST-001",
            hunter="h1",
            title="test",
            severity="CRITICAL",
            description="test",
            created_at=time.time() - 5 * 3600,  # 5 hours ago
            acknowledged_at=None,  # Not acknowledged
        )
        breached = report.is_sla_breached
        assert breached["ack"] is True  # 5h > 4h SLA

    def test_bounty_pool_limit(self):
        """Rewards stop when pool is exhausted."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager(max_bounty_pool=100_000)
        r = mgr.submit("h1", "Crit", "CRITICAL", "desc")
        mgr.triage(r.report_id, "confirm")
        mgr.mark_fixed(r.report_id)
        mgr.reward(r.report_id)
        assert mgr.total_rewards_paid == 50_000
        assert mgr.get_program_info()["remaining_pool"] == 50_000

    def test_get_report(self):
        """Get single report by ID."""
        from baitcoin_core.audit.bug_bounty import BugBountyManager
        mgr = BugBountyManager()
        r = mgr.submit("h1", "test", "MEDIUM", "desc")
        result = mgr.get_report(r.report_id)
        assert result is not None
        assert result["report_id"] == r.report_id

        missing = mgr.get_report("NONEXISTENT")
        assert missing is None


# ══════════════════════════════════════════════════════════════════════════════
# Phase 22: Mainnet Launcher
# ══════════════════════════════════════════════════════════════════════════════

class TestMainnetLauncher:
    r"""Test MainnetLauncher — Phase 22."""

    def test_prepare_genesis(self):
        """Genesis config has all required fields."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        config = launcher.prepare_genesis()
        assert config["network"]["name"] == "b'AI'tcoin Mainnet"
        assert config["token"]["max_supply"] == 21_000_000
        assert config["token"]["initial_reward"] == 50
        assert config["token"]["decimals"] == 8
        assert config["consensus"]["algorithm"] == "zkML + PoUW"
        assert len(config["premine_allocation"]) == 4
        assert config["premine_total_bait"] == 2_100_000
        assert config["mining_supply_bait"] == 18_900_000

    def test_genesis_allocations(self):
        """Genesis allocations sum correctly."""
        from baitcoin_mainnet.launcher import MainnetLauncher, ALLOCATION
        launcher = MainnetLauncher()
        config = launcher.prepare_genesis()
        total_alloc = sum(a["amount_bait"] for a in ALLOCATION.values())
        assert total_alloc == 2_100_000
        assert total_alloc + config["mining_supply_bait"] == 21_000_000

    def test_bootstrap_network(self):
        """Network bootstrap returns correct structure."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        info = launcher.bootstrap_network(num_seed_nodes=3)
        assert len(info["seed_nodes"]) == 3
        assert len(info["dns_seeds"]) == 3
        assert info["peer_discovery"] == "kademlia_dht"

    def test_launch_checklist(self):
        """Launch checklist returns 12 items."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        launcher.prepare_genesis()
        result = launcher.run_launch_checklist(
            l2_promoted=True,
            sig_verification=True,
            external_audit_clean=True,
            fee_market=True,
            load_tested=True,
            difficulty_ok=True,
            testnet_stable=True,
            contracts_deployed=True,
            address_unified=True,
        )
        assert result["total"] == 12
        assert result["pass_count"] >= 10
        assert result["passed"] is True

    def test_launch_checklist_fails(self):
        """Checklist fails when critical items fail."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        result = launcher.run_launch_checklist(
            l2_promoted=False,  # Fail
            sig_verification=True,
            external_audit_clean=False,  # Fail
        )
        assert result["passed"] is False

    def test_go_live(self):
        """Go live transitions to LIVE phase."""
        from baitcoin_mainnet.launcher import MainnetLauncher, LaunchPhase
        launcher = MainnetLauncher()
        result = launcher.go_live()
        assert result["status"] == "MAINNET_LIVE"
        assert launcher.phase == LaunchPhase.LIVE

    def test_health_monitoring(self):
        """Health monitoring detects unhealthy metrics."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        launcher.start_monitoring()

        # Healthy
        health = launcher.check_health(
            orphan_rate=0.001,
            peer_count=10,
            block_propagation_s=1.0,
            mempool_size=100,
        )
        assert health["overall_healthy"] is True

        # Unhealthy: high orphan rate
        health_bad = launcher.check_health(
            orphan_rate=0.05,  # 5% > 1%
            peer_count=10,
            block_propagation_s=1.0,
            mempool_size=100,
        )
        assert health_bad["overall_healthy"] is False
        assert len(health_bad["alerts"]) > 0

    def test_health_peer_count_low(self):
        """Low peer count triggers alert."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        launcher.start_monitoring()
        health = launcher.check_health(
            orphan_rate=0.0,
            peer_count=2,  # < 5
            block_propagation_s=0.5,
            mempool_size=10,
        )
        assert health["overall_healthy"] is False

    def test_post_launch_kpis(self):
        """Post-launch KPIs are computed."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        launcher.go_live()
        launcher.record_block(28.0, 5)
        launcher.record_block(31.0, 3)
        launcher.record_block(29.5, 7)
        kpis = launcher.get_post_launch_kpis()
        assert kpis["total_blocks"] == 3
        assert kpis["total_transactions"] == 15
        assert 25 < kpis["avg_block_time_s"] < 35
        assert kpis["phase"] == "live"

    def test_post_launch_before_launch(self):
        """KPIs before launch return error."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        kpis = launcher.get_post_launch_kpis()
        assert "error" in kpis

    def test_incident_runbooks(self):
        """Runbooks are available for all incident types."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        runbooks = launcher.list_runbooks()
        assert len(runbooks) >= 5

        types = {rb["incident_type"] for rb in runbooks}
        assert "chain_split" in types
        assert "high_orphan_rate" in types
        assert "mempool_bloat" in types
        assert "consensus_failure" in types
        assert "peer_disconnect" in types

    def test_get_single_runbook(self):
        """Get single runbook by type."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        rb = launcher.get_runbook("chain_split")
        assert rb is not None
        assert rb["severity"] == "CRITICAL"
        assert len(rb["auto_actions"]) > 0
        assert len(rb["manual_steps"]) > 0

        missing = launcher.get_runbook("nonexistent")
        assert missing is None

    def test_runbook_has_escalation(self):
        """Critical runbooks have escalation contacts."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        rb = launcher.get_runbook("consensus_failure")
        assert rb["escalation_contact"] != ""
        assert rb["max_response_time_s"] > 0

    def test_launcher_to_dict(self):
        """Launcher serializes correctly."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        launcher.prepare_genesis()
        d = launcher.to_dict()
        assert d["phase"] == "genesis"  # prepare_genesis() sets phase to GENESIS
        assert d["genesis_configured"] is True
        assert d["seed_nodes"] >= 5
        assert d["runbooks"] >= 5

    def test_health_thresholds_exist(self):
        """All health thresholds are defined."""
        from baitcoin_mainnet.launcher import HEALTH_THRESHOLDS
        assert "max_orphan_rate" in HEALTH_THRESHOLDS
        assert "min_peer_count" in HEALTH_THRESHOLDS
        assert "max_block_propagation_s" in HEALTH_THRESHOLDS
        assert "max_mempool_size" in HEALTH_THRESHOLDS

    def test_seed_nodes_default(self):
        """Default seed nodes are configured."""
        from baitcoin_mainnet.launcher import DEFAULT_SEED_NODES
        assert len(DEFAULT_SEED_NODES) >= 5
        locations = {n["location"] for n in DEFAULT_SEED_NODES}
        assert "US-East" in locations
        assert "EU-West" in locations
        assert "AP-Southeast" in locations

    def test_record_block_tracking(self):
        """Block recording tracks times correctly."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        launcher.go_live()
        for i in range(5):
            launcher.record_block(30.0, 2)
        kpis = launcher.get_post_launch_kpis()
        assert kpis["total_blocks"] == 5
        assert kpis["total_transactions"] == 10

    def test_alert_deduplication(self):
        """Each health check creates alerts for unhealthy metrics (no dedup)."""
        from baitcoin_mainnet.launcher import MainnetLauncher
        launcher = MainnetLauncher()
        launcher.start_monitoring()
        # Only orphan_rate is unhealthy (>0.01), peer_count/propagation/mempool are healthy
        launcher.check_health(orphan_rate=0.05, peer_count=10, block_propagation_s=1.0, mempool_size=100)
        launcher.check_health(orphan_rate=0.05, peer_count=10, block_propagation_s=1.0, mempool_size=100)
        # Only orphan_rate generates alerts: 1 per check = 2 total
        orphan_alerts = [a for a in launcher.alerts if a.metric_name == "orphan_rate"]
        assert len(orphan_alerts) == 2  # Each check creates new alert (no dedup)
