import pytest

from tools.hsm_recovery_e2e_dry_run import RecoveryOrchestrator, run_recovery_simulation
from tools.hsm_signing_e2e_dry_run import MockHSMSigner, RejectingMockHSMSigner


def test_recovery_after_hsm_alert_revalidates_and_signs_again():
    result = run_recovery_simulation()
    assert result["final_state"] == "signed"
    assert result["broadcast_attempted"] is False
    assert result["mutations"] == []
    assert result["broadcast_result"].startswith("broadcast blocked:")
    assert result["audit_events"] == [
        "hsm_alert",
        "executor_paused",
        "payload_revalidated",
        "signer_reauthorized",
        "signature_accepted",
    ]


def test_recovery_stops_when_revalidation_fails():
    orchestrator = RecoveryOrchestrator(RejectingMockHSMSigner())
    with pytest.raises(RuntimeError, match="HSM_REJECTED"):
        orchestrator.request_signature(b"\x33" * 32)
    orchestrator.mitigate_alert()
    with pytest.raises(RuntimeError, match="revalidation failed"):
        orchestrator.recover(
            b"\x33" * 32,
            revalidate=lambda: False,
            fresh_signer=MockHSMSigner("hsm-recovery-test-key"),
        )
    assert orchestrator.state == "paused"
    assert orchestrator.broadcast_attempted is False
    assert orchestrator.mutations == []
