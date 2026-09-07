import base64
import json
import time
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from native_processing.native_adapters import BitcoinCoreReader, BitcoinRpcError, BaitBlockchainSettlement
from native_processing.swap_engine import SwapEngine
from native_processing.swap_executor import Deposit, OrderState, SwapExecutor
from native_processing.swap_protocol import sign_quote
from native_processing.swap_service import NativeSwapService
from native_processing.swap_sync import SwapSyncStore


class FakeBitcoin:
    def __init__(self, deposit=None):
        self.deposit = deposit

    def find_deposit(self, order_id, intent):
        return self.deposit


class FakeBait:
    def __init__(self):
        self.calls = 0
        self.state = "pending"

    def submit(self, intent, deposit):
        self.calls += 1
        return "bait-tx-fake"

    def status(self, external_id):
        return self.state


class FakeP2P:
    def __init__(self):
        self.broadcasts = []

    def broadcast_tx(self, tx):
        self.broadcasts.append(tx)
        return 1


def make_signed_intent(now=1000.0, **kwargs):
    engine = SwapEngine(":memory:", quote_ttl_seconds=120)
    quote = engine.quote("buy_bait", 100_000, 2_000_000, now=now)
    maker = Ed25519PrivateKey.generate()
    recipient = kwargs.pop("bait_recipient_pubkey", b"r" * 32)
    intent = sign_quote(
        quote,
        "maker-native",
        maker,
        "client-native",
        now=now + 1,
        btc_deposit_address=kwargs.pop("btc_deposit_address", "bcrt1qswapdeposit"),
        bait_recipient_pubkey=recipient,
        network=kwargs.pop("network", "regtest"),
    )
    engine.close()
    return intent


def test_executor_signed_intent_confirmation_and_idempotent_settlement(tmp_path: Path):
    intent = make_signed_intent()
    bitcoin = FakeBitcoin(Deposit("btc-tx-1", 100_000, 1, "bcrt1qswapdeposit", "regtest", vout=0))
    bait = FakeBait()
    executor = SwapExecutor(
        str(tmp_path / "orders.sqlite"), bitcoin, bait,
        required_confirmations=2, enable_settlement=True, clock=lambda: 1002.0,
    )
    try:
        assert executor.admit(intent) == OrderState.INTENT_VALIDATED
        assert executor.process(intent.order_id) == OrderState.BTC_OBSERVED
        bitcoin.deposit = Deposit("btc-tx-1", 100_000, 2, "bcrt1qswapdeposit", "regtest", vout=0)
        assert executor.process(intent.order_id) == OrderState.BAIT_SUBMITTED
        assert bait.calls == 1
        bait.state = "confirmed"
        assert executor.process(intent.order_id) == OrderState.SETTLED
        assert executor.process(intent.order_id) == OrderState.SETTLED
        assert bait.calls == 1
    finally:
        executor.close()


def test_executor_reconciles_recipient_network_and_amount(tmp_path: Path):
    intent = make_signed_intent()
    bitcoin = FakeBitcoin(Deposit("btc-tx-2", 100_001, 6, "wrong-address", "mainnet", vout=1))
    executor = SwapExecutor(
        str(tmp_path / "orders.sqlite"), bitcoin, FakeBait(),
        required_confirmations=1, clock=lambda: 1002.0,
    )
    try:
        executor.admit(intent)
        assert executor.process(intent.order_id) == OrderState.RECONCILING
    finally:
        executor.close()


def test_bitcoin_core_reader_checks_explicit_network_and_amount():
    class Reader(BitcoinCoreReader):
        def __init__(self, chain):
            super().__init__("http://rpc.invalid", "u", "p", network="regtest")
            self.chain = chain
            self.calls = []

        def _rpc(self, method, params):
            self.calls.append((method, params))
            if method == "getblockchaininfo":
                return {"chain": self.chain}
            if method == "getblockcount":
                return 10
            if method == "scantxoutset":
                return {"success": True, "unspents": [{
                    "txid": "a" * 64, "vout": 0, "amount": "0.00100000", "height": 8,
                }]}
            raise AssertionError(method)

    intent = make_signed_intent()
    reader = Reader("regtest")
    deposit = reader.find_deposit(intent.order_id, intent)
    assert deposit is not None
    assert deposit.btc_sats == 100_000
    assert deposit.confirmations == 3
    assert deposit.network == "regtest"
    assert [call[0] for call in reader.calls] == ["getblockchaininfo", "scantxoutset", "getblockcount"]

    mismatch = Reader("main")
    try:
        mismatch.find_deposit(intent.order_id, intent)
    except BitcoinRpcError as exc:
        assert "network mismatch" in str(exc)
    else:
        raise AssertionError("network mismatch must be rejected")


def test_native_bait_full_node_settlement_is_confirmed_after_mining(tmp_path: Path):
    blockchain = Blockchain()
    bridge_key = SchnorrKeyPair(private_key=12345)
    recipient_key = SchnorrKeyPair(private_key=67890)
    for _ in range(8):
        blockchain.mine_block("bridge-fund", bridge_key.pub_bytes)
        if any(output.script_pubkey == bridge_key.pub_bytes for output in blockchain.utxo_set.values()):
            break
    assert any(output.script_pubkey == bridge_key.pub_bytes for output in blockchain.utxo_set.values())
    intent = make_signed_intent(bait_recipient_pubkey=recipient_key.pub_bytes)
    deposit = Deposit("btc-tx-native", intent.btc_sats, 6, "bcrt1qswapdeposit", "regtest", vout=0)
    p2p = FakeP2P()
    settlement = BaitBlockchainSettlement(
        blockchain, bridge_key, network="regtest", db_path=str(tmp_path / "settlement.sqlite"), p2p_node=p2p
    )
    executor = SwapExecutor(
        str(tmp_path / "orders.sqlite"), FakeBitcoin(deposit), settlement,
        required_confirmations=1, enable_settlement=True, clock=lambda: 1002.0,
    )
    try:
        executor.admit(intent)
        assert executor.process(intent.order_id) == OrderState.BAIT_SUBMITTED
        assert len(p2p.broadcasts) == 1
        assert p2p.broadcasts[0]["tx_id"] == executor.get_order(intent.order_id)["external_id"]
        txid = executor.get_order(intent.order_id)["external_id"]
        assert settlement.status(txid) == "pending"
        state = OrderState.BAIT_SUBMITTED
        for _ in range(8):
            blockchain.mine_block("validator", SchnorrKeyPair(private_key=99999).pub_bytes)
            state = executor.process(intent.order_id)
            if state == OrderState.SETTLED:
                break
        assert state == OrderState.SETTLED
        assert settlement.status(txid) == "confirmed"
        assert any(
            output.script_pubkey == recipient_key.pub_bytes and output.amount_sats == intent.bait_units
            for block in blockchain.chain for tx in block.transactions for output in tx.outputs
        )
    finally:
        executor.close()
        settlement.close()


def test_service_persists_executor_state_for_resume(tmp_path: Path):
    intent = make_signed_intent(now=time.time())
    store = SwapSyncStore(str(tmp_path / "sync.sqlite"), "node-service")
    executor = SwapExecutor(
        str(tmp_path / "orders.sqlite"), FakeBitcoin(None), FakeBait(),
        required_confirmations=1, clock=time.time,
    )
    service = NativeSwapService(SwapEngine(":memory:"), store, executor)
    try:
        assert service.admit_intent(intent) == OrderState.INTENT_VALIDATED
        assert service.process_order(intent.order_id) == OrderState.INTENT_VALIDATED
        assert store.get_intent(intent.order_id)["status"] == OrderState.INTENT_VALIDATED.value
        assert store.pending_order_ids() == [intent.order_id]
    finally:
        executor.close()
        store.close()
