import json
from pathlib import Path

import pytest

from tools.hex_tx_dry_run import EvmTx, HexTxError, load, simulate


FIXTURE = Path(__file__).parent / "fixtures" / "hex_evm_tx_dry_run.json"


def test_hex_dry_run_calculates_max_fee_and_blocks_side_effects():
    raw = load(FIXTURE)
    tx = EvmTx.from_dict(raw["transaction"])
    result = simulate(tx, native_balance_wei=10_000_000_000_000_000)

    assert result.chain_id == 369
    assert result.nonce == 42
    assert result.calldata_bytes == 36
    assert result.max_fee_wei == 6_000_000_000_000_000
    assert result.required_native_balance_wei == result.max_fee_wei
    assert result.signing.startswith("blocked:")
    assert result.broadcast.startswith("blocked:")
    assert result.monitoring.startswith("not started:")


def test_rejects_insufficient_native_balance():
    tx = EvmTx.from_dict(load(FIXTURE)["transaction"])
    with pytest.raises(HexTxError, match="insufficient native balance"):
        simulate(tx, native_balance_wei=1)


def test_rejects_invalid_evm_fields():
    raw = load(FIXTURE)["transaction"]
    raw["to"] = "not-an-address"
    with pytest.raises(HexTxError, match="20-byte EVM address"):
        EvmTx.from_dict(raw)


def test_cli_fixture_is_json_and_has_no_private_key_material():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    serialized = json.dumps(data).lower()
    assert "private_key" not in serialized
    assert "seed" not in serialized
