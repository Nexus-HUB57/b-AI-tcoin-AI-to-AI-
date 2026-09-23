import pytest

from tools.hsm_recovery_control import (
    BoundedRecoveryQueue,
    CircuitBreaker,
    CircuitOpen,
    QueueBackpressure,
    RecoveryJob,
)


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def test_bounded_queue_rejects_when_full():
    queue = BoundedRecoveryQueue[str, str](maxsize=2)
    queue.submit(RecoveryJob("a", "A"))
    queue.submit(RecoveryJob("b", "B"))
    with pytest.raises(QueueBackpressure, match="queue full"):
        queue.submit(RecoveryJob("c", "C"))
    assert len(queue) == 2
    assert queue.rejected_full == 1


def test_circuit_opens_after_repeated_failures_and_pauses_queued_jobs():
    clock = Clock()
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout=10, clock=clock)
    queue = BoundedRecoveryQueue[str, str](maxsize=4, breaker=breaker)
    queue.submit(RecoveryJob("a", "A"))
    queue.submit(RecoveryJob("b", "B"))
    queue.submit(RecoveryJob("c", "C"))

    def fail(_payload):
        raise RuntimeError("HSM rejected")

    with pytest.raises(RuntimeError, match="HSM rejected"):
        queue.process_one(fail)
    with pytest.raises(RuntimeError, match="HSM rejected"):
        queue.process_one(fail)
    assert breaker.state == "open"
    assert len(queue) == 1
    with pytest.raises(CircuitOpen, match="queued recovery paused"):
        queue.process_one(lambda value: value)
    assert len(queue) == 1

    clock.advance(10)
    assert breaker.state == "half-open"
    assert queue.process_one(lambda value: value.lower()) == "c"
    assert breaker.state == "closed"
    assert queue.rejected_circuit == 1
