"""Provider-neutral HSM/MPC signing boundary.

This module never handles private keys and never broadcasts transactions. It
accepts an unsigned payload, validates policy, and delegates signing to an
external HTTPS signer. Missing configuration or malformed responses fail
closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class SignerError(RuntimeError):
    """Base error for safe signing failures."""


class PolicyViolation(SignerError):
    """Request is outside the configured signing policy."""


class SignerUnavailable(SignerError):
    """Signer is disabled, unreachable, or returned an invalid response."""


_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


@dataclass(frozen=True)
class SigningPolicy:
    policy_id: str
    allowed_networks: frozenset[str]
    max_amount_sats: int
    allowed_destinations: frozenset[str]
    max_payload_bytes: int = 400_000

    def validate(self, request: "SigningRequest") -> None:
        if request.network not in self.allowed_networks:
            raise PolicyViolation("network is not allowed by signing policy")
        if request.amount_sats <= 0 or request.amount_sats > self.max_amount_sats:
            raise PolicyViolation("amount exceeds signing policy")
        if request.destination not in self.allowed_destinations:
            raise PolicyViolation("destination is not allowlisted")
        if request.policy_id != self.policy_id:
            raise PolicyViolation("policy_id mismatch")
        if len(request.unsigned_tx_hex) // 2 > self.max_payload_bytes:
            raise PolicyViolation("unsigned payload exceeds policy size")


@dataclass(frozen=True)
class SigningRequest:
    unsigned_tx_hex: str
    network: str
    destination: str
    amount_sats: int
    policy_id: str
    idempotency_key: str
    input_count: int = 1

    def validate_shape(self) -> None:
        if not isinstance(self.unsigned_tx_hex, str) or not self.unsigned_tx_hex:
            raise PolicyViolation("unsigned transaction is required")
        if len(self.unsigned_tx_hex) % 2 or not _HEX_RE.fullmatch(self.unsigned_tx_hex):
            raise PolicyViolation("unsigned transaction must be even-length hex")
        if not isinstance(self.network, str) or not self.network:
            raise PolicyViolation("network is required")
        if not isinstance(self.destination, str) or not self.destination:
            raise PolicyViolation("destination is required")
        if type(self.amount_sats) is not int or self.amount_sats <= 0:
            raise PolicyViolation("amount_sats must be a positive integer")
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise PolicyViolation("policy_id is required")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", self.idempotency_key):
            raise PolicyViolation("invalid idempotency key")
        if type(self.input_count) is not int or self.input_count <= 0:
            raise PolicyViolation("input_count must be a positive integer")

    @property
    def payload_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.unsigned_tx_hex)).hexdigest()


class SignerTransport(Protocol):
    def post(self, payload: Mapping[str, Any], idempotency_key: str) -> Mapping[str, Any]: ...


class HttpsSignerTransport:
    """Minimal HTTPS transport; secrets are read only from the environment."""

    def __init__(self, endpoint: str, token: str, timeout_seconds: float = 10.0) -> None:
        if not endpoint.startswith("https://"):
            raise SignerUnavailable("signer endpoint must use HTTPS")
        if not token:
            raise SignerUnavailable("signer credential is not configured")
        self.endpoint = endpoint
        self._token = token
        self.timeout_seconds = timeout_seconds

    def post(self, payload: Mapping[str, Any], idempotency_key: str) -> Mapping[str, Any]:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status < 200 or response.status >= 300:
                    raise SignerUnavailable(f"signer returned HTTP {response.status}")
                result = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise SignerUnavailable("signer request failed") from exc
        if not isinstance(result, dict):
            raise SignerUnavailable("signer response must be an object")
        return result


class HsmMpcSigner:
    """Policy gate and external signing boundary; no broadcast capability."""

    def __init__(self, policy: SigningPolicy, transport: SignerTransport) -> None:
        self.policy = policy
        self.transport = transport

    def sign(self, request: SigningRequest) -> dict[str, object]:
        request.validate_shape()
        self.policy.validate(request)
        response = self.transport.post(
            {
                "version": 1,
                "operation": "sign_raw_transaction",
                "network": request.network,
                "unsigned_tx_hex": request.unsigned_tx_hex,
                "destination": request.destination,
                "amount_sats": request.amount_sats,
                "policy_id": request.policy_id,
                "payload_sha256": request.payload_sha256,
                "input_count": request.input_count,
                "require_all_signed": True,
            },
            request.idempotency_key,
        )
        signed = response.get("signed_tx_hex")
        request_id = response.get("request_id")
        if not isinstance(signed, str) or not signed or len(signed) % 2 or not _HEX_RE.fullmatch(signed):
            raise SignerUnavailable("signer did not return valid signed_tx_hex")
        if not isinstance(request_id, str) or not request_id:
            raise SignerUnavailable("signer did not return request_id")
        if response.get("all_signed") is not True:
            raise SignerUnavailable("signer response is not all-signed")
        if response.get("signed_input_count") != request.input_count:
            raise SignerUnavailable("signer did not sign every input")
        if response.get("payload_sha256") != request.payload_sha256:
            raise SignerUnavailable("signer payload hash mismatch")
        if response.get("idempotency_key") != request.idempotency_key:
            raise SignerUnavailable("signer idempotency key mismatch")
        return {
            "request_id": request_id,
            "signed_tx_hex": signed,
            "all_signed": True,
            "signed_input_count": request.input_count,
            "payload_sha256": request.payload_sha256,
            "idempotency_key": request.idempotency_key,
        }


def from_environment(policy: SigningPolicy) -> HsmMpcSigner:
    """Build a signer only when explicitly enabled and fully configured."""
    if os.getenv("BAITCOIN_SIGNER_ENABLED", "false").lower() != "true":
        raise SignerUnavailable("HSM/MPC signer is disabled")
    endpoint = os.getenv("BAITCOIN_SIGNER_ENDPOINT", "")
    token = os.getenv("BAITCOIN_SIGNER_TOKEN", "")
    return HsmMpcSigner(policy, HttpsSignerTransport(endpoint, token))


__all__ = [
    "HsmMpcSigner", "HttpsSignerTransport", "PolicyViolation", "SignerError",
    "SignerUnavailable", "SigningPolicy", "SigningRequest", "from_environment",
]
