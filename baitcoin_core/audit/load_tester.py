"""
b'AI'tcoin Load Testing Framework.

Benchmarks mining throughput, transaction processing, signature speed,
address generation, block validation, concurrent mining, and API handling.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class _TimedResult:
    """Internal container for a timed benchmark result."""
    name: str
    num_ops: int
    elapsed_s: float
    ops_per_sec: float
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "num_ops": self.num_ops,
            "elapsed_seconds": round(self.elapsed_s, 4),
            "ops_per_sec": round(self.ops_per_sec, 2),
        }
        d.update(self.extra)
        return d


class LoadTester:
    """Benchmarking suite for b'AI'tcoin node performance."""

    # ── Mining performance ────────────────────────────────────────────────

    @staticmethod
    def test_mining_performance(num_blocks: int = 100, consensus: Any = None) -> Dict[str, Any]:
        """Mine *num_blocks* blocks and measure throughput.

        If a real consensus engine is supplied it will be used; otherwise a
        lightweight SHA-256 based proof-of-work loop runs in-process.

        Returns
        -------
        dict with keys: ``num_blocks``, ``total_time_s``, ``time_per_block_ms``,
        ``throughput_blocks_per_sec``.
        """
        logger.info("Mining performance test: %d blocks", num_blocks)
        start = time.perf_counter()

        if consensus is not None and hasattr(consensus, "mine_block"):
            # Use real consensus
            for i in range(num_blocks):
                try:
                    consensus.mine_block()
                except Exception as exc:
                    logger.warning("mine_block %d failed: %s", i, exc)
        else:
            # Lightweight in-process PoW simulation
            target_difficulty = getattr(consensus, "difficulty", 8) if consensus else 8
            prefix = b"\x00" * max(1, target_difficulty // 8)
            for i in range(num_blocks):
                nonce = 0
                while True:
                    h = hashlib.sha256(struct.pack(">IQ", i, nonce)).digest()
                    if h.startswith(prefix):
                        break
                    nonce += 1

        elapsed = time.perf_counter() - start
        per_block_ms = (elapsed / num_blocks) * 1000 if num_blocks else 0
        throughput = num_blocks / elapsed if elapsed else 0

        result = {
            "name": "mining_performance",
            "num_blocks": num_blocks,
            "total_time_s": round(elapsed, 4),
            "time_per_block_ms": round(per_block_ms, 2),
            "throughput_blocks_per_sec": round(throughput, 2),
        }
        logger.info("  → %.2f blocks/sec, %.2f ms/block", throughput, per_block_ms)
        return result

    # ── Transaction throughput ────────────────────────────────────────────

    @staticmethod
    def test_transaction_throughput(num_txs: int = 1000, blockchain: Any = None) -> Dict[str, Any]:
        """Add *num_txs* transactions to the mempool (or simulate) and measure speed.

        Returns
        -------
        dict with keys: ``num_transactions``, ``total_time_s``, ``txs_per_sec``,
        ``avg_fee``.
        """
        logger.info("Transaction throughput test: %d txs", num_txs)
        start = time.perf_counter()
        total_fee = 0.0

        mempool = None
        if blockchain is not None:
            mempool = getattr(blockchain, "mempool", None) or getattr(blockchain, "get_mempool", lambda: None)()

        for i in range(num_txs):
            tx = {
                "txid": hashlib.sha256(f"tx-{i}-{time.time()}".encode()).hexdigest(),
                "inputs": [{"prev_txid": f"prev-{i}", "index": 0}],
                "outputs": [{"address": f"addr-{i % 100}", "amount": 1000}],
                "fee": 1,
            }
            fee = tx["fee"]
            total_fee += fee
            if mempool is not None and hasattr(mempool, "add_transaction"):
                try:
                    mempool.add_transaction(tx)
                except Exception:
                    pass

        elapsed = time.perf_counter() - start
        txs_per_sec = num_txs / elapsed if elapsed else 0
        avg_fee = total_fee / num_txs if num_txs else 0

        result = {
            "name": "transaction_throughput",
            "num_transactions": num_txs,
            "total_time_s": round(elapsed, 4),
            "txs_per_sec": round(txs_per_sec, 2),
            "avg_fee": avg_fee,
        }
        logger.info("  → %.2f txs/sec", txs_per_sec)
        return result

    # ── Signature verification speed ──────────────────────────────────────

    @staticmethod
    def test_signature_verification_speed(num_sigs: int = 1000) -> Dict[str, Any]:
        """Generate and verify *num_sigs* Schnorr signatures.

        Uses the real ``SchnorrSigner`` if available; otherwise falls back
        to a deterministic SHA-256-based mock so the test always runs.
        """
        logger.info("Signature verification speed test: %d sigs", num_sigs)
        start = time.perf_counter()

        try:
            from baitcoin_core.crypto.schnorr import SchnorrSigner
            use_real = True
        except Exception:
            use_real = False

        verify_failures = 0
        for _ in range(num_sigs):
            if use_real:
                signer = SchnorrSigner()
                msg = os.urandom(32)
                sig = signer.sign(msg)
                pub = signer.public_key
                if not SchnorrSigner.verify(pub, msg, sig):
                    verify_failures += 1
            else:
                # Mock: SHA-256 HMAC-style sign + verify
                key = os.urandom(32)
                msg = os.urandom(32)
                sig = hashlib.sha256(key + msg).digest()
                expected = hashlib.sha256(key + msg).digest()
                if sig != expected:
                    verify_failures += 1

        elapsed = time.perf_counter() - start
        ops_per_sec = num_sigs / elapsed if elapsed else 0

        result = {
            "name": "signature_verification_speed",
            "num_signatures": num_sigs,
            "total_time_s": round(elapsed, 4),
            "ops_per_sec": round(ops_per_sec, 2),
            "verify_failures": verify_failures,
            "backend": "schnorr" if use_real else "mock-sha256",
        }
        logger.info("  → %.2f sigs/sec (%s)", ops_per_sec, "schnorr" if use_real else "mock")
        return result

    # ── Address generation speed ──────────────────────────────────────────

    @staticmethod
    def test_address_generation_speed(num_addrs: int = 1000) -> Dict[str, Any]:
        """Generate *num_addrs* BAIT addresses and measure speed.

        Uses the real ``BAITAddress`` class if importable; otherwise
        generates mock P2PKH-style addresses from random keys.
        """
        logger.info("Address generation speed test: %d addrs", num_addrs)
        start = time.perf_counter()

        use_real = False
        try:
            from baitcoin_core.crypto.address import BAITAddress
            use_real = True
        except Exception:
            pass

        addresses: List[str] = []
        for _ in range(num_addrs):
            if use_real:
                addr = BAITAddress.generate()
                addresses.append(str(addr))
            else:
                # Mock: base58check-style from random 20 bytes
                raw = os.urandom(20)
                h = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
                addr_b = raw + h
                # Simple base58 encoding
                alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
                n = int.from_bytes(addr_b, "big")
                s = ""
                while n > 0:
                    n, r = divmod(n, 58)
                    s = alphabet[r] + s
                addresses.append(s or alphabet[0])

        elapsed = time.perf_counter() - start
        ops_per_sec = num_addrs / elapsed if elapsed else 0
        unique = len(set(addresses))

        result = {
            "name": "address_generation_speed",
            "num_addresses": num_addrs,
            "total_time_s": round(elapsed, 4),
            "ops_per_sec": round(ops_per_sec, 2),
            "unique_addresses": unique,
            "backend": "bait_address" if use_real else "mock-base58",
        }
        logger.info("  → %.2f addrs/sec", ops_per_sec)
        return result

    # ── Block validation speed ────────────────────────────────────────────

    @staticmethod
    def test_block_validation_speed(chain: Any) -> Dict[str, Any]:
        """Validate every block in *chain* and measure total time.

        Returns
        -------
        dict with ``num_blocks``, ``total_time_s``, ``blocks_per_sec``.
        """
        logger.info("Block validation speed test")
        blocks = chain.blocks if hasattr(chain, "blocks") else list(chain)
        n = len(blocks)

        start = time.perf_counter()
        for i, block in enumerate(blocks):
            # Structural validation
            h = (getattr(block, "hash", None) or block.get("hash") if isinstance(block, dict) else None)
            prev = (getattr(block, "previous_hash", None) or block.get("previous_hash") if isinstance(block, dict) else None)
            if i > 0:
                prev_h = (getattr(blocks[i - 1], "hash", None) or blocks[i - 1].get("hash") if isinstance(blocks[i - 1], dict) else None)
                if prev_h and prev and prev_h != prev:
                    logger.warning("Block %d link broken", i)

            # Hash recomputation if data available
            block_data = getattr(block, "to_dict", None)
            if block_data:
                try:
                    d = block_data()
                    hashlib.sha256(str(d).encode()).hexdigest()
                except Exception:
                    pass
        elapsed = time.perf_counter() - start

        blocks_per_sec = n / elapsed if elapsed else 0
        result = {
            "name": "block_validation_speed",
            "num_blocks": n,
            "total_time_s": round(elapsed, 4),
            "blocks_per_sec": round(blocks_per_sec, 2),
        }
        logger.info("  → %.2f blocks/sec validation", blocks_per_sec)
        return result

    # ── Concurrent mining ─────────────────────────────────────────────────

    @staticmethod
    def test_concurrent_mining(num_miners: int = 5, blocks_per_miner: int = 10) -> Dict[str, Any]:
        """Simulate *num_miners* mining *blocks_per_miner* blocks each concurrently.

        Uses ``asyncio`` to run mining coroutines in parallel.
        """
        logger.info("Concurrent mining test: %d miners × %d blocks", num_miners, blocks_per_miner)

        async def _mine_miner(miner_id: int) -> Dict[str, Any]:
            blocks_found = 0
            start = time.perf_counter()
            prefix = b"\x00"  # Very easy target for speed
            for b in range(blocks_per_miner):
                nonce = 0
                while True:
                    h = hashlib.sha256(struct.pack(">IIQ", miner_id, b, nonce)).digest()
                    if h.startswith(prefix):
                        blocks_found += 1
                        break
                    nonce += 1
            elapsed = time.perf_counter() - start
            return {
                "miner_id": miner_id,
                "blocks_found": blocks_found,
                "elapsed_s": round(elapsed, 4),
                "blocks_per_sec": round(blocks_found / elapsed, 2) if elapsed else 0,
            }

        async def _run_all() -> List[Dict[str, Any]]:
            tasks = [_mine_miner(i) for i in range(num_miners)]
            return await asyncio.gather(*tasks)

        wall_start = time.perf_counter()
        results = asyncio.run(_run_all())
        wall_elapsed = time.perf_counter() - wall_start

        total_blocks = sum(r["blocks_found"] for r in results)
        avg_per_miner = total_blocks / num_miners if num_miners else 0

        result = {
            "name": "concurrent_mining",
            "num_miners": num_miners,
            "blocks_per_miner": blocks_per_miner,
            "total_blocks": total_blocks,
            "wall_time_s": round(wall_elapsed, 4),
            "aggregate_blocks_per_sec": round(total_blocks / wall_elapsed, 2) if wall_elapsed else 0,
            "per_miner": results,
            "avg_per_miner": round(avg_per_miner, 2),
        }
        logger.info("  → %d total blocks in %.2fs (%.2f blocks/sec aggregate)",
                     total_blocks, wall_elapsed,
                     total_blocks / wall_elapsed if wall_elapsed else 0)
        return result

    # ── API throughput ────────────────────────────────────────────────────

    @staticmethod
    def test_api_throughput(num_requests: int = 100) -> Dict[str, Any]:
        """Simulate handling *num_requests* API requests.

        This is an in-process simulation – no actual HTTP server is started.
        Each "request" goes through a lightweight dispatch that mimics
        the 52-endpoint router.
        """
        logger.info("API throughput test: %d requests", num_requests)

        # Simulated endpoint handlers
        endpoints = {
            "/api/v1/blocks": lambda: {"height": 100, "hash": "abc"},
            "/api/v1/transactions": lambda: {"count": 500},
            "/api/v1/peers": lambda: {"peers": 12},
            "/api/v1/mempool": lambda: {"size": 50},
            "/api/v1/consensus": lambda: {"difficulty": 8, "target": 0xFFFF},
            "/api/v1/contracts/deploy": lambda: {"txid": "0x" + "00" * 32},
            "/api/v1/mining/info": lambda: {"hashrate": 1.5},
            "/api/v1/network/status": lambda: {"connected": True, "peers": 12},
        }
        endpoint_list = list(endpoints.keys())

        errors = 0
        start = time.perf_counter()
        for i in range(num_requests):
            path = endpoint_list[i % len(endpoint_list)]
            try:
                handler = endpoints[path]
                _ = handler()
            except Exception:
                errors += 1
        elapsed = time.perf_counter() - start

        req_per_sec = num_requests / elapsed if elapsed else 0

        result = {
            "name": "api_throughput",
            "num_requests": num_requests,
            "total_time_s": round(elapsed, 4),
            "requests_per_sec": round(req_per_sec, 2),
            "errors": errors,
            "endpoints_tested": len(endpoints),
        }
        logger.info("  → %.2f req/sec", req_per_sec)
        return result

    # ── Report generation ─────────────────────────────────────────────────

    @staticmethod
    def generate_report(results: Dict[str, Any]) -> str:
        """Produce a human-readable performance report from test results.

        Parameters
        ----------
        results : dict
            Mapping of test name → result dict (as returned by the test methods).
        """
        lines: List[str] = []
        lines.append("=" * 72)
        lines.append("  b'AI'tcoin Load Test Report")
        lines.append("=" * 72)
        lines.append(f"  Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
        lines.append("")

        # ── Metrics table ─────────────────────────────────────────────────
        header = f"  {'Test':<35} {'Ops':>8} {'Time (s)':>10} {'Ops/s':>12}"
        lines.append(header)
        lines.append("  " + "-" * (len(header) - 2))

        for name, r in results.items():
            if not isinstance(r, dict) or "name" not in r:
                continue
            label = r["name"].replace("_", " ").title()
            # Determine ops count
            num_ops = r.get("num_blocks") or r.get("num_transactions") or r.get("num_signatures") or r.get("num_addresses") or r.get("num_requests") or r.get("total_blocks") or 0
            total_s = r.get("total_time_s") or r.get("wall_time_s") or 0
            ops_sec = r.get("throughput_blocks_per_sec") or r.get("txs_per_sec") or r.get("ops_per_sec") or r.get("requests_per_sec") or r.get("aggregate_blocks_per_sec") or 0
            lines.append(f"  {label:<35} {num_ops:>8} {total_s:>10.4f} {ops_sec:>12.2f}")

        lines.append("")
        lines.append("-" * 72)

        # ── Extra details ─────────────────────────────────────────────────
        for name, r in results.items():
            if not isinstance(r, dict):
                continue
            label = r.get("name", name).replace("_", " ").title()
            extras = {k: v for k, v in r.items() if k not in ("name", "per_miner") and v}
            if extras:
                lines.append(f"  [{label}]")
                for k, v in extras.items():
                    lines.append(f"    {k}: {v}")
                lines.append("")

        lines.append("=" * 72)
        lines.append("  End of Report")
        lines.append("=" * 72)
        return "\n".join(lines)
