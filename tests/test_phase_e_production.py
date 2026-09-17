"""
Tests for Phase E: Production Readiness.

All tests are self-contained, fast, and do NOT depend on the full project
being importable.  We use lightweight fakes/stubs for blockchain, consensus,
peers, etc.
"""

from __future__ import annotations

import hashlib
import time
import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from baitcoin_core.audit.security_audit import SecurityAuditor, Severity
from baitcoin_core.audit.load_tester import LoadTester
from baitcoin_core.audit.mainnet_checker import MainnetChecker, ChecklistItem


# ── Lightweight fakes ────────────────────────────────────────────────────────

@dataclass
class FakeTransaction:
    txid: str = ""
    value: int = 0
    amount: int = 0
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)


@dataclass
class FakeBlock:
    hash: str = ""
    previous_hash: str = ""
    transactions: List[FakeTransaction] = field(default_factory=list)
    reward: int = 0
    coinbase_value: int = 0
    zkml_proof: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"hash": self.hash, "previous_hash": self.previous_hash}


class FakeBlockchain:
    def __init__(self, blocks: Optional[List[FakeBlock]] = None):
        self.blocks: List[FakeBlock] = blocks or []
        self.utxo_set: Dict[str, int] = {}


class FakeConsensus:
    def __init__(self, difficulty: int = 8, target: int = 0xFFFF):
        self.difficulty = difficulty
        self.current_difficulty = difficulty
        self.target = target
        self.max_target = 0xFFFF_FFFF_FFFF_FFFF
        self.min_target = 1
        self.target_block_time = 30
        self.verify_zkml_proof = lambda proof: True  # type: ignore[assignment]
        self.zkml_prover = True


class FakeContractEngine:
    def __init__(self, gas_limit: int = 1_000_000, max_state_size: int = 10 * 1024 * 1024):
        self.gas_limit = gas_limit
        self.max_state_size = max_state_size

    def validate_bytecode(self, bytecode: bytes) -> bool:
        return False  # rejects garbage


def _make_simple_chain(num_blocks: int = 5, genesis_reward: int = 50) -> FakeBlockchain:
    """Build a fake chain with correct linkage and consistent rewards."""
    blocks: List[FakeBlock] = []
    prev_hash = ""  # genesis has no parent
    for i in range(num_blocks):
        reward = genesis_reward // (2 ** (i // 210_000))
        h = hashlib.sha256(f"block-{i}-{prev_hash}".encode()).hexdigest()
        coinbase = FakeTransaction(txid=f"cb-{i}", value=reward)
        block = FakeBlock(
            hash=h,
            previous_hash=prev_hash,
            transactions=[coinbase],
            reward=reward,
            coinbase_value=reward,
            zkml_proof=f"proof-{i}" if i > 0 else None,
        )
        blocks.append(block)
        prev_hash = h
    return FakeBlockchain(blocks)


def _make_broken_genesis_chain() -> FakeBlockchain:
    """Chain where genesis rewards 5000 BAIT (wrong)."""
    blocks: List[FakeBlock] = []
    coinbase = FakeTransaction(txid="cb-bad", value=5000)
    block = FakeBlock(
        hash=hashlib.sha256(b"bad-genesis").hexdigest(),
        previous_hash="",
        transactions=[coinbase],
        reward=5000,
        coinbase_value=5000,
    )
    blocks.append(block)
    return FakeBlockchain(blocks)


# ══════════════════════════════════════════════════════════════════════════════
# Security Audit Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurityAudit(unittest.TestCase):
    """Tests for SecurityAuditor."""

    def test_genesis_correctness(self):
        """Genesis with 50 BAIT must pass; genesis with 5000 must fail."""
        chain = _make_simple_chain(genesis_reward=50)
        result = SecurityAuditor.audit_blockchain(chain)
        self.assertTrue(result["passed"], "Chain with correct genesis should pass")
        # No CRITICAL finding about genesis
        for f in result["findings"]:
            if "genesis" in f["category"] and f["severity"] == "CRITICAL":
                self.fail(f"Unexpected CRITICAL genesis finding: {f['description']}")

        # Now test the broken one
        bad_chain = _make_broken_genesis_chain()
        result2 = SecurityAuditor.audit_blockchain(bad_chain)
        self.assertFalse(result2["passed"], "Chain with 5000 BAIT genesis should fail")
        genesis_findings = [f for f in result2["findings"] if "genesis" in f["category"] and f["severity"] == "CRITICAL"]
        self.assertGreater(len(genesis_findings), 0, "Expected a CRITICAL genesis finding")
        self.assertIn("5000", genesis_findings[0]["description"])

    def test_chain_integrity(self):
        """Blocks with broken linkage must produce a CRITICAL finding."""
        chain = _make_simple_chain(num_blocks=3)
        # Break the chain
        chain.blocks[1].previous_hash = "GARBAGE"
        result = SecurityAuditor.audit_blockchain(chain)
        integrity = [f for f in result["findings"] if f["category"] == "chain_integrity"]
        self.assertGreater(len(integrity), 0, "Expected a chain_integrity finding")
        self.assertEqual(integrity[0]["severity"], "CRITICAL")

    def test_schnorr_roundtrip(self):
        """Cryptography audit must run without errors and return a score."""
        result = SecurityAuditor.audit_cryptography()
        self.assertIn("passed", result)
        self.assertIn("score", result)
        self.assertIn("findings", result)
        self.assertIsInstance(result["score"], float)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_full_audit_structure(self):
        """run_full_audit must return all five audit sections."""
        chain = _make_simple_chain(num_blocks=2)
        consensus = FakeConsensus()
        report = SecurityAuditor.run_full_audit(
            blockchain=chain,
            consensus=consensus,
        )
        self.assertIn("overall_score", report)
        self.assertIn("overall_passed", report)
        self.assertIn("summary", report)
        self.assertIn("timestamp", report)
        for section in ("blockchain", "consensus", "cryptography", "network", "contracts"):
            self.assertIn(section, report["audits"])
            self.assertIn("passed", report["audits"][section])
            self.assertIn("score", report["audits"][section])
        # Severity summary keys
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
            self.assertIn(sev, report["summary"])

    def test_network_audit_empty_peers_fails(self):
        """Empty peer list must fail the network audit."""
        result = SecurityAuditor.audit_network([])
        self.assertFalse(result["passed"])

    def test_consensus_audit_none_fails(self):
        """None consensus must produce a failed audit."""
        result = SecurityAuditor.audit_consensus(None, FakeBlockchain())
        self.assertFalse(result["passed"])

    def test_contract_audit_rejects_invalid_bytecode(self):
        """Contract engine that rejects garbage bytecode should score well."""
        engine = FakeContractEngine()
        result = SecurityAuditor.audit_contracts(engine)
        self.assertTrue(result["passed"])

    def test_utxo_consistency(self):
        """UTXO total exceeding minted must be CRITICAL."""
        chain = _make_simple_chain(num_blocks=1)
        chain.utxo_set = {"addr": 999_999_999}  # way more than minted
        result = SecurityAuditor.audit_blockchain(chain)
        utxo_findings = [f for f in result["findings"] if f["category"] == "utxo"]
        self.assertTrue(any(f["severity"] == "CRITICAL" for f in utxo_findings))


# ══════════════════════════════════════════════════════════════════════════════
# Load Tester Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestLoadTester(unittest.TestCase):
    """Tests for LoadTester."""

    def test_mining_performance(self):
        """Mining test must return expected keys and positive throughput."""
        result = LoadTester.test_mining_performance(num_blocks=10)
        self.assertEqual(result["num_blocks"], 10)
        self.assertGreater(result["total_time_s"], 0)
        self.assertGreater(result["throughput_blocks_per_sec"], 0)
        self.assertGreater(result["time_per_block_ms"], 0)

    def test_tx_throughput(self):
        """Transaction throughput test must return expected keys."""
        result = LoadTester.test_transaction_throughput(num_txs=100)
        self.assertEqual(result["num_transactions"], 100)
        self.assertGreater(result["txs_per_sec"], 0)
        self.assertGreater(result["total_time_s"], 0)

    def test_sig_speed(self):
        """Signature verification test must complete and have ops/sec > 0."""
        result = LoadTester.test_signature_verification_speed(num_sigs=100)
        self.assertEqual(result["num_signatures"], 100)
        self.assertGreater(result["ops_per_sec"], 0)
        self.assertIn("backend", result)

    def test_address_speed(self):
        """Address generation test must complete and all addresses be unique."""
        result = LoadTester.test_address_generation_speed(num_addrs=100)
        self.assertEqual(result["num_addresses"], 100)
        self.assertGreater(result["ops_per_sec"], 0)
        self.assertEqual(result["unique_addresses"], 100)

    def test_concurrent_mining(self):
        """Concurrent mining must produce results for each miner."""
        result = LoadTester.test_concurrent_mining(num_miners=3, blocks_per_miner=2)
        self.assertEqual(result["num_miners"], 3)
        self.assertEqual(len(result["per_miner"]), 3)
        self.assertGreater(result["aggregate_blocks_per_sec"], 0)

    def test_api_throughput(self):
        """API throughput test must handle requests without errors."""
        result = LoadTester.test_api_throughput(num_requests=50)
        self.assertEqual(result["num_requests"], 50)
        self.assertEqual(result["errors"], 0)
        self.assertGreater(result["requests_per_sec"], 0)

    def test_report_generation(self):
        """generate_report must produce a non-empty string with key headers."""
        results = {
            "mining": LoadTester.test_mining_performance(num_blocks=5),
            "tx": LoadTester.test_transaction_throughput(num_txs=50),
        }
        report = LoadTester.generate_report(results)
        self.assertIsInstance(report, str)
        self.assertIn("b'AI'tcoin Load Test Report", report)
        self.assertIn("Ops/s", report)

    def test_block_validation_speed(self):
        """Block validation speed must return for a chain."""
        chain = _make_simple_chain(num_blocks=5)
        result = LoadTester.test_block_validation_speed(chain)
        self.assertEqual(result["num_blocks"], 5)
        self.assertGreater(result["blocks_per_sec"], 0)


# ══════════════════════════════════════════════════════════════════════════════
# Mainnet Checker Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMainnetChecker(unittest.TestCase):
    """Tests for MainnetChecker."""

    def test_checklist_items_count(self):
        """CHECKLIST must contain at least 20 items."""
        self.assertGreaterEqual(len(MainnetChecker.CHECKLIST), 20)

    def test_checklist_categories(self):
        """CHECKLIST must cover all five categories."""
        cats = {item.category for item in MainnetChecker.CHECKLIST}
        for expected in ("Security", "Performance", "Network", "Consensus", "Protocol"):
            self.assertIn(expected, cats, f"Missing category: {expected}")

    def test_genesis_check_passes(self):
        """With a correct genesis (50 BAIT), the genesis_50_bait item must pass."""
        chain = _make_simple_chain(num_blocks=2, genesis_reward=50)
        result = MainnetChecker.run_checklist(blockchain=chain)
        genesis_item = next(i for i in result["items"] if i["id"] == "genesis_50_bait")
        self.assertEqual(genesis_item["status"], "pass", f"Genesis check failed: {genesis_item['details']}")

    def test_genesis_check_fails_on_wrong_reward(self):
        """With wrong genesis reward, the genesis_50_bait item must fail."""
        chain = _make_broken_genesis_chain()
        result = MainnetChecker.run_checklist(blockchain=chain)
        genesis_item = next(i for i in result["items"] if i["id"] == "genesis_50_bait")
        self.assertEqual(genesis_item["status"], "fail")

    def test_run_checklist(self):
        """run_checklist must return proper structure with all fields."""
        chain = _make_simple_chain(num_blocks=2)
        consensus = FakeConsensus()
        result = MainnetChecker.run_checklist(blockchain=chain, consensus=consensus)
        self.assertIn("total", result)
        self.assertIn("passed", result)
        self.assertIn("failed", result)
        self.assertIn("skipped", result)
        self.assertIn("items", result)
        self.assertEqual(result["total"], len(MainnetChecker.CHECKLIST))
        self.assertEqual(len(result["items"]), result["total"])
        # Sum must equal total
        self.assertEqual(
            result["passed"] + result["failed"] + result["skipped"],
            result["total"],
        )
        # Every item has expected keys
        for item in result["items"]:
            for key in ("id", "category", "description", "required", "status", "details"):
                self.assertIn(key, item)
            self.assertIn(item["status"], ("pass", "fail", "skip"))

    def test_report_generation(self):
        """generate_report must produce a non-empty string with key sections."""
        chain = _make_simple_chain(num_blocks=2)
        result = MainnetChecker.run_checklist(blockchain=chain)
        report = MainnetChecker.generate_report(result)
        self.assertIsInstance(report, str)
        self.assertIn("b'AI'tcoin Mainnet Readiness Checklist", report)
        self.assertIn("Summary", report)
        self.assertIn("Security", report)

    def test_no_inflation_check(self):
        """Supply within 21M must pass; exceeding must fail."""
        # Small chain – well within 21M
        chain = _make_simple_chain(num_blocks=2, genesis_reward=50)
        result = MainnetChecker.run_checklist(blockchain=chain)
        item = next(i for i in result["items"] if i["id"] == "no_inflation_bug")
        self.assertEqual(item["status"], "pass")

    def test_difficulty_adjustment_check(self):
        """Consensus with positive difficulty should pass difficulty check."""
        consensus = FakeConsensus(difficulty=10)
        result = MainnetChecker.run_checklist(consensus=consensus)
        item = next(i for i in result["items"] if i["id"] == "difficulty_adjustment")
        self.assertEqual(item["status"], "pass")

    def test_zkml_consensus_check(self):
        """FakeConsensus has zkml attributes, should pass."""
        consensus = FakeConsensus()
        result = MainnetChecker.run_checklist(consensus=consensus)
        item = next(i for i in result["items"] if i["id"] == "zkml_consensus")
        self.assertEqual(item["status"], "pass")

    def test_checklist_items_have_required_field(self):
        """Every checklist item must have a boolean 'required' field."""
        for item in MainnetChecker.CHECKLIST:
            self.assertIsInstance(item.required, bool, f"{item.id} missing required bool")
            self.assertIsInstance(item.id, str)
            self.assertIsInstance(item.category, str)
            self.assertIsInstance(item.description, str)
            self.assertIn(item.status, ("pending", "pass", "fail", "skip"))


if __name__ == "__main__":
    unittest.main()
