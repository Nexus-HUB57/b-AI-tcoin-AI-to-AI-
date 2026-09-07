"""Componentes isolados para o nó nativo de processamento."""

from .webhook_auth import (
    AuthError,
    EventEnvelope,
    WebhookAuthenticator,
    canonical_payload,
    payload_hash,
)
from .swap_engine import SwapEngine, SwapError, SwapQuote, SwapOrder

__all__ = [
    "AuthError",
    "EventEnvelope",
    "WebhookAuthenticator",
    "canonical_payload",
    "payload_hash",
    "SwapEngine",
    "SwapError",
    "SwapQuote",
    "SwapOrder",
]

__version__ = "0.1.0"
