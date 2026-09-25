"""Safe HTTP-facing adapter for external mining work in non-Mainnet networks."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Optional

from baitcoin_core.consensus.work_template import ShareSubmission, WorkTemplateManager


class MiningTransportService:
    """Expose work and share operations without applying blocks or paying out."""

    TEST_NETWORKS = {"regtest", "testnet", "baitcoin-testnet"}
    MAINNET_NAMES = {"mainnet", "baitcoin-mainnet", "production"}

    def __init__(
        self,
        blockchain,
        *,
        network: str,
        chain_id: str,
        template_ttl_seconds: int = 60,
        share_target: Optional[int] = None,
        max_requests: int = 30,
        window_seconds: int = 60,
        clock=time.time,
    ):
        normalized = network.strip().lower()
        if normalized in self.MAINNET_NAMES or normalized not in self.TEST_NETWORKS:
            raise ValueError("external mining transport is disabled outside regtest/testnet")
        self.network = normalized
        self.chain_id = chain_id
        self.clock = clock
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._request_times = defaultdict(deque)
        self.manager = WorkTemplateManager(
            blockchain,
            network=normalized,
            chain_id=chain_id,
            template_ttl_seconds=template_ttl_seconds,
            share_target=share_target,
            clock=clock,
        )

    def _check_rate(self, client_id: str, now: float) -> bool:
        if not client_id or len(client_id) > 128:
            return False
        bucket = self._request_times[client_id]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True

    def issue_template(self, *, miner_id: str, payout_script_hex: str, client_id: str, now: Optional[float] = None) -> dict:
        now = self.clock() if now is None else now
        if not self._check_rate(client_id, now):
            raise PermissionError("rate limit exceeded")
        if not isinstance(payout_script_hex, str) or not payout_script_hex or len(payout_script_hex) > 512:
            raise ValueError("payout_script_hex is required and bounded")
        try:
            payout_script = bytes.fromhex(payout_script_hex)
        except ValueError as exc:
            raise ValueError("payout_script_hex must be valid hex") from exc
        template = self.manager.create_template(miner_id, payout_script, now=now)
        return template.to_dict()

    def submit_share(self, payload: dict, *, client_id: str, now: Optional[float] = None) -> dict:
        now = self.clock() if now is None else now
        if not self._check_rate(client_id, now):
            raise PermissionError("rate limit exceeded")
        if not isinstance(payload, dict):
            raise ValueError("share payload must be an object")
        submission = ShareSubmission(
            template_id=str(payload.get("template_id", "")),
            miner_id=str(payload.get("miner_id", "")),
            nonce=payload.get("nonce", -1),
            extra_nonce=str(payload.get("extra_nonce", "")),
            tensor_commitment=str(payload.get("tensor_commitment", "")),
            proof_hash=str(payload.get("proof_hash", "")),
        )
        result = self.manager.submit_share(submission, now=now)
        return {
            "status": result.status,
            "reason": result.reason,
            "share_id": result.share_id,
            "is_block_solution": result.is_block_solution,
            "network": self.network,
            "attestation": "share-only-no-payout",
        }

    def submit_block(self, payload: dict, *, client_id: str, now: Optional[float] = None) -> dict:
        """Admit a candidate for later application; never append or broadcast."""
        now = self.clock() if now is None else now
        if not self._check_rate(client_id, now):
            raise PermissionError("rate limit exceeded")
        if not isinstance(payload, dict) or not isinstance(payload.get("block"), dict):
            raise ValueError("block payload must contain an object under block")
        template_id = str(payload.get("template_id", ""))
        try:
            from baitcoin_core.ecosystem import _restore_block
            block = _restore_block(payload["block"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("invalid serialized block") from exc
        result = self.manager.submit_block(template_id, block, now=now)
        validation = result.validation
        return {
            "status": result.status,
            "reason": result.reason,
            "template_id": template_id,
            "block_hash": block.block_hash.hex(),
            "validation": {
                "valid": validation.valid,
                "reason": validation.reason,
                "fees_sats": validation.fees_sats,
            } if validation is not None else None,
            "network": self.network,
            "attestation": "candidate-only-no-application",
        }
