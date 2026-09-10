#!/usr/bin/env python3
"""Validate ISP/Lightning operational configuration against safety invariants.

The validator is intentionally fail-closed. It never prints configuration values
that may contain credentials. Use --allow-placeholders for a template file; this
still validates the schema and safety defaults but permits REPLACE_WITH_* values.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised in minimal environments
    print("ERROR: PyYAML is required: python3 -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys."""


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False):
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"found duplicate key {key!r}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)

PLACEHOLDER = re.compile(r"REPLACE_WITH_|CHANGE-OR-AUTHORIZATION-ID|example\.invalid|^$", re.I)
SECRET_WORDS = re.compile(r"(seed|mnemonic|private.?key|wif|secret|password|token|api.?key)", re.I)


class Validator:
    def __init__(self, data: dict[str, Any], *, allow_placeholders: bool):
        self.d = data
        self.allow_placeholders = allow_placeholders
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def required(self, path: str) -> Any:
        value: Any = self.d
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                self.error(f"missing required field: {path}")
                return None
            value = value[part]
        return value

    def check_placeholder(self, path: str, value: Any, *, required_live: bool = True) -> None:
        if not isinstance(value, str):
            return
        if PLACEHOLDER.search(value):
            if required_live and not self.allow_placeholders:
                self.error(f"placeholder or empty value not allowed: {path}")
            else:
                self.warning(f"placeholder accepted for template field: {path}")

    def check(self) -> None:
        if not isinstance(self.d, dict):
            self.error("top-level YAML value must be a mapping")
            return

        schema = self.required("schema_version")
        if schema != "1.0":
            self.error("schema_version must be '1.0'")

        environment = self.required("environment")
        execution_mode = self.required("execution.mode")
        execution_enabled = self.required("execution.enabled")
        live = execution_enabled is True and execution_mode == "live"
        mainnet = environment == "mainnet"

        if environment not in {"regtest", "testnet", "mainnet"}:
            self.error("environment must be regtest, testnet, or mainnet")
        if execution_mode not in {"dry-run", "live"}:
            self.error("execution.mode must be dry-run or live")
        if not isinstance(execution_enabled, bool):
            self.error("execution.enabled must be boolean")

        # Mainnet and live mode are independently guarded.
        guard_enabled = self.required("mainnet_guard.enabled")
        authorization_status = self.required("mainnet_guard.authorization_status")
        approval_required = self.required("execution.require_explicit_live_approval")
        approval_ref = self.required("execution.live_approval_reference")
        if mainnet and guard_enabled is not True:
            self.error("mainnet requires mainnet_guard.enabled=true")
        if mainnet and authorization_status != "authorized":
            self.error("mainnet requires mainnet_guard.authorization_status=authorized")
        if live and approval_required is not True:
            self.error("live mode requires require_explicit_live_approval=true")
        if live:
            self.check_placeholder("execution.live_approval_reference", approval_ref)
            for path in (
                "mainnet_guard.authorization_reference",
                "mainnet_guard.operator_allowlist",
            ):
                if path == "mainnet_guard.operator_allowlist":
                    value = self.required(path)
                    if not isinstance(value, list) or not value:
                        self.error("live mode requires a non-empty operator_allowlist")
                else:
                    self.check_placeholder(path, self.required(path))

        # A dry-run must never broadcast or settle.
        if execution_mode == "dry-run":
            if self.dig("lightning.capabilities.pay_invoices") is True:
                self.error("dry-run cannot enable lightning.capabilities.pay_invoices")
            if self.dig("lightning.capabilities.settle_swaps") is True:
                self.error("dry-run cannot enable lightning.capabilities.settle_swaps")
            if self.dig("lightning.capabilities.broadcast_onchain_transactions") is True:
                self.error("dry-run cannot enable on-chain broadcasting")
            if self.dig("validation.prohibit_live_broadcast_in_dry_run") is not True:
                self.error("dry-run requires prohibit_live_broadcast_in_dry_run=true")

        # Network consistency.
        for path in ("isp.network", "lightning.network"):
            value = self.required(path)
            if value != environment:
                self.error(f"{path} must match top-level environment")
        allowed_networks = self.required("limits.allowed_networks")
        if isinstance(allowed_networks, list) and environment not in allowed_networks:
            self.error("limits.allowed_networks must include the selected environment")

        # Credentials must be indirect and scoped; private material is forbidden.
        credential_source = self.required("lightning.authentication.credential_source")
        if isinstance(credential_source, str):
            if not credential_source.startswith("secret-manager://"):
                self.error("lightning authentication must reference secret-manager://")
            self.check_placeholder("lightning.authentication.credential_source", credential_source)
        scope = self.required("lightning.authentication.scope")
        self.check_placeholder("lightning.authentication.scope", scope)
        for path, value in self.walk(self.d):
            if SECRET_WORDS.search(path) and isinstance(value, str) and value.strip():
                if path.endswith("private_key_in_config") or path.endswith("seed_in_config"):
                    continue
                if not value.startswith(("secret-manager://", "external_signer_only")):
                    self.error(f"possible inline secret material at {path}; use a secret reference")
        if self.dig("settlement_wallet.private_key_in_config") is not False:
            self.error("settlement_wallet.private_key_in_config must be false")
        if self.dig("settlement_wallet.seed_in_config") is not False:
            self.error("settlement_wallet.seed_in_config must be false")

        # TLS and endpoint checks.
        if self.dig("lightning.endpoint.tls.enabled") is not True:
            self.error("Lightning endpoint TLS must be enabled")
        if self.dig("lightning.endpoint.tls.verify_peer") is not True:
            self.error("Lightning endpoint TLS peer verification must be enabled")
        port = self.dig("lightning.endpoint.port")
        if self.allow_placeholders and port == 0:
            self.warning("placeholder port 0000 accepted for template validation")
        elif not isinstance(port, int) or not 1 <= port <= 65535:
            self.error("lightning.endpoint.port must be an integer from 1 to 65535")
        for path in ("lightning.endpoint.host", "lightning.endpoint.tls.server_name", "lightning.endpoint.tls.ca_source"):
            self.check_placeholder(path, self.dig(path), required_live=live)

        # Numeric limits and confirmation invariants.
        for path in (
            "limits.max_order_amount_btc", "limits.min_order_amount_btc",
            "limits.daily_limit_btc", "limits.hourly_limit_btc",
        ):
            value = self.dig(path)
            try:
                if float(value) < 0:
                    self.error(f"{path} cannot be negative")
                if live and float(value) <= 0:
                    self.error(f"{path} must be greater than zero in live mode")
            except (TypeError, ValueError):
                self.error(f"{path} must be a numeric value")
        min_amount = self.dig("limits.min_order_amount_btc")
        max_amount = self.dig("limits.max_order_amount_btc")
        try:
            if float(min_amount) > float(max_amount):
                self.error("min_order_amount_btc cannot exceed max_order_amount_btc")
        except (TypeError, ValueError):
            pass
        for path in (
            "confirmation_policy.bitcoin.required_confirmations_for_btc_locked",
            "confirmation_policy.bitcoin.required_confirmations_for_final_settlement",
        ):
            value = self.dig(path)
            if not isinstance(value, int) or value < 1:
                self.error(f"{path} must be an integer >= 1")
        locked = self.dig("confirmation_policy.bitcoin.required_confirmations_for_btc_locked")
        settled = self.dig("confirmation_policy.bitcoin.required_confirmations_for_final_settlement")
        if isinstance(locked, int) and isinstance(settled, int) and settled < locked:
            self.error("final settlement confirmations cannot be below btc_locked confirmations")

        # Rollback and audit are mandatory safety controls.
        required_true = (
            "rollback.cancel_pending_orders", "rollback.cancel_only_unsettled_orders",
            "rollback.reverse_config_without_delete", "rollback.preserve_audit_log",
            "rollback.preserve_order_records", "rollback.resume_requires_manual_review",
            "audit.enabled", "audit.immutable_event_log", "audit.redact_credentials",
        )
        for path in required_true:
            if self.dig(path) is not True:
                self.error(f"{path} must be true")
        for path in ("rollback.procedure_id", "rollback.pause_executor_command", "rollback.incident_contact"):
            self.check_placeholder(path, self.dig(path), required_live=live)

    def dig(self, path: str) -> Any:
        value: Any = self.d
        for part in path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    def walk(self, value: Any, prefix: str = ""):
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                yield from self.walk(child, path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from self.walk(child, f"{prefix}[{index}]")
        else:
            yield prefix, value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="YAML configuration file")
    parser.add_argument(
        "--allow-placeholders", action="store_true",
        help="allow template placeholders; never enables live execution",
    )
    args = parser.parse_args()

    try:
        with args.config.open("r", encoding="utf-8") as handle:
            data = yaml.load(handle, Loader=UniqueKeyLoader)
    except FileNotFoundError:
        print("ERROR: configuration file not found", file=sys.stderr)
        return 2
    except yaml.YAMLError as exc:
        print(f"ERROR: invalid YAML: {exc.__class__.__name__}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: cannot read configuration: {exc.__class__.__name__}", file=sys.stderr)
        return 2

    validator = Validator(data, allow_placeholders=args.allow_placeholders)
    validator.check()
    for warning in validator.warnings:
        print(f"WARNING: {warning}")
    if validator.errors:
        print(f"INVALID: {len(validator.errors)} safety check(s) failed")
        for error in validator.errors:
            print(f"ERROR: {error}")
        return 1
    print("VALID: configuration passed all safety checks")
    if args.allow_placeholders:
        print("NOTE: placeholder mode was used; this file is not ready for live execution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
