"""Bounded recovery queue and fail-closed circuit breaker for HSM jobs."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import monotonic
from typing import Callable, Deque, Generic, TypeVar


T = TypeVar("T")
R = TypeVar("R")


class QueueBackpressure(RuntimeError):
    """Raised when the bounded queue cannot accept another recovery job."""


class CircuitOpen(RuntimeError):
    """Raised while repeated HSM failures keep the circuit open."""


class CircuitBreaker:
    """Small deterministic breaker with closed, open and half-open states."""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout: float = 30.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if failure_threshold <= 0 or reset_timeout <= 0:
            raise ValueError("failure_threshold and reset_timeout must be positive")
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._probe_in_flight = False

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if self._clock() - self._opened_at >= self.reset_timeout:
            return "half-open"
        return "open"

    @property
    def failures(self) -> int:
        return self._failures

    def allow(self) -> bool:
        state = self.state
        if state == "closed":
            return True
        if state == "open":
            return False
        if self._probe_in_flight:
            return False
        self._probe_in_flight = True
        return True

    def require_allow(self) -> None:
        if not self.allow():
            raise CircuitOpen("HSM circuit open: recovery temporarily blocked")

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._probe_in_flight = False

    def record_failure(self) -> None:
        self._probe_in_flight = False
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = self._clock()


@dataclass(frozen=True)
class RecoveryJob(Generic[T]):
    job_id: str
    payload: T


class BoundedRecoveryQueue(Generic[T, R]):
    """Non-blocking bounded queue; full queues apply explicit backpressure."""

    def __init__(self, maxsize: int, breaker: CircuitBreaker | None = None) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self.maxsize = maxsize
        self._items: Deque[RecoveryJob[T]] = deque()
        self.breaker = breaker or CircuitBreaker()
        self.accepted = 0
        self.rejected_full = 0
        self.rejected_circuit = 0

    def submit(self, job: RecoveryJob[T]) -> None:
        if len(self._items) >= self.maxsize:
            self.rejected_full += 1
            raise QueueBackpressure("recovery queue full: apply backpressure")
        if not self.breaker.allow():
            self.rejected_circuit += 1
            raise CircuitOpen("HSM circuit open: recovery temporarily blocked")
        self._items.append(job)
        self.accepted += 1

    def process_one(self, handler: Callable[[T], R]) -> R | None:
        if not self._items:
            return None
        if not self.breaker.allow():
            self.rejected_circuit += 1
            raise CircuitOpen("HSM circuit open: queued recovery paused")
        job = self._items.popleft()
        try:
            result = handler(job.payload)
        except Exception:
            self.breaker.record_failure()
            raise
        self.breaker.record_success()
        return result

    def __len__(self) -> int:
        return len(self._items)
