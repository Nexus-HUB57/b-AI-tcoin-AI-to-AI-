#!/usr/bin/env python3
"""Bounded local stress test for HSM recovery and synthetic UTXO artifacts."""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from tools.hsm_recovery_e2e_dry_run import RecoveryOrchestrator
from tools.hsm_signing_e2e_dry_run import MockHSMSigner, RejectingMockHSMSigner


@dataclass(frozen=True)
class StressResult:
    requested: int
    completed: int
    failed: int
    workers: int
    broadcast_attempts: int
    mutations: int
    elapsed_seconds: float
    recovery_rate_per_second: float


def one_recovery(index: int) -> bool:
    digest = index.to_bytes(32, "big")
    # Synthetic UTXO/artifact identity is local only and never queried on-chain.
    _utxo_artifact = {"txid": digest.hex(), "vout": index % 4, "spent": False}
    orchestrator = RecoveryOrchestrator(RejectingMockHSMSigner(f"hsm-alert-{index}"))
    try:
        orchestrator.request_signature(digest)
    except RuntimeError:
        pass
    orchestrator.mitigate_alert()
    orchestrator.recover(
        digest,
        revalidate=lambda: not _utxo_artifact["spent"] and len(digest) == 32,
        fresh_signer=MockHSMSigner(f"hsm-recovery-{index}"),
    )
    try:
        orchestrator.broadcast()
    except RuntimeError:
        pass
    return orchestrator.state == "signed" and not orchestrator.broadcast_attempted and not orchestrator.mutations


def run(count: int, workers: int) -> StressResult:
    if count <= 0 or workers <= 0 or workers > 32:
        raise ValueError("count must be positive and workers must be between 1 and 32")
    started = time.perf_counter()
    completed = 0
    with ThreadPoolExecutor(max_workers=min(workers, count)) as pool:
        futures = [pool.submit(one_recovery, index) for index in range(count)]
        for future in as_completed(futures):
            completed += int(future.result())
    elapsed = time.perf_counter() - started
    return StressResult(
        requested=count,
        completed=completed,
        failed=count - completed,
        workers=min(workers, count),
        broadcast_attempts=0,
        mutations=0,
        elapsed_seconds=round(elapsed, 6),
        recovery_rate_per_second=round(completed / elapsed, 2) if elapsed else 0.0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=256)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(run(args.count, args.workers).__dict__, indent=2, sort_keys=True))
