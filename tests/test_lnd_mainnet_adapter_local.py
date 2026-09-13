from types import SimpleNamespace

from scripts.lnd_mainnet_adapter import (
    LndAdapterConfig,
    MainnetAdapterError,
    MainnetSettlementAdapter,
    SettlementPaused,
)


class LightningMessages:
    class GetInfoRequest:
        pass

    class PayReqString:
        def __init__(self, pay_req):
            self.pay_req = pay_req


class RouterMessages:
    class SendPaymentRequest:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


class Lightning:
    def GetInfo(self, request, timeout=None):
        return SimpleNamespace(chains=[SimpleNamespace(network="mainnet")])

    def DecodePayReq(self, request, timeout=None):
        return SimpleNamespace(network="mainnet", num_satoshis=1000, timestamp=100, expiry=100000)


class Router:
    def SendPaymentV2(self, request, timeout=None):
        assert request.payment_request.startswith("lnbc")
        return iter([SimpleNamespace(status=2, payment_hash="hash-1", fee_msat=10)])


class ApprovalGateStub:
    def require_two(self, **kwargs):
        assert kwargs["amount_sats"] == 1000
        assert len(kwargs["approvals"]) == 2


def make_adapter(tmp_path):
    return MainnetSettlementAdapter(
        LndAdapterConfig(
            host="lnd.invalid", port=10009, ca_cert_path="unused", tls_server_name="lnd.invalid",
            macaroon_scope="read_info,send_payment", max_order_sats=2000,
            daily_limit_sats=5000, max_fee_msat=100, authorization_reference="AUTH-1",
            manual_unlock=True, two_person_approval=True,
        ),
        Lightning(), Router(), tmp_path / "adapter.sqlite3",
        lightning_message_module=LightningMessages,
        router_message_module=RouterMessages,
        approval_gate=ApprovalGateStub(),
        approvals_loader=lambda order_id: ["approval-a", "approval-b"],
        config_sha256="a" * 64,
        now=lambda: 200,
    )


def test_settle_and_idempotent_reconcile(tmp_path):
    adapter = make_adapter(tmp_path)
    order = {
        "order_id": "order-1", "payment_request": "lnbc10u-test",
        "btc_sats": 1000, "state": "bait_confirmed", "counterparty_allowlisted": True,
    }
    receipt = adapter.settle(order)
    assert receipt.status == "SUCCEEDED"
    assert receipt.external_payment_hash == "hash-1"
    assert adapter.reconcile("order-1") == receipt
    assert adapter.settle(order) == receipt
    adapter.close()


def test_pause_blocks_settlement(tmp_path):
    adapter = make_adapter(tmp_path)
    adapter.pause()
    order = {
        "order_id": "order-2", "payment_request": "lnbc10u-test",
        "btc_sats": 1000, "state": "bait_confirmed", "counterparty_allowlisted": True,
    }
    try:
        adapter.settle(order)
    except SettlementPaused:
        pass
    else:
        raise AssertionError("paused adapter accepted settlement")
    adapter.close()


def test_wrong_state_rejected(tmp_path):
    adapter = make_adapter(tmp_path)
    try:
        adapter.preflight({
            "order_id": "order-3", "payment_request": "lnbc10u-test",
            "btc_sats": 1000, "state": "created", "counterparty_allowlisted": True,
        })
    except MainnetAdapterError:
        pass
    else:
        raise AssertionError("invalid state accepted")
    adapter.close()
