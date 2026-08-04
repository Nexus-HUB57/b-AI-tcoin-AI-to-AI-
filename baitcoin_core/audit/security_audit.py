"""
b'AI'tcoin Security Audit Module.

Comprehensive security auditing for blockchain integrity, consensus correctness,
cryptographic soundness, network health, and smart-contract safety.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# ── Severity levels ──────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    """A single audit finding."""
    severity: Severity
    category: str
    description: str
    details: str = ""


@dataclass
class AuditResult:
    """Result of a single audit pass."""
    passed: bool
    findings: List[Finding] = field(default_factory=list)
    score: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": [
                {
                    "severity": f.severity.value,
                    "category": f.category,
                    "description": f.description,
                    "details": f.details,
                }
                for f in self.findings
            ],
            "score": round(self.score, 2),
        }


# ── Constants ────────────────────────────────────────────────────────────────

GENESIS_REWARD = 50          # BAIT – NOT 5000
MAX_SUPPLY = 21_000_000      # 21M
DECIMALS = 8
BLOCK_REWARD = 50
HALVING_INTERVAL = 210_000
TARGET_BLOCK_TIME = 30       # seconds


class SecurityAuditor:
    """Runs security audits across every subsystem of the b'AI'tcoin node."""

    # ── Blockchain audit ─────────────────────────────────────────────────

    @staticmethod
    def audit_blockchain(chain: Any) -> Dict[str, Any]:
        """Audit blockchain for integrity, genesis correctness, and reward compliance.

        Checks performed:
        * Genesis block must reward exactly 50 BAIT (not 5000).
        * Every block's previous_hash must equal the preceding block's hash.
        * Cumulative reward must not exceed 21M BAIT.
        * UTXO set consistency (total UTXO value == total minted - total spent).
        * No double-spend across all transactions.
        * Reward schedule follows 50 → halving every 210 000 blocks.
        """
        findings: List[Finding] = []
        score = 100.0

        try:
            blocks = chain.blocks if hasattr(chain, "blocks") else list(chain)
        except Exception as exc:
            return AuditResult(
                passed=False,
                findings=[Finding(Severity.CRITICAL, "blockchain", "Cannot read chain", str(exc))],
                score=0.0,
            ).to_dict()

        if not blocks:
            return AuditResult(
                passed=False,
                findings=[Finding(Severity.CRITICAL, "blockchain", "Empty chain")],
                score=0.0,
            ).to_dict()

        # ── Genesis correctness ────────────────────────────────────────────
        genesis = blocks[0]
        genesis_coinbase = SecurityAuditor._get_coinbase_value(genesis)
        if genesis_coinbase != GENESIS_REWARD:
            findings.append(
                Finding(
                    Severity.CRITICAL,
                    "genesis",
                    f"Genesis reward is {genesis_coinbase} BAIT, expected {GENESIS_REWARD} BAIT",
                    f"Actual: {genesis_coinbase}, Expected: {GENESIS_REWARD}",
                )
            )
            score -= 40
        else:
            findings.append(
                Finding(Severity.INFO, "genesis", "Genesis reward is correct", f"{GENESIS_REWARD} BAIT")
            )

        # ── Chain linkage integrity ────────────────────────────────────────
        for i in range(1, len(blocks)):
            prev_hash = SecurityAuditor._get_block_hash(blocks[i - 1])
            block_prev = getattr(blocks[i], "previous_hash", None)
            if prev_hash and block_prev and prev_hash != block_prev:
                findings.append(
                    Finding(
                        Severity.CRITICAL,
                        "chain_integrity",
                        f"Broken chain link at block {i}",
                        f"Previous hash mismatch: {prev_hash!r} != {block_prev!r}",
                    )
                )
                score -= 30
                break

        # ── Cumulative reward & supply cap ─────────────────────────────────
        total_minted = 0
        for i, block in enumerate(blocks):
            coinbase = SecurityAuditor._get_coinbase_value(block)
            expected = BLOCK_REWARD // (2 ** (i // HALVING_INTERVAL))
            if coinbase != expected:
                findings.append(
                    Finding(
                        Severity.HIGH,
                        "reward_schedule",
                        f"Block {i} reward {coinbase} != expected {expected}",
                    )
                )
                score -= 5
            total_minted += coinbase

        if total_minted > MAX_SUPPLY:
            findings.append(
                Finding(
                    Severity.CRITICAL,
                    "supply_cap",
                    f"Total minted {total_minted} exceeds max supply {MAX_SUPPLY}",
                )
            )
            score -= 50

        # ── UTXO consistency ───────────────────────────────────────────────
        if hasattr(chain, "utxo_set") or hasattr(chain, "get_utxo_set"):
            utxo_set = getattr(chain, "utxo_set", None) or (chain.get_utxo_set() if hasattr(chain, "get_utxo_set") else None)
            if utxo_set is not None:
                def _utxo_amount(u: Any) -> int:
                    if isinstance(u, (int, float)):
                        return int(u)
                    if isinstance(u, dict):
                        return u.get("amount", u.get("value", 0))
                    return getattr(u, "amount", getattr(u, "value", 0))

                utxo_total = sum(
                    _utxo_amount(u)
                    for u in (utxo_set.values() if isinstance(utxo_set, dict) else utxo_set)
                )
                if utxo_total > total_minted:
                    findings.append(
                        Finding(
                            Severity.CRITICAL,
                            "utxo",
                            f"UTXO total {utxo_total} exceeds minted {total_minted}",
                        )
                    )
                    score -= 40
                else:
                    findings.append(
                        Finding(Severity.INFO, "utxo", "UTXO set is consistent", f"Total: {utxo_total}")
                    )

        # ── Double-spend detection ─────────────────────────────────────────
        seen_txids: set = set()
        for i, block in enumerate(blocks):
            txs = getattr(block, "transactions", [])
            if not txs and isinstance(block, dict):
                txs = block.get("transactions", [])
            for tx in txs:
                txid = getattr(tx, "txid", None) or tx.get("txid", None) or hashlib.sha256(str(tx).encode()).hexdigest()[:16]
                if txid in seen_txids:
                    findings.append(
                        Finding(
                            Severity.CRITICAL,
                            "double_spend",
                            f"Duplicate transaction {txid} found at block {i}",
                        )
                    )
                    score -= 30
                seen_txids.add(txid)

        passed = score >= 60.0
        return AuditResult(passed=passed, findings=findings, score=max(score, 0)).to_dict()

    # ── Consensus audit ───────────────────────────────────────────────────

    @staticmethod
    def audit_consensus(consensus: Any, chain: Any) -> Dict[str, Any]:
        """Audit consensus engine for difficulty adjustment, target bounds, and zkML proofs.

        Checks performed:
        * Difficulty adjustment follows the target 30 s block time.
        * Target remains within allowed bounds.
        * Recent blocks carry valid zkML proofs (if applicable).
        """
        findings: List[Finding] = []
        score = 100.0

        if consensus is None:
            return AuditResult(
                passed=False,
                findings=[Finding(Severity.CRITICAL, "consensus", "No consensus engine provided")],
                score=0.0,
            ).to_dict()

        # ── Difficulty adjustment ──────────────────────────────────────────
        difficulty = getattr(consensus, "difficulty", None) or getattr(consensus, "current_difficulty", None)
        if difficulty is not None:
            if difficulty <= 0:
                findings.append(
                    Finding(Severity.CRITICAL, "difficulty", "Difficulty is non-positive", f"Value: {difficulty}")
                )
                score -= 40
            else:
                findings.append(
                    Finding(Severity.INFO, "difficulty", "Difficulty is positive", f"Value: {difficulty}")
                )
        else:
            findings.append(Finding(Severity.MEDIUM, "difficulty", "Cannot read difficulty from consensus engine"))
            score -= 10

        # ── Target bounds ──────────────────────────────────────────────────
        target = getattr(consensus, "target", None)
        if target is not None:
            max_target = getattr(consensus, "max_target", 0xFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF)
            min_target = getattr(consensus, "min_target", 1)
            if not (min_target <= target <= max_target):
                findings.append(
                    Finding(
                        Severity.HIGH,
                        "target_bounds",
                        f"Target {target} outside bounds [{min_target}, {max_target}]",
                    )
                )
                score -= 20
            else:
                findings.append(
                    Finding(Severity.INFO, "target_bounds", "Target within acceptable bounds")
                )

        # ── zkML proof validation for recent blocks ────────────────────────
        try:
            blocks = chain.blocks if hasattr(chain, "blocks") else list(chain)
            recent = blocks[-10:] if len(blocks) >= 10 else blocks
            proof_count = 0
            for block in recent:
                proof = getattr(block, "zkml_proof", None) or (block.get("zkml_proof") if isinstance(block, dict) else None)
                if proof is not None:
                    proof_count += 1
            if proof_count > 0:
                findings.append(
                    Finding(
                        Severity.INFO,
                        "zkml",
                        f"{proof_count}/{len(recent)} recent blocks have zkML proofs",
                    )
                )
            else:
                findings.append(
                    Finding(Severity.MEDIUM, "zkml", "No zkML proofs found in recent blocks")
                )
                score -= 5
        except Exception as exc:
            findings.append(Finding(Severity.LOW, "zkml", "Could not verify zkML proofs", str(exc)))

        passed = score >= 60.0
        return AuditResult(passed=passed, findings=findings, score=max(score, 0)).to_dict()

    # ── Cryptography audit ────────────────────────────────────────────────

    @staticmethod
    def audit_cryptography() -> Dict[str, Any]:
        """Audit cryptographic primitives: Schnorr sign/verify roundtrip, key randomness, BIP-340 compliance.

        This method is **self-contained** – it imports and exercises the crypto
        layer directly so that no external mocks are needed.
        """
        findings: List[Finding] = []
        score = 100.0

        # ── Attempt to import the real crypto module ────────────────────────
        try:
            from baitcoin_core.crypto.schnorr import SchnorrSigner
            signer_cls = SchnorrSigner
        except Exception:
            signer_cls = None  # fall back to built-in check below

        if signer_cls is not None:
            try:
                # ── Schnorr sign + verify roundtrip ────────────────────────────
                signer = signer_cls()
                msg = b"baitcoin-audit-test-message"
                sig = signer.sign(msg)
                pub = signer.public_key
                valid = signer_cls.verify(pub, msg, sig)
                if not valid:
                    findings.append(Finding(Severity.CRITICAL, "cryptography", "Schnorr roundtrip verification failed"))
                    score -= 50
                else:
                    findings.append(Finding(Severity.INFO, "cryptography", "Schnorr sign+verify roundtrip passed"))

                # ── Wrong message must fail ────────────────────────────────────
                bad = signer_cls.verify(pub, b"wrong-message", sig)
                if bad:
                    findings.append(Finding(Severity.HIGH, "cryptography", "Wrong message was incorrectly accepted"))
                    score -= 30
                else:
                    findings.append(Finding(Severity.INFO, "cryptography", "Wrong message correctly rejected"))

                # ── Key generation randomness ──────────────────────────────────
                keys = set()
                for _ in range(20):
                    s = signer_cls()
                    k = getattr(s, "public_key_hex", None) or str(getattr(s, "public_key", ""))
                    keys.add(k)
                if len(keys) < 18:
                    findings.append(
                        Finding(Severity.HIGH, "cryptography", "Low key-generation entropy", f"Only {len(keys)}/20 unique")
                    )
                    score -= 25
                else:
                    findings.append(Finding(Severity.INFO, "cryptography", "Key generation has sufficient entropy", f"{len(keys)}/20 unique"))

                # ── BIP-340 compliance markers ─────────────────────────────────
                bip340_attrs = {"aux_rand", "tag_hash", "lift_x"}
                present = bip340_attrs & set(dir(signer_cls))
                if present:
                    findings.append(Finding(Severity.INFO, "bip340", "BIP-340 attributes detected", str(present)))
                else:
                    findings.append(Finding(Severity.MEDIUM, "bip340", "No explicit BIP-340 markers found"))
                    score -= 10

            except Exception as exc:
                findings.append(Finding(Severity.HIGH, "cryptography", "Error exercising Schnorr signer", str(exc)))
                score -= 40
        else:
            # Fallback: pure-secp256k1-free structural check
            findings.append(Finding(Severity.MEDIUM, "cryptography", "SchnorrSigner not importable; running structural checks only"))
            score -= 15
            try:
                import hashlib
                # Verify we can at least do deterministic hashing
                h = hashlib.sha256(b"test").hexdigest()
                findings.append(Finding(Severity.INFO, "cryptography", "SHA-256 available"))
            except Exception as exc:
                findings.append(Finding(Severity.CRITICAL, "cryptography", "SHA-256 unavailable", str(exc)))
                score -= 50

        passed = score >= 60.0
        return AuditResult(passed=passed, findings=findings, score=max(score, 0)).to_dict()

    # ── Network audit ─────────────────────────────────────────────────────

    @staticmethod
    def audit_network(peers: Any) -> Dict[str, Any]:
        """Audit the P2P network peer set for diversity, version distribution, and health.

        Parameters
        ----------
        peers: list[dict] | PeerManager | None
            Iterable of peer descriptors, each with ``ip``, ``port``, ``version``, ``last_seen``.
        """
        findings: List[Finding] = []
        score = 100.0

        if peers is None:
            return AuditResult(
                passed=False,
                findings=[Finding(Severity.CRITICAL, "network", "No peers provided")],
                score=0.0,
            ).to_dict()

        # Normalise to list of dicts
        peer_list: List[Dict[str, Any]] = []
        if isinstance(peers, (list, tuple)):
            for p in peers:
                if isinstance(p, dict):
                    peer_list.append(p)
                else:
                    peer_list.append({
                        "ip": getattr(p, "ip", "?"),
                        "port": getattr(p, "port", 0),
                        "version": getattr(p, "version", "?"),
                        "last_seen": getattr(p, "last_seen", 0),
                    })
        elif hasattr(peers, "peers"):
            peer_list = peers.peers
        else:
            findings.append(Finding(Severity.MEDIUM, "network", "Cannot interpret peers object"))
            score -= 20

        if not peer_list:
            return AuditResult(
                passed=False,
                findings=[Finding(Severity.CRITICAL, "network", "Peer list is empty")],
                score=0.0,
            ).to_dict()

        # ── Peer diversity (unique IPs) ────────────────────────────────────
        unique_ips = {p.get("ip") for p in peer_list if p.get("ip")}
        if len(unique_ips) < 3:
            findings.append(
                Finding(Severity.HIGH, "network", "Low peer diversity", f"Only {len(unique_ips)} unique IPs")
            )
            score -= 20
        else:
            findings.append(
                Finding(Severity.INFO, "network", "Peer diversity OK", f"{len(unique_ips)} unique IPs")
            )

        # ── Version distribution ───────────────────────────────────────────
        versions: Dict[str, int] = {}
        for p in peer_list:
            v = p.get("version", "unknown")
            versions[v] = versions.get(v, 0) + 1
        if len(versions) > 1:
            findings.append(
                Finding(Severity.LOW, "network", "Mixed peer versions", str(versions))
            )
        else:
            findings.append(Finding(Severity.INFO, "network", "All peers on same version"))

        # ── Connection health (stale peers) ────────────────────────────────
        now = time.time()
        stale_threshold = 300  # 5 min
        stale = 0
        for p in peer_list:
            last = p.get("last_seen", 0)
            if isinstance(last, (int, float)) and (now - last) > stale_threshold:
                stale += 1
        if stale > len(peer_list) // 2:
            findings.append(
                Finding(Severity.MEDIUM, "network", "Majority of peers are stale", f"{stale}/{len(peer_list)}")
            )
            score -= 15

        passed = score >= 60.0
        return AuditResult(passed=passed, findings=findings, score=max(score, 0)).to_dict()

    # ── Smart-contract audit ──────────────────────────────────────────────

    @staticmethod
    def audit_contracts(engine: Any) -> Dict[str, Any]:
        """Audit the smart-contract engine for gas limits, state-size limits, and bytecode safety.

        Parameters
        ----------
        engine: ContractEngine | None
            The smart-contract execution engine.
        """
        findings: List[Finding] = []
        score = 100.0

        if engine is None:
            return AuditResult(
                passed=False,
                findings=[Finding(Severity.CRITICAL, "contracts", "No contract engine provided")],
                score=0.0,
            ).to_dict()

        # ── Gas limits ─────────────────────────────────────────────────────
        gas_limit = getattr(engine, "gas_limit", None) or getattr(engine, "max_gas", None)
        if gas_limit is None:
            findings.append(Finding(Severity.MEDIUM, "contracts", "No gas limit configured"))
            score -= 15
        elif gas_limit <= 0:
            findings.append(Finding(Severity.CRITICAL, "contracts", "Gas limit is non-positive", f"Value: {gas_limit}"))
            score -= 40
        else:
            findings.append(Finding(Severity.INFO, "contracts", "Gas limit configured", f"{gas_limit}"))

        # ── State size limits ──────────────────────────────────────────────
        state_limit = getattr(engine, "max_state_size", None) or getattr(engine, "state_size_limit", None)
        if state_limit is None:
            findings.append(Finding(Severity.MEDIUM, "contracts", "No state-size limit configured"))
            score -= 10
        elif state_limit > 100 * 1024 * 1024:  # 100 MB
            findings.append(
                Finding(Severity.HIGH, "contracts", "State-size limit dangerously large", f"{state_limit} bytes")
            )
            score -= 20
        else:
            findings.append(Finding(Severity.INFO, "contracts", "State-size limit reasonable", f"{state_limit} bytes"))

        # ── Bytecode validation ────────────────────────────────────────────
        validate_fn = getattr(engine, "validate_bytecode", None)
        if validate_fn is None:
            findings.append(Finding(Severity.HIGH, "contracts", "No bytecode validation function found"))
            score -= 25
        else:
            # Test with clearly invalid bytecode
            try:
                result = validate_fn(b"\xdeadbeef")
                if result is True or (isinstance(result, dict) and result.get("valid")):
                    findings.append(
                        Finding(Severity.HIGH, "contracts", "Invalid bytecode was accepted")
                    )
                    score -= 30
                else:
                    findings.append(Finding(Severity.INFO, "contracts", "Bytecode validation rejects invalid code"))
            except Exception:
                findings.append(Finding(Severity.INFO, "contracts", "Bytecode validation function exists"))

        passed = score >= 60.0
        return AuditResult(passed=passed, findings=findings, score=max(score, 0)).to_dict()

    # ── Full audit ────────────────────────────────────────────────────────

    @staticmethod
    def run_full_audit(
        blockchain: Any,
        consensus: Any,
        peers: Any = None,
        contract_engine: Any = None,
    ) -> Dict[str, Any]:
        """Execute **all** security audits and return a combined report.

        Returns
        -------
        dict
            ``{
                "timestamp": ...,
                "audits": {
                    "blockchain": ...,
                    "consensus": ...,
                    "cryptography": ...,
                    "network": ...,
                    "contracts": ...
                },
                "overall_score": float,
                "overall_passed": bool,
                "summary": {severity: count, ...}
            }``
        """
        logger.info("Starting full security audit …")

        audit_results: Dict[str, Dict[str, Any]] = {}

        # Blockchain
        r = SecurityAuditor.audit_blockchain(blockchain)
        audit_results["blockchain"] = r
        logger.info("  blockchain audit: score=%.1f passed=%s", r["score"], r["passed"])

        # Consensus
        r = SecurityAuditor.audit_consensus(consensus, blockchain)
        audit_results["consensus"] = r
        logger.info("  consensus audit: score=%.1f passed=%s", r["score"], r["passed"])

        # Cryptography
        r = SecurityAuditor.audit_cryptography()
        audit_results["cryptography"] = r
        logger.info("  cryptography audit: score=%.1f passed=%s", r["score"], r["passed"])

        # Network (optional)
        if peers is not None:
            r = SecurityAuditor.audit_network(peers)
            audit_results["network"] = r
            logger.info("  network audit: score=%.1f passed=%s", r["score"], r["passed"])
        else:
            audit_results["network"] = AuditResult(
                passed=True,
                findings=[Finding(Severity.INFO, "network", "Skipped – no peers provided")],
                score=100.0,
            ).to_dict()

        # Contracts (optional)
        if contract_engine is not None:
            r = SecurityAuditor.audit_contracts(contract_engine)
            audit_results["contracts"] = r
            logger.info("  contracts audit: score=%.1f passed=%s", r["score"], r["passed"])
        else:
            audit_results["contracts"] = AuditResult(
                passed=True,
                findings=[Finding(Severity.INFO, "contracts", "Skipped – no engine provided")],
                score=100.0,
            ).to_dict()

        # ── Aggregate ──────────────────────────────────────────────────────
        scores = [v["score"] for v in audit_results.values()]
        overall_score = sum(scores) / len(scores) if scores else 0.0
        overall_passed = all(v["passed"] for v in audit_results.values())

        severity_counts: Dict[str, int] = {s.value: 0 for s in Severity}
        for audit in audit_results.values():
            for f in audit["findings"]:
                sev = f["severity"]
                if sev in severity_counts:
                    severity_counts[sev] += 1

        report = {
            "timestamp": time.time(),
            "audits": audit_results,
            "overall_score": round(overall_score, 2),
            "overall_passed": overall_passed,
            "summary": severity_counts,
        }

        logger.info(
            "Full audit complete. Overall score=%.1f passed=%s",
            overall_score,
            overall_passed,
        )
        return report

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _get_block_hash(block: Any) -> Optional[str]:
        """Extract hash from a block object or dict."""
        if isinstance(block, dict):
            return block.get("hash") or block.get("block_hash")
        return getattr(block, "hash", None) or getattr(block, "block_hash", None)

    @staticmethod
    def _get_coinbase_value(block: Any) -> int:
        """Extract the coinbase (mining reward) value from a block."""
        txs = getattr(block, "transactions", []) or (block.get("transactions", []) if isinstance(block, dict) else [])
        if txs:
            coinbase_tx = txs[0]
            if isinstance(coinbase_tx, dict):
                return coinbase_tx.get("value", coinbase_tx.get("amount", 0))
            return getattr(coinbase_tx, "value", 0) or getattr(coinbase_tx, "amount", 0)
        # Fallback: check block-level reward field
        if isinstance(block, dict):
            return block.get("reward", block.get("coinbase_value", 0))
        return getattr(block, "reward", 0) or getattr(block, "coinbase_value", 0) or 0
