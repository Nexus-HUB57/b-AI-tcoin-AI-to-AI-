from tools.hsm_recovery_stress_dry_run import run


def test_bounded_recovery_stress_keeps_broadcast_and_mutations_zero():
    result = run(count=16, workers=4)
    assert result.requested == 16
    assert result.completed == 16
    assert result.failed == 0
    assert result.broadcast_attempts == 0
    assert result.mutations == 0
    assert result.recovery_rate_per_second > 0
