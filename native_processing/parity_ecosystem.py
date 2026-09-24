"""Sincronização ParityGate ↔ SwapExecutor / ecossistema BAIT.

Uso no serviço de swap (sem editar swap_executor.py):

    from native_processing.parity_ecosystem import build_settlement_stack

    stack = build_settlement_stack(
        config_path="secrets/oracles-staging/parity_gate_config.staging.json",
        executor_db="executor.sqlite",
        bitcoin_reader=reader,
        bait_settlement=settlement,
        enable_settlement=True,
    )
    state = stack.executor.admit(intent)

Attestation ao vivo:

    from native_processing.parity_ecosystem import live_attestation_dict
    att = live_attestation_dict(signers, bait_usdt=1.0)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Union

from native_processing.parity_gate import ParityGate
from native_processing.parity_gate_factory import load_parity_gate
from native_processing.parity_attestation_builder import build_signed_attestation

try:
    from native_processing.swap_executor import SwapExecutor
except ImportError:  # ambiente parcial / testes isolados
    SwapExecutor = None  # type: ignore


@dataclass
class SettlementStack:
    gate: ParityGate
    executor: Any
    config_path: Optional[str] = None


def build_settlement_stack(
    *,
    config_path: Union[str, Path, Mapping[str, Any]],
    executor_db: str,
    bitcoin_reader: Any,
    bait_settlement: Any,
    enable_settlement: bool = True,
    required_confirmations: int = 1,
    clock: Callable[[], float] = time.time,
) -> SettlementStack:
    if SwapExecutor is None:
        raise ImportError("native_processing.swap_executor not available in this environment")
    gate = load_parity_gate(config_path, clock=clock)
    executor = SwapExecutor(
        executor_db,
        bitcoin_reader,
        bait_settlement,
        required_confirmations=required_confirmations,
        enable_settlement=enable_settlement,
        clock=clock,
        parity_gate=gate if enable_settlement else None,
    )
    path_str = str(config_path) if isinstance(config_path, (str, Path)) else None
    return SettlementStack(gate=gate, executor=executor, config_path=path_str)


def live_attestation_dict(
    signers: Mapping[str, Any],
    *,
    bait_usdt: float = 1.0,
    ttl_seconds: float = 90.0,
    now: Optional[float] = None,
) -> dict:
    att = build_signed_attestation(
        signers,
        bait_usdt=bait_usdt,
        usdt_usd=1.0,
        usd_brl=5.0,
        ttl_seconds=ttl_seconds,
        now=now,
    )
    return {
        "version": 1,
        "pair": att.pair,
        "bait_usdt_ppm": att.bait_usdt_ppm,
        "usdt_usd_ppm": att.usdt_usd_ppm,
        "usd_brl_ppm": att.usd_brl_ppm,
        "observed_at": att.observed_at,
        "expires_at": att.expires_at,
        "round_id": att.round_id,
        "source_ids": list(att.source_ids),
        "quorum": att.quorum,
        "proof_b64": att.proof_b64,
    }


def health_parity(config_path: Union[str, Path, Mapping[str, Any]]) -> dict:
    import json
    from pathlib import Path as P

    if isinstance(config_path, (str, Path)):
        data = json.loads(P(config_path).read_text())
    else:
        data = dict(config_path)
    gate = load_parity_gate(data)
    pubs = data.get("authorized_pubkeys") or {}
    return {
        "ok": True,
        "scheme": data.get("scheme", "auto"),
        "min_quorum": gate.min_quorum,
        "tolerance_bps": gate.tolerance_bps,
        "n_authorized": len(pubs),
        "source_ids": list(pubs.keys()),
    }
