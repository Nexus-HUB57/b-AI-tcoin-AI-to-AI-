#!/usr/bin/env python3
"""Fail-closed dry-run builder/auditor for HEX-style EVM transactions.

This tool models account-based transactions only. It never loads private keys,
signs payloads, calls an RPC endpoint, or broadcasts a transaction.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
HEX_DATA = re.compile(r"^0x(?:[0-9a-fA-F]{2})*$")
WEI_PER_NATIVE = Decimal("1000000000000000000")


class HexTxError(ValueError):
    pass


@dataclass(frozen=True)
class EvmTx:
    chain_id: int
    nonce: int
    to: str
    value_wei: int
    data: str
    gas_limit: int
    max_fee_per_gas_wei: int
    max_priority_fee_per_gas_wei: int

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvmTx":
        required = (
            "chain_id", "nonce", "to", "value_wei", "data", "gas_limit",
            "max_fee_per_gas_wei", "max_priority_fee_per_gas_wei",
        )
        missing = [key for key in required if key not in raw]
        if missing:
            raise HexTxError(f"missing transaction fields: {', '.join(missing)}")
        tx = cls(*(raw[key] for key in required))
        if tx.chain_id <= 0 or tx.nonce < 0 or tx.value_wei < 0:
            raise HexTxError("chain_id must be positive; nonce and value must be non-negative")
        if not ADDRESS.fullmatch(tx.to):
            raise HexTxError("to must be a 20-byte EVM address")
        if not HEX_DATA.fullmatch(tx.data):
            raise HexTxError("data must be even-length 0x-prefixed hex")
        if tx.gas_limit <= 0 or tx.max_fee_per_gas_wei < 0 or tx.max_priority_fee_per_gas_wei < 0:
            raise HexTxError("gas and fee fields are invalid")
        if tx.max_priority_fee_per_gas_wei > tx.max_fee_per_gas_wei:
            raise HexTxError("priority fee cannot exceed max fee")
        return tx


@dataclass(frozen=True)
class DryRunResult:
    mode: str
    chain_id: int
    nonce: int
    to: str
    calldata_bytes: int
    max_fee_wei: int
    max_fee_native: str
    required_native_balance_wei: int
    required_native_balance: str
    value_wei: int
    value_native: str
    signing: str
    broadcast: str
    monitoring: str


def native(wei: int) -> str:
    return format(Decimal(wei) / WEI_PER_NATIVE, "f")


def simulate(tx: EvmTx, native_balance_wei: int) -> DryRunResult:
    if native_balance_wei < 0:
        raise HexTxError("native balance must be non-negative")
    max_fee = tx.gas_limit * tx.max_fee_per_gas_wei
    required = tx.value_wei + max_fee
    if native_balance_wei < required:
        raise HexTxError(
            f"insufficient native balance: need {required} wei, have {native_balance_wei} wei"
        )
    return DryRunResult(
        mode="dry-run",
        chain_id=tx.chain_id,
        nonce=tx.nonce,
        to=tx.to,
        calldata_bytes=(len(tx.data) - 2) // 2,
        max_fee_wei=max_fee,
        max_fee_native=native(max_fee),
        required_native_balance_wei=required,
        required_native_balance=native(required),
        value_wei=tx.value_wei,
        value_native=native(tx.value_wei),
        signing="blocked: external signer required; no key material accepted",
        broadcast="blocked: no RPC or broadcaster configured",
        monitoring="not started: no transaction hash exists in dry-run",
    )


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HexTxError(f"invalid JSON input: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("transaction"), dict):
        raise HexTxError("input must contain a transaction object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--native-balance-wei", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        raw = load(args.input)
        tx = EvmTx.from_dict(raw["transaction"])
        print(json.dumps(asdict(simulate(tx, args.native_balance_wei)), indent=2, sort_keys=True))
        return 0
    except HexTxError as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
