"""Factory: carrega ParityGate a partir de config JSON (somente pubkeys).

Suporta:
  - multi-sig concatenada (oracle-a/b/c)
  - FROST group key (frost-group)

Exemplo staging:
  gate = load_parity_gate("secrets/oracles-staging/parity_gate_config.staging.json")
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Union

from native_processing.parity_gate import ParityGate
from native_processing.frost_verifier import make_verifier_from_authorized


def load_parity_gate(
    config: Union[str, Path, Mapping[str, Any]],
    *,
    clock: Optional[Callable[[], float]] = None,
) -> ParityGate:
    if isinstance(config, (str, Path)):
        data = json.loads(Path(config).read_text())
    else:
        data = dict(config)

    pubs_raw = data.get("authorized_pubkeys") or {}
    if not pubs_raw:
        raise ValueError("config missing authorized_pubkeys")

    scheme = str(data.get("scheme", "auto"))
    verify = make_verifier_from_authorized(pubs_raw, scheme=scheme)

    kwargs: dict = {
        "min_quorum": int(data.get("min_quorum", 3)),
        "tolerance_bps": int(data.get("tolerance_bps", 50)),
        "max_age_seconds": int(data.get("max_age_seconds", 60)),
    }
    if scheme in ("frost", "frost-pedersen-dkg", "musig2") or (
        scheme == "auto" and list(pubs_raw.keys()) == ["frost-group"]
    ):
        kwargs["min_quorum"] = int(data.get("min_quorum", 1))

    if clock is not None:
        kwargs["clock"] = clock
    return ParityGate(verify, **kwargs)


def load_authorized_pubkeys(path: Union[str, Path]) -> dict:
    data = json.loads(Path(path).read_text())
    raw = data.get("authorized_pubkeys", data)
    out = {}
    for k, v in raw.items():
        out[k] = bytes.fromhex(v) if isinstance(v, str) else v
    return out
