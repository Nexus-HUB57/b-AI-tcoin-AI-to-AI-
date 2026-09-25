#!/usr/bin/env python3
"""Fail-closed recovery protocol after a simulated HSM operational alert."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from tools.hsm_signing_e2e_dry_run import (
    HSMRejected,
    MockHSMSigner,
    RejectingMockHSMSigner,
)


@dataclass
class RecoveryOrchestrator:
    signer: MockHSMSigner
    state: str = "ready"
    broadcast_attempted: bool = False
    mutations: list[str] = field(default_factory=list)
    audit_events: list[str] = field(default_factory=list)

    def request_signature(self, digest: bytes) -> None:
        if self.state not in {"ready", "recovered"}:
            raise RuntimeError(f"signing unavailable in state {self.state}")
        try:
            self.signer.sign_digest(digest)
            self.state = "signed"
            self.audit_events.append("signature_accepted")
        except HSMRejected as exc:
            self.state = "alerted"
            self.audit_events.append("hsm_alert")
            raise RuntimeError(str(exc)) from exc

    def mitigate_alert(self) -> None:
        if self.state != "alerted":
            raise RuntimeError("no HSM alert to mitigate")
        self.state = "paused"
        self.audit_events.append("executor_paused")

    def recover(
        self,
        digest: bytes,
        revalidate: Callable[[], bool],
        fresh_signer: MockHSMSigner,
    ) -> None:
        if self.state != "paused":
            raise RuntimeError(f"recovery unavailable in state {self.state}")
        if len(digest) != 32:
            raise ValueError("digest must remain 32 bytes")
        if not revalidate():
            self.audit_events.append("revalidation_failed")
            raise RuntimeError("recovery blocked: payload or nonce revalidation failed")
        self.audit_events.append("payload_revalidated")
        self.signer = fresh_signer
        self.state = "recovered"
        self.audit_events.append("signer_reauthorized")
        self.request_signature(digest)

    def broadcast(self) -> None:
        if self.state != "signed":
            raise RuntimeError("broadcast blocked until a fresh signature exists")
        # Deliberately fail closed in this local harness.
        raise RuntimeError("broadcast blocked: dry-run recovery has no broadcaster")


def run_recovery_simulation() -> dict[str, object]:
    digest = bytes.fromhex("22" * 32)
    orchestrator = RecoveryOrchestrator(RejectingMockHSMSigner())
    try:
        orchestrator.request_signature(digest)
    except RuntimeError as exc:
        rejected_error = str(exc)
    orchestrator.mitigate_alert()
    revalidated = {"digest": digest, "nonce": 7, "chain_id": 1, "limits": True}
    orchestrator.recover(
        digest,
        revalidate=lambda: revalidated == {
            "digest": digest,
            "nonce": 7,
            "chain_id": 1,
            "limits": True,
        },
        fresh_signer=MockHSMSigner("hsm-recovery-test-key"),
    )
    broadcast_error = ""
    try:
        orchestrator.broadcast()
    except RuntimeError as exc:
        broadcast_error = str(exc)
    return {
        "initial_alert": rejected_error,
        "final_state": orchestrator.state,
        "broadcast_attempted": orchestrator.broadcast_attempted,
        "broadcast_result": broadcast_error,
        "mutations": orchestrator.mutations,
        "audit_events": orchestrator.audit_events,
    }


if __name__ == "__main__":
    print(json.dumps(run_recovery_simulation(), indent=2, sort_keys=True))
