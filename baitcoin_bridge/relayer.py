r"""Relayer — Submits cross-chain proofs to target chains.

The relayer is responsible for:
    1. Watching the BridgeManager for confirmed lock events
    2. Generating Merkle proofs for those events
    3. Submitting proofs to the target chain (ETH/SOL contract)
    4. Collecting multi-sig signatures from authorized signers
    5. Tracking relayer fees and performance

In production, the relayer runs as a separate service that:
    - Connects to b'AI'tcoin P2P network for event detection
    - Connects to ETH/SOL RPC for proof submission
    - Earns fees for successful proof submissions

Security:
    - Relayers cannot mint tokens directly
    - They can only submit proofs that the N-of-M signers verify
    - Relayer fees are paid separately from bridge fees

Usage::

    relayer = Relayer(bridge_manager)
    result = relayer.relay_next()
    print(result["status"])  # "submitted"
"""
import time
import hashlib
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class RelayerConfig:
    r"""Relayer configuration."""
    relayer_id: str
    fee_bps: int = 10  # Relayer fee in basis points
    max_retries: int = 3
    retry_delay: float = 30.0
    auto_relay: bool = True

    def to_dict(self) -> dict:
        return {
            "relayer_id": self.relayer_id,
            "fee_bps": self.fee_bps,
            "max_retries": max_retries,
            "retry_delay": self.retry_delay,
            "auto_relay": self.auto_relay,
        }


@dataclass
class RelayJob:
    r"""A proof relay job."""
    job_id: str
    event_id: str
    transfer_id: str
    chain_id: int
    proof: List[str]
    signatures: List[str]
    attempts: int = 0
    status: str = "pending"  # pending, submitted, confirmed, failed
    submitted_at: float = 0.0
    confirmed_at: float = 0.0
    fee_sats: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "event_id": self.event_id,
            "transfer_id": self.transfer_id,
            "chain_id": self.chain_id,
            "status": self.status,
            "attempts": self.attempts,
            "signatures": len(self.signatures),
            "fee_sats": self.fee_sats,
            "fee_bait": self.fee_sats / 100_000_000,
            "submitted_at": self.submitted_at,
            "confirmed_at": self.confirmed_at,
            "error": self.error,
        }


class Relayer:
    r"""Cross-chain proof relayer.

    Picks up lock events from the BridgeManager, generates
    Merkle proofs, and submits them to target chains.

    Parameters
    ----------
    bridge_manager : BridgeManager
        The bridge manager to relay proofs for
    config : RelayerConfig
        Relayer configuration
    """

    def __init__(self, bridge_manager, config: RelayerConfig = None):
        self.manager = bridge_manager
        self.config = config or RelayerConfig(
            relayer_id=uuid.uuid4().hex[:8],
        )
        self._jobs: Dict[str, RelayJob] = {}
        self._total_relayed = 0
        self._total_failed = 0
        self._total_fees_earned = 0

    def relay_event(self, event_id: str) -> dict:
        r"""Relay a specific lock event to the target chain.

        Parameters
        ----------
        event_id : str
            Lock event ID to relay

        Returns
        -------
        dict
            Relay result
        """
        stats = self.manager.get_stats()
        event = self.manager._events.get(event_id)
        if not event:
            return {"error": "event_not_found"}

        if event.event_type != "lock":
            return {"error": "not_a_lock_event"}

        # Check if already relayed
        for job in self._jobs.values():
            if job.event_id == event_id and job.status == "confirmed":
                return {"error": "already_relayed"}

        job_id = f"relay_{uuid.uuid4().hex[:8]}"
        fee_sats = int(event.amount_sats * self.config.fee_bps / 10000)

        job = RelayJob(
            job_id=job_id,
            event_id=event_id,
            transfer_id=event.transfer_id,
            chain_id=event.chain_id,
            proof=event.merkle_proof,
            signatures=[],
            fee_sats=fee_sats,
        )

        # Submit proof to bridge manager
        result = self.manager.submit_proof(
            event_id=event_id,
            proof=event.merkle_proof,
            signer_id=self.config.relayer_id,
            signature=hashlib.sha256(
                f"{event_id}:{job_id}".encode()
            ).hexdigest(),
        )

        if result.get("success"):
            job.status = "submitted"
            job.submitted_at = time.time()
            job.signatures = [f"{self.config.relayer_id}:auto"]

            if result.get("ready_to_mint"):
                job.status = "confirmed"
                job.confirmed_at = time.time()
                self._total_relayed += 1
                self._total_fees_earned += fee_sats
        else:
            job.status = "failed"
            job.error = result.get("error", "unknown")
            self._total_failed += 1

        self._jobs[job_id] = job
        return {
            "success": job.status in ("submitted", "confirmed"),
            "job": job.to_dict(),
            "manager_result": result,
        }

    def relay_next(self) -> Optional[dict]:
        r"""Automatically relay the next eligible event.

        Finds a locked event that hasn't been relayed yet
        and submits its proof.
        """
        for event_id, event in self.manager._events.items():
            if (event.event_type == "lock"
                    and event.state in ("locked", "pending_proof")):
                # Check if already in a job
                already_relayed = any(
                    j.event_id == event_id
                    and j.status in ("submitted", "confirmed")
                    for j in self._jobs.values()
                )
                if not already_relayed:
                    return self.relay_event(event_id)
        return None

    def get_job(self, job_id: str) -> dict:
        r"""Get relay job details."""
        job = self._jobs.get(job_id)
        return job.to_dict() if job else {"error": "not_found"}

    def get_stats(self) -> dict:
        r"""Get relayer statistics."""
        by_status = {}
        for job in self._jobs.values():
            by_status[job.status] = by_status.get(job.status, 0) + 1

        return {
            "relayer_id": self.config.relayer_id,
            "total_relayed": self._total_relayed,
            "total_failed": self._total_failed,
            "total_fees_earned_bait": (
                self._total_fees_earned / 100_000_000
            ),
            "active_jobs": sum(
                1 for j in self._jobs.values()
                if j.status in ("pending", "submitted")
            ),
            "by_status": by_status,
        }

    def to_dict(self) -> dict:
        r"""Full relayer state export."""
        return {
            "config": self.config.to_dict(),
            "stats": self.get_stats(),
            "jobs": {jid: j.to_dict() for jid, j in self._jobs.items()},
        }
