import pytest

from baitcoin_security.hsm_mpc import (
    HsmMpcSigner,
    PolicyViolation,
    SignerUnavailable,
    SigningPolicy,
    SigningRequest,
    from_environment,
)


RAW = "02000000000000000000"
DEST = "bc1qwwgdhzdgy97ysqqtd9z7rwv76fwktg0w4tvwf8"


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, payload, idempotency_key):
        self.calls.append((payload, idempotency_key))
        return self.response


def policy():
    return SigningPolicy("btc-mainnet-v1", frozenset({"bitcoin-mainnet"}), 240700000, frozenset({DEST}))


def request(**overrides):
    values = dict(unsigned_tx_hex=RAW, network="bitcoin-mainnet", destination=DEST,
                  amount_sats=240700000, policy_id="btc-mainnet-v1", idempotency_key="req-20260921-0001")
    values.update(overrides)
    return SigningRequest(**values)


def test_sign_delegates_without_private_key():
    r = request()
    transport = FakeTransport({"request_id": "hsm-1", "signed_tx_hex": "ab12", "all_signed": True, "signed_input_count": 1, "payload_sha256": r.payload_sha256, "idempotency_key": r.idempotency_key})
    result = HsmMpcSigner(policy(), transport).sign(r)
    assert result["request_id"] == "hsm-1"
    assert result["signed_tx_hex"] == "ab12"
    assert result["all_signed"] is True
    assert result["signed_input_count"] == 1
    assert result["payload_sha256"] == r.payload_sha256
    assert "private_key" not in transport.calls[0][0]
    assert transport.calls[0][1] == "req-20260921-0001"


def test_destination_policy_fails_closed():
    signer = HsmMpcSigner(policy(), FakeTransport({"request_id": "x", "signed_tx_hex": "ab12"}))
    with pytest.raises(PolicyViolation):
        signer.sign(request(destination="bc1qnotallowlisted"))


def test_malformed_signer_response_fails_closed():
    signer = HsmMpcSigner(policy(), FakeTransport({"request_id": "x", "signed_tx_hex": "not-hex"}))
    with pytest.raises(SignerUnavailable):
        signer.sign(request())


def test_partial_signature_is_rejected():
    r = request(input_count=2)
    response = {"request_id": "x", "signed_tx_hex": "ab12", "all_signed": False, "signed_input_count": 1, "payload_sha256": r.payload_sha256, "idempotency_key": r.idempotency_key}
    with pytest.raises(SignerUnavailable, match="all-signed"):
        HsmMpcSigner(policy(), FakeTransport(response)).sign(r)


def test_all_signed_requires_matching_input_count_and_payload():
    r = request(input_count=2)
    response = {"request_id": "x", "signed_tx_hex": "ab12", "all_signed": True, "signed_input_count": 1, "payload_sha256": "0" * 64, "idempotency_key": r.idempotency_key}
    with pytest.raises(SignerUnavailable, match="every input"):
        HsmMpcSigner(policy(), FakeTransport(response)).sign(r)


def test_transport_payload_requires_all_signed_contract():
    r = request(input_count=2)
    response = {"request_id": "x", "signed_tx_hex": "ab12", "all_signed": True, "signed_input_count": 2, "payload_sha256": r.payload_sha256, "idempotency_key": r.idempotency_key}
    transport = FakeTransport(response)
    HsmMpcSigner(policy(), transport).sign(r)
    payload, key = transport.calls[0]
    assert payload["require_all_signed"] is True
    assert payload["input_count"] == 2
    assert key == r.idempotency_key


def test_environment_default_is_disabled(monkeypatch):
    monkeypatch.delenv("BAITCOIN_SIGNER_ENABLED", raising=False)
    with pytest.raises(SignerUnavailable, match="disabled"):
        from_environment(policy())


def test_http_endpoint_requires_https():
    from baitcoin_security.hsm_mpc import HttpsSignerTransport
    with pytest.raises(SignerUnavailable, match="HTTPS"):
        HttpsSignerTransport("http://localhost:8080/sign", "token")
