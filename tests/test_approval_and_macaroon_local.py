import base64
import os

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.approval_gate import Approval, ApprovalError, ApprovalGate, canonical_json
from scripts.macaroon_provider import FileMacaroonProvider, MacaroonProviderError


def signed_approval(private_key, operator_id, approval_id):
    payload = {
        "approval_id": approval_id,
        "order_id": "order-1",
        "invoice_sha256": "b" * 64,
        "amount_sats": 1000,
        "config_sha256": "c" * 64,
        "purpose": "lightning-mainnet-settlement",
        "issued_at": 100,
        "expires_at": 200,
        "operator_id": operator_id,
    }
    signature = private_key.sign(canonical_json(payload))
    return Approval(payload, base64.b64encode(signature).decode("ascii"))


def test_two_distinct_signed_approvals(tmp_path):
    key_a = Ed25519PrivateKey.generate()
    key_b = Ed25519PrivateKey.generate()
    registry = {
        "a": {"status": "active", "role": "settlement-approver", "public_key_b64": base64.b64encode(key_a.public_key().public_bytes_raw()).decode()},
        "b": {"status": "active", "role": "settlement-approver", "public_key_b64": base64.b64encode(key_b.public_key().public_bytes_raw()).decode()},
    }
    gate = ApprovalGate(str(tmp_path / "approvals.sqlite3"), registry, now=lambda: 150)
    gate.require_two(order_id="order-1", invoice_sha256="b" * 64, amount_sats=1000, config_sha256="c" * 64, approvals=[signed_approval(key_a, "a", "ap-a"), signed_approval(key_b, "b", "ap-b")])
    with pytest.raises(ApprovalError):
        gate.require_two(order_id="order-1", invoice_sha256="b" * 64, amount_sats=1000, config_sha256="c" * 64, approvals=[signed_approval(key_a, "a", "ap-c"), signed_approval(key_a, "a", "ap-d")])
    gate.close()


def test_macaroon_file_permissions_and_content(tmp_path):
    path = tmp_path / "macaroon"
    path.write_bytes(b"least-privilege-macaroon")
    os.chmod(path, 0o600)
    assert FileMacaroonProvider(path).load() == b"least-privilege-macaroon"
    os.chmod(path, 0o644)
    with pytest.raises(MacaroonProviderError):
        FileMacaroonProvider(path).load()
