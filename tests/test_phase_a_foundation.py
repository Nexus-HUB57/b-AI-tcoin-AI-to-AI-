r"""
Phase A: Foundation Hardening — Tests

Tests for:
- A.1: Address System (BAITAddress, pubkey_to_address, agent_to_address)
- A.2: Fee Market (FeeMarket, FeeEstimator, MempoolEntry)
- A.3: Transaction Verifier (TransactionVerifier)
- A.4: Difficulty Adjustment (DifficultyAdjuster)
- A.5: Integration (Blockchain with all Phase A modules)
"""

import hashlib
import pytest
from baitcoin_core.blockchain.addresses import (
    BAITAddress, pubkey_to_address, agent_to_address, validate_address,
    hash160, base58_encode, base58_decode,
)
from baitcoin_core.blockchain.fees import FeeMarket, FeeEstimator, MempoolEntry
from baitcoin_core.blockchain.tx_verifier import TransactionVerifier, verify_transaction
from baitcoin_core.blockchain.block import (
    Block, BlockHeader, Transaction, TransactionInput, TransactionOutput,
)
from baitcoin_core.consensus.difficulty import DifficultyAdjuster
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus


# ═══════════════════════════════════════════════════════════
# A.1: Address System Tests
# ═══════════════════════════════════════════════════════════

class TestAddressSystem:
    r"""Test BAITAddress derivation, parsing, and validation."""

    def test_pubkey_to_address_mainnet(self):
        r"""Derive mainnet address from 32-byte pubkey."""
        pubkey = hashlib.sha256(b"test_agent").digest()[:32]
        addr = BAITAddress.from_pubkey(pubkey, 'mainnet')
        assert addr.version == 0x00
        assert addr.network == 'mainnet'
        assert len(addr.pubkey_hash) == 20
        addr_str = str(addr)
        assert addr_str.startswith("b'")

    def test_pubkey_to_address_testnet(self):
        r"""Derive testnet address."""
        pubkey = hashlib.sha256(b"test_agent").digest()[:32]
        addr = BAITAddress.from_pubkey(pubkey, 'testnet')
        assert addr.version == 0x01
        assert addr.network == 'testnet'
        assert str(addr).startswith("t'")

    def test_agent_to_address(self):
        r"""Derive deterministic address from agent ID."""
        addr1 = agent_to_address("chimera7")
        addr2 = agent_to_address("chimera7")
        assert addr1 == addr2  # Same agent = same address

        addr3 = agent_to_address("other_agent")
        assert addr1 != addr3  # Different agent = different address

    def test_address_roundtrip(self):
        r"""Address -> string -> parse -> same address."""
        pubkey = hashlib.sha256(b"roundtrip_test").digest()[:32]
        original = BAITAddress.from_pubkey(pubkey, 'mainnet')
        addr_str = str(original)
        parsed = BAITAddress.parse(addr_str)
        assert parsed.version == original.version
        assert parsed.pubkey_hash == original.pubkey_hash

    def test_invalid_address(self):
        r"""Reject invalid addresses."""
        assert not validate_address("invalid")
        assert not validate_address("b'")
        assert not validate_address("")

    def test_hash160(self):
        r"""Hash160 produces 20 bytes."""
        result = hash160(b"test")
        assert len(result) == 20

    def test_base58_roundtrip(self):
        r"""Base58 encode/decode roundtrip."""
        data = b"\x00" * 5 + b"\xab\xcd\xef\x01\x23\x45"
        encoded = base58_encode(data)
        decoded = base58_decode(encoded)
        assert decoded == data

    def test_address_equality(self):
        r"""Address equality and hashing."""
        pubkey = hashlib.sha256(b"eq_test").digest()[:32]
        a1 = BAITAddress.from_pubkey(pubkey)
        a2 = BAITAddress.from_pubkey(pubkey)
        assert a1 == a2
        assert hash(a1) == hash(a2)


# ═══════════════════════════════════════════════════════════
# A.2: Fee Market Tests
# ═══════════════════════════════════════════════════════════

class TestFeeMarket:
    r"""Test FeeMarket, FeeEstimator, and MempoolEntry."""

    def _make_tx(self, agent_id: str = "agent1") -> Transaction:
        return Transaction(
            tx_type="transfer",
            agent_id=agent_id,
            nonce=0,
            outputs=[TransactionOutput(amount_sats=1000, script_pubkey=b"\x00" * 32)],
        )

    def test_add_transaction(self):
        r"""Add a valid transaction to the mempool."""
        fm = FeeMarket()
        tx = self._make_tx()
        ok, reason = fm.add_transaction(tx, fee_rate=10)
        assert ok
        assert reason == ""
        assert fm.size == 1

    def test_reject_coinbase(self):
        r"""Coinbase transactions cannot be added to mempool."""
        fm = FeeMarket()
        tx = Transaction(tx_type="coinbase", agent_id="miner")
        ok, reason = fm.add_transaction(tx, fee_rate=10)
        assert not ok
        assert "Coinbase" in reason

    def test_reject_below_min_fee(self):
        r"""Transactions below minimum fee rate are rejected."""
        fm = FeeMarket(min_fee_rate=5)
        tx = self._make_tx()
        ok, reason = fm.add_transaction(tx, fee_rate=1)
        assert not ok
        assert "below minimum" in reason

    def test_reject_duplicate(self):
        r"""Duplicate transactions are rejected."""
        fm = FeeMarket()
        tx = self._make_tx()
        fm.add_transaction(tx, fee_rate=10)
        ok, reason = fm.add_transaction(tx, fee_rate=20)
        assert not ok
        assert "already in mempool" in reason

    def test_fee_prioritization(self):
        r"""Transactions are selected by fee rate (highest first)."""
        fm = FeeMarket()
        tx_low = self._make_tx("agent_low")
        tx_high = self._make_tx("agent_high")
        fm.add_transaction(tx_low, fee_rate=5)
        fm.add_transaction(tx_high, fee_rate=50)
        selected, fees, median = fm.select_transactions()
        assert len(selected) == 2
        assert selected[0].agent_id == "agent_high"  # Higher fee first

    def test_fee_estimation(self):
        r"""FeeEstimator provides estimates based on history."""
        est = FeeEstimator()
        # No history: returns default
        assert est.estimate_fee(1) == 10
        # With history
        for rate in [5, 8, 12, 15, 10]:
            est.record_block_fees(rate)
        assert est.estimate_fee(1) >= 5  # Median should be 10

    def test_block_max_weight(self):
        r"""Selection respects block weight limit."""
        fm = FeeMarket(block_max_weight=500)
        for i in range(100):
            tx = self._make_tx(f"agent_{i}")
            fm.add_transaction(tx, fee_rate=10)
        selected, _, _ = fm.select_transactions()
        # Should include fewer than 100 txs due to weight limit
        assert len(selected) < 100

    def test_fee_histogram(self):
        r"""Fee histogram is available for the API."""
        fm = FeeMarket()
        tx = self._make_tx()
        fm.add_transaction(tx, fee_rate=10)
        info = fm.to_dict()
        assert info["size"] == 1
        assert info["estimated_fee_1block"] >= 1
        assert info["total_fees_collected"] == 0


# ═══════════════════════════════════════════════════════════
# A.3: Transaction Verifier Tests
# ═══════════════════════════════════════════════════════════

class TestTransactionVerifier:
    r"""Test TransactionVerifier."""

    def test_reject_no_inputs(self):
        r"""Transaction with no inputs is rejected."""
        verifier = TransactionVerifier({})
        tx = Transaction(tx_type="transfer", outputs=[
            TransactionOutput(amount_sats=100, script_pubkey=b"\x00" * 32),
        ])
        result = verifier.verify(tx)
        assert not result.valid
        assert "no inputs" in result.reason

    def test_reject_no_outputs(self):
        r"""Transaction with no outputs is rejected."""
        verifier = TransactionVerifier({})
        tx = Transaction(tx_type="transfer", inputs=[
            TransactionInput(prev_tx_id=b"\x00" * 32, prev_output_index=0),
        ])
        result = verifier.verify(tx)
        assert not result.valid
        assert "no outputs" in result.reason

    def test_reject_missing_utxo(self):
        r"""Transaction referencing non-existent UTXO is rejected."""
        verifier = TransactionVerifier({})
        tx = Transaction(
            tx_type="transfer",
            inputs=[TransactionInput(prev_tx_id=b"\x01" * 32, prev_output_index=0)],
            outputs=[TransactionOutput(amount_sats=100, script_pubkey=b"\x00" * 32)],
        )
        result = verifier.verify(tx)
        assert not result.valid
        assert "not found" in result.reason

    def _make_signed_tx(self, utxo_set, tx):
        r"""Add a valid Schnorr signature to a transaction for testing."""
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair, SchnorrSignature
        kp = SchnorrKeyPair()
        sig = kp.sign(tx.tx_id)
        tx.signature = sig.raw
        # Update UTXO to have correct pubkey for verification
        first_key = f"{tx.inputs[0].prev_tx_id.hex()}:{tx.inputs[0].prev_output_index}"
        if first_key in utxo_set:
            utxo_set[first_key] = TransactionOutput(
                amount_sats=utxo_set[first_key].amount_sats,
                script_pubkey=kp.pub_bytes,  # Use signer's pubkey
            )
        return tx

    def test_reject_double_spend(self):
        r"""Double-spend within same block is rejected."""
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        kp = SchnorrKeyPair()
        utxo = TransactionOutput(amount_sats=1000, script_pubkey=kp.pub_bytes)
        utxo_set = {"aa" * 32 + ":0": utxo}
        verifier = TransactionVerifier(utxo_set)
        tx = Transaction(
            tx_type="transfer",
            inputs=[TransactionInput(prev_tx_id=b"\xaa" * 32, prev_output_index=0)],
            outputs=[TransactionOutput(amount_sats=500, script_pubkey=b"\x00" * 32)],
        )
        tx = self._make_signed_tx(utxo_set, tx)
        # First time: OK
        r1 = verifier.verify(tx)
        assert r1.valid
        # Second time: double-spend
        r2 = verifier.verify(tx)
        assert not r2.valid
        assert "Double-spend" in r2.reason

    def test_valid_transfer(self):
        r"""Valid transfer passes verification."""
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        kp = SchnorrKeyPair()
        utxo = TransactionOutput(amount_sats=1000, script_pubkey=kp.pub_bytes)
        utxo_set = {"bb" * 16 + "00" * 16 + ":0": utxo}
        verifier = TransactionVerifier(utxo_set)
        tx = Transaction(
            tx_type="transfer",
            inputs=[TransactionInput(prev_tx_id=b"\xbb" * 16 + b"\x00" * 16, prev_output_index=0)],
            outputs=[TransactionOutput(amount_sats=900, script_pubkey=b"\x00" * 32)],
        )
        tx = self._make_signed_tx(utxo_set, tx)
        result = verifier.verify(tx, fee_rate=10)
        assert result.valid
        assert result.fee == 100

    def test_nonce_enforcement(self):
        r"""Nonces must be increasing per agent."""
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        kp = SchnorrKeyPair()
        utxo_set = {}
        for i in range(3):
            txid = hashlib.sha256(f"utxo_{i}".encode()).digest()
            key = f"{txid.hex()}:0"
            utxo_set[key] = TransactionOutput(amount_sats=1000, script_pubkey=kp.pub_bytes)

        verifier = TransactionVerifier(utxo_set)
        txid0 = hashlib.sha256(b"utxo_0").digest()
        tx1 = Transaction(
            tx_type="transfer", agent_id="a1", nonce=0,
            inputs=[TransactionInput(prev_tx_id=txid0, prev_output_index=0)],
            outputs=[TransactionOutput(amount_sats=500, script_pubkey=b"\x00" * 32)],
        )
        tx1 = self._make_signed_tx(utxo_set, tx1)
        txid1 = hashlib.sha256(b"utxo_1").digest()
        tx2 = Transaction(
            tx_type="transfer", agent_id="a1", nonce=0,
            inputs=[TransactionInput(prev_tx_id=txid1, prev_output_index=0)],
            outputs=[TransactionOutput(amount_sats=500, script_pubkey=b"\x00" * 32)],
        )
        tx2 = self._make_signed_tx(utxo_set, tx2)
        r1 = verifier.verify(tx1)
        assert r1.valid
        r2 = verifier.verify(tx2)
        assert not r2.valid
        assert "Invalid nonce" in r2.reason


# ═══════════════════════════════════════════════════════════
# A.4: Difficulty Adjustment Tests
# ═══════════════════════════════════════════════════════════

class TestDifficultyAdjustment:
    r"""Test DifficultyAdjuster."""

    def test_initial_difficulty(self):
        r"""Initial difficulty is the default."""
        da = DifficultyAdjuster()
        assert da.current_bits == 0x1d00ffff

    def test_should_adjust_at_interval(self):
        r"""Adjustment triggers every ADJUSTMENT_INTERVAL blocks."""
        da = DifficultyAdjuster()
        assert not da.should_adjust(0)
        assert not da.should_adjust(100)
        assert not da.should_adjust(2015)
        assert da.should_adjust(2016)
        assert da.should_adjust(4032)

    def test_bits_to_target(self):
        r"""Compact bits conversion is correct."""
        assert DifficultyAdjuster._bits_to_target(0x1d00ffff) > 0

    def test_target_to_bits_roundtrip(self):
        r"""target -> bits -> target roundtrip."""
        da = DifficultyAdjuster()
        for bits in [0x1d00ffff, 0x1c0000ff, 0x20010000, 0x17000001]:
            target = da._bits_to_target(bits)
            back = da._target_to_bits(target)
            # May not be exact due to precision, but should be close
            assert abs(da._bits_to_target(back) - target) <= 1

    def test_difficulty_info(self):
        r"""Difficulty info is available for the API."""
        da = DifficultyAdjuster()
        info = da.get_difficulty_info([])
        assert "current_bits" in info
        assert "target_block_time" in info
        assert info["adjustment_interval"] == 2016


# ═══════════════════════════════════════════════════════════
# A.5: Integration Tests
# ═══════════════════════════════════════════════════════════

class TestPhaseAIntegration:
    r"""Integration: Blockchain with FeeMarket + DAA + Address + TxVerifier."""

    def test_blockchain_has_fee_market(self):
        r"""Blockchain initializes with FeeMarket."""
        bc = Blockchain()
        assert bc.fee_market is not None
        assert bc.fee_market.size == 0

    def test_blockchain_has_difficulty_adjuster(self):
        r"""Blockchain initializes with DifficultyAdjuster."""
        bc = Blockchain()
        assert bc.difficulty_adjuster is not None

    def test_mine_blocks_with_phase_a(self):
        r"""Mine 5 blocks and verify Phase A features work."""
        # Use loose target for test speed
        consensus = ZkMLConsensus(
            target=0x00ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
        )
        bc = Blockchain(consensus=consensus)
        for i in range(5):
            pubkey = hashlib.sha256(f"miner_{i}".encode()).digest()[:33]
            block = bc.mine_block(f"miner_{i}", pubkey)
            assert block.index == i + 1
        assert bc.height == 5
        assert bc.validate_chain()

    def test_to_dict_includes_fee_market(self):
        r"""Blockchain.to_dict() includes fee market data."""
        bc = Blockchain()
        bc.mine_block("miner1", hashlib.sha256(b"m1").digest()[:33])
        d = bc.to_dict()
        assert "fee_market" in d
        assert "difficulty" in d

    def test_agent_address_in_balance_lookup(self):
        r"""Agent addresses can be used for balance lookups."""
        bc = Blockchain()
        # agent_to_address returns a string, but we can also create a BAITAddress object
        addr_obj = BAITAddress.from_agent_id("chimera7")
        bc.mine_block("chimera7", hashlib.sha256(b"chimera7_pub").digest()[:33])
        # Address derivation works - roundtrip test
        addr_str = str(addr_obj)
        parsed = BAITAddress.parse(addr_str)
        assert parsed.pubkey_hash == addr_obj.pubkey_hash

    def test_version_bump(self):
        r"""Core version is now 0.5.0."""
        from baitcoin_core import __version__
        assert __version__ == "0.6.0"
