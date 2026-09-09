"""Adaptador mínimo para o endpoint de webhook existente.

Uso no serviço atual, sem alterar seus módulos:

    from native_processing.integration import verify_webhook_body
    envelope, duplicate = verify_webhook_body(body, authenticator)
    inserted = ledger.put_event(envelope.payload)

A validação acontece antes de qualquer gravação no ledger. O serviço pode manter
seu contrato HTTP atual e mapear AuthError para HTTP 400/401 conforme sua política.
"""
from __future__ import annotations

from typing import Any, Mapping, Tuple

from .webhook_auth import AuthError, EventEnvelope, WebhookAuthenticator


def verify_webhook_body(body: Mapping[str, Any], authenticator: WebhookAuthenticator) -> Tuple[EventEnvelope, bool]:
    envelope = EventEnvelope.from_dict(body)
    _, status = authenticator.authenticate_and_record(envelope)
    return envelope, status == "duplicate"


def build_authenticator_from_env(environ: Mapping[str, str]) -> WebhookAuthenticator:
    registry = environ.get("WEBHOOK_KEY_REGISTRY")
    state_db = environ.get("WEBHOOK_AUTH_DB")
    if not registry or not state_db:
        raise AuthError("WEBHOOK_KEY_REGISTRY and WEBHOOK_AUTH_DB are required")
    return WebhookAuthenticator(
        registry, state_db,
        max_skew_seconds=int(environ.get("WEBHOOK_MAX_SKEW_SECONDS", "300")),
        max_ttl_seconds=int(environ.get("WEBHOOK_MAX_TTL_SECONDS", "900")),
    )
