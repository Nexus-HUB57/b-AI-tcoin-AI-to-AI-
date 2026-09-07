"""Componentes isolados para o nó nativo de processamento."""

from .webhook_auth import (
    AuthError,
    EventEnvelope,
    WebhookAuthenticator,
    canonical_payload,
    payload_hash,
)
from .swap_engine import SwapEngine, SwapError, SwapQuote, SwapOrder
from .swap_protocol import IntentError, SwapIntent, sign_quote
from .swap_sync import SwapSyncStore, SyncError
from .swap_executor import Deposit, ExecutorError, OrderState, SwapExecutor
from .parity_gate import ParityAttestation, ParityError, ParityGate
from .native_adapters import BitcoinCoreReader, BitcoinRpcError, BaitBlockchainSettlement
from .swap_service import NativeSwapService

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
    "IntentError",
    "SwapIntent",
    "sign_quote",
    "SwapSyncStore",
    "SyncError",
    "Deposit",
    "ExecutorError",
    "OrderState",
    "SwapExecutor",
    "ParityAttestation",
    "ParityError",
    "ParityGate",
    "BitcoinCoreReader",
    "BitcoinRpcError",
    "BaitBlockchainSettlement",
    "NativeSwapService",
]

__version__ = "0.2.0"
