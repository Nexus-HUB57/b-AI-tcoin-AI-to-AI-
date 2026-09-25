"""Tests E2E para o A2A Compliance Orchestrator.

Audit 2026-09-22 — P3 item 3 (suite de testes E2E).
"""
import json
import os
import re
import tempfile
from pathlib import Path

import pytest

from a2a_compliance.orchestrator import (
    A2AComplianceOrchestrator,
    ComplianceError,
)
from a2a_compliance.schemas import (
    AgentAuditReport,
    ConsolidatedComplianceReport,
)


@pytest.fixture
def tmp_dirs():
    """Fixture: diretórios temporários isolados por teste."""
    with tempfile.TemporaryDirectory() as d:
        reports = Path(d) / "reports"
        log = Path(d) / "hashes.json"
        yield reports, log


def test_orchestrator_init_creates_dirs(tmp_dirs):
    reports, log = tmp_dirs
    A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))
    assert reports.exists()
    assert log.parent.exists()


def test_run_dr_ddk_returns_valid_schema(tmp_dirs):
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))
    r = orch.run_agent_dr_ddk()
    assert isinstance(r, AgentAuditReport)
    assert r.agent_id == "Dr_DDK_Legal_AI"
    assert r.status in ("APPROVED", "REJECTED", "WARNING", "ERROR")
    assert 0 <= r.audit_score <= 100
    assert "heurístic" in r.legal_disclaimer.lower() or "heuristic" in r.legal_disclaimer.lower()


def test_run_dra_pwc_returns_valid_schema(tmp_dirs):
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))
    r = orch.run_agent_dra_pwc()
    assert r.agent_id == "Dra_PWC_TechAudit_AI"
    assert "BAITBridge" in str(r.findings)
    assert r.audit_score >= 50
    assert r.status == "APPROVED"


def test_validate_rejects_low_score_with_approved_status(tmp_dirs):
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))
    bad = AgentAuditReport(
        agent_id="test_bad", timestamp=0, status="APPROVED",
        audit_score=10.0, findings=["some finding"],
    )
    with pytest.raises(ComplianceError, match="score=10"):
        orch.validate(bad)


def test_validate_rejects_empty_findings(tmp_dirs):
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))
    bad = AgentAuditReport(
        agent_id="test_bad", timestamp=0, status="APPROVED",
        audit_score=80.0, findings=[],
    )
    with pytest.raises(ComplianceError, match="findings vazio"):
        orch.validate(bad)


def test_execute_audit_cycle_end_to_end(tmp_dirs):
    """Ciclo completo: 2 agentes → validação → consolidação → arquivo + proof log."""
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))

    consolidated = orch.execute_audit_cycle()

    # Schema
    assert isinstance(consolidated, ConsolidatedComplianceReport)
    assert len(consolidated.agents_evaluations) == 2
    assert re.match(r"^[a-f0-9]{64}$", consolidated.sha256)

    # Arquivo salvo
    files = list(reports.glob("audit_*.json"))
    assert len(files) == 1
    saved = json.loads(files[0].read_text())
    assert saved["environment"] == "E2E-Compliance"
    assert len(saved["agents_evaluations"]) == 2

    # SHA bate com o do payload canonicalizado
    canonical = json.dumps(
        {k: v for k, v in saved.items() if k != "sha256"},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    import hashlib
    assert hashlib.sha256(canonical).hexdigest() == consolidated.sha256

    # Proof log
    entries = json.loads(log.read_text())
    assert len(entries) == 1
    assert entries[0]["sha256"] == consolidated.sha256


def test_multiple_cycles_append_to_proof_log(tmp_dirs):
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))

    for _ in range(3):
        orch.execute_audit_cycle()

    entries = json.loads(log.read_text())
    assert len(entries) == 3
    files = list(reports.glob("audit_*.json"))
    assert len(files) == 3
    # SHAs são únicos (timestamps podem repetir mas hash é do payload inteiro)
    shas = {e["sha256"] for e in entries}
    assert len(shas) == 3


def test_health_returns_valid_schema(tmp_dirs):
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))
    h = orch.health()
    assert h.status == "healthy"
    assert h.cycles_total == 0

    orch.execute_audit_cycle()
    h2 = orch.health()
    assert h2.cycles_total == 1
    assert h2.last_cycle_sha256 is not None
    assert h2.last_cycle_ts is not None


def test_proof_log_resilient_to_corruption(tmp_dirs):
    reports, log = tmp_dirs
    log.write_text("{[corrupted json")
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))
    # Não deve crashar — começa do zero
    orch.execute_audit_cycle()
    entries = json.loads(log.read_text())
    assert len(entries) == 1


def test_legal_disclaimer_in_every_report(tmp_dirs):
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))
    r = orch.execute_audit_cycle()
    for a in r.agents_evaluations:
        assert "INTERNA" in a.legal_disclaimer or "INTERNAL" in a.legal_disclaimer.upper()
        assert "advocacia" in a.legal_disclaimer.lower() or "lawyer" in a.legal_disclaimer.lower() or "opinião legal" in a.legal_disclaimer.lower()


def test_audit_score_bounds_in_findings(tmp_dirs):
    """Invariante cross-field: score < 50 + status APPROVED → rejected."""
    reports, log = tmp_dirs
    orch = A2AComplianceOrchestrator(reports_dir=str(reports), proof_log_path=str(log))

    # Patch run_agent para retornar score baixo
    bad_report = AgentAuditReport(
        agent_id="low_score_bot", timestamp=0, status="APPROVED",
        audit_score=30.0, findings=["x"],
    )
    orch.run_agent_dr_ddk = lambda: bad_report

    with pytest.raises(ComplianceError):
        orch.execute_audit_cycle()
