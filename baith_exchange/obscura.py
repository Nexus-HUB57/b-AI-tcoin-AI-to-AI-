"""Read-only Obscura provenance boundary for BAITHex preparation.

This adapter composes existing BAITHex policy validation with an Obscura
read operation. It never signs or broadcasts a transaction and therefore keeps
those capabilities behind :class:`BaithExchange`'s existing explicit gates.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from baith_policy.engine import TransactionIntent

from .service import BaithExchange


class ObscuraEvidenceProvider(Protocol):
    """Minimal provider contract; compatible with ObscuraBridge or a capability."""

    def fetch_page(self, url: str, *, agent_id: str = "", **kwargs: object) -> object: ...


class ObscuraEvidenceError(RuntimeError):
    """Raised when external evidence is not suitable for BAITHex preparation."""


@dataclass(frozen=True)
class ObscuraEvidence:
    url: str
    agent_id: str
    content_sha256: str
    content_length: int
    title: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "agent_id": self.agent_id,
            "content_sha256": self.content_sha256,
            "content_length": self.content_length,
            "title": self.title,
        }


class BaithObscuraCoordinator:
    """Attach auditable Obscura evidence to a validated BAITHex preparation."""

    def __init__(self, exchange: BaithExchange, evidence_provider: ObscuraEvidenceProvider) -> None:
        self.exchange = exchange
        self.evidence_provider = evidence_provider

    def prepare_with_evidence(
        self,
        intent: TransactionIntent,
        source_url: str,
        *,
        agent_id: str = "",
        **fetch_options: object,
    ) -> dict[str, object]:
        if not source_url or not source_url.startswith(("https://", "http://")):
            raise ObscuraEvidenceError("source_url must be an HTTP(S) URL")

        result = self.evidence_provider.fetch_page(
            source_url, agent_id=agent_id, **fetch_options
        )
        status = getattr(result, "status", None)
        content = getattr(result, "content", None)
        if status != "success" or not isinstance(content, str) or not content:
            raise ObscuraEvidenceError("Obscura did not return successful non-empty evidence")

        evidence = ObscuraEvidence(
            url=source_url,
            agent_id=agent_id,
            content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            content_length=len(content),
            title=str(getattr(result, "title", "") or ""),
        )
        prepared = self.exchange.validate_and_prepare(intent)
        prepared["obscura_evidence"] = evidence.to_dict()
        return prepared


__all__ = ["BaithObscuraCoordinator", "ObscuraEvidence", "ObscuraEvidenceError", "ObscuraEvidenceProvider"]
