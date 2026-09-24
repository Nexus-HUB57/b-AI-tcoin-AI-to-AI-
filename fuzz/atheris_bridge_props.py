#!/usr/bin/env python3
"""
Atheris coverage-guided fuzzer for BAIT bridge property predicates.

Improvements (no assert relaxation):
  - Seed corpus with happy-path sequences (request → 3 confirms → burn)
  - Biased op selection toward confirm after successful request
  - Structured mutations via FuzzedDataProvider + manual seed bytes

Usage:
  pip install atheris
  python fuzz/atheris_bridge_props.py                 # libFuzzer loop
  python fuzz/atheris_bridge_props.py --demo         # short biased campaign + metrics
  ATHERIS_FALLBACK_ITERS=50000 python fuzz/atheris_bridge_props.py
"""
from __future__ import annotations

import os
import random
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent / "corpus_atheris"


@dataclass
class BridgeModel:
    total_locked: int = 0
    total_minted: int = 0
    supply: int = 0
    rate_limit: int = 100_000 * 10**8
    daily_minted: dict = field(default_factory=dict)
    max_supply: int = 21_000_000 * 10**8
    consumed_l1: set = field(default_factory=set)
    pending: dict = field(default_factory=dict)
    hits: dict = field(
        default_factory=lambda: {
            "req_ok": 0,
            "req_bad_amt": 0,
            "req_dup_l1": 0,
            "req_rate": 0,
            "conf_miss": 0,
            "conf_inc": 0,
            "conf_mint": 0,
            "conf_inv_block": 0,
            "burn_ok": 0,
            "burn_bad": 0,
            "day": 0,
        }
    )
    last_rid: int | None = None

    def request(self, l1: bytes, recipient: int, amount: int) -> bool:
        if amount <= 0 or recipient == 0:
            self.hits["req_bad_amt"] += 1
            return False
        if l1 in self.consumed_l1:
            self.hits["req_dup_l1"] += 1
            return False
        if self.daily_minted.get(recipient, 0) + amount > self.rate_limit:
            self.hits["req_rate"] += 1
            return False
        self.consumed_l1.add(l1)
        self.total_locked += amount
        rid = len(self.pending) + 1
        while rid in self.pending:
            rid += 1
        self.pending[rid] = [recipient, amount, 0]
        self.last_rid = rid
        self.hits["req_ok"] += 1
        return True

    def confirm(self, rid: int) -> bool:
        if rid not in self.pending:
            self.hits["conf_miss"] += 1
            return False
        p = self.pending[rid]
        if p[2] >= 3:
            self.hits["conf_miss"] += 1
            return False
        p[2] += 1
        self.hits["conf_inc"] += 1
        if p[2] >= 3:
            amount, recipient = p[1], p[0]
            # ASSERT — never relax
            if self.total_minted + amount > self.total_locked:
                self.hits["conf_inv_block"] += 1
                p[2] -= 1
                return False
            if self.supply + amount > self.max_supply:
                self.hits["conf_inv_block"] += 1
                p[2] -= 1
                return False
            self.total_minted += amount
            self.supply += amount
            self.daily_minted[recipient] = self.daily_minted.get(recipient, 0) + amount
            del self.pending[rid]
            if self.last_rid == rid:
                self.last_rid = None
            self.hits["conf_mint"] += 1
        return True

    def burn(self, amount: int) -> bool:
        if amount <= 0 or amount > self.supply:
            self.hits["burn_bad"] += 1
            return False
        self.supply -= amount
        self.total_minted = max(0, self.total_minted - amount)
        self.hits["burn_ok"] += 1
        return True

    def advance_day(self) -> None:
        self.daily_minted.clear()
        self.hits["day"] += 1

    def ok(self) -> bool:
        return (
            self.total_minted <= self.total_locked
            and self.supply == self.total_minted
            and self.supply <= self.max_supply
        )


def _pack_happy_path(seed: int, amount: int, recipient: int) -> bytes:
    """Encode a structured sequence: req + 3x confirm-last + optional burn.

    Layout (little-endian hints for FuzzedDataProvider-style consumption):
      [n_steps=5 u8][op=0][l1 8][recipient u16][amount u64]
      [op=1][op=1][op=1]  — confirms use last_rid bias in TestOneInput
      [op=2][burn_frac u8]
    """
    buf = bytearray()
    buf.append(6)  # steps
    # request
    buf.append(0)
    buf.extend(struct.pack("<Q", seed)[:8].ljust(8, b"\x00"))
    buf.extend(struct.pack("<H", recipient))
    buf.extend(struct.pack("<Q", amount))
    # three confirms (bias path)
    buf.extend(b"\x01\x01\x01")
    # burn up to 50%
    buf.append(2)
    buf.append(50)
    return bytes(buf)


def write_seed_corpus() -> list[bytes]:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    seeds: list[bytes] = []
    specs = [
        (1, 1_000 * 10**8, 1),
        (2, 10_000 * 10**8, 2),
        (3, 50_000 * 10**8, 3),
        (4, 1, 1),
        (5, 99_999 * 10**8, 4),
    ]
    for i, (s, amt, rec) in enumerate(specs):
        data = _pack_happy_path(s, amt, rec)
        seeds.append(data)
        (CORPUS_DIR / f"happy_{i}.bin").write_bytes(data)
    # edge: zero amount / zero recipient (negative paths — still useful edges)
    seeds.append(b"\x02\x00" + b"\x00" * 16)
    seeds.append(b"\x03\x02\xff" + b"\x00" * 8)
    (CORPUS_DIR / "neg_zero.bin").write_bytes(seeds[-2])
    return seeds


def run_biased_steps(model: BridgeModel, fdp_data: bytes, rng: random.Random | None = None) -> None:
    """Consume bytes with happy-path bias: after req_ok, prefer confirming last_rid."""
    rng = rng or random.Random()
    # Prefer structured parse when long enough
    i = 0

    def take(n: int) -> bytes:
        nonlocal i
        if i >= len(fdp_data):
            return rng.randbytes(n)
        chunk = fdp_data[i : i + n]
        i += n
        if len(chunk) < n:
            chunk += rng.randbytes(n - len(chunk))
        return chunk

    n_steps = take(1)[0] % 16 + 1
    for _ in range(n_steps):
        # Bias: 40% confirm if pending, 25% request, 20% burn, 15% day
        if model.pending and rng.random() < 0.40:
            op = 1
        else:
            r = rng.random()
            if r < 0.35:
                op = 0
            elif r < 0.55:
                op = 2
            elif r < 0.70:
                op = 3
            else:
                op = take(1)[0] % 4

        if op == 0:
            l1 = take(8)
            recipient = int.from_bytes(take(2), "little") % 16
            amount = int.from_bytes(take(8), "little") % (100_000 * 10**8)
            model.request(l1, recipient, amount)
        elif op == 1:
            if model.last_rid is not None and model.last_rid in model.pending:
                model.confirm(model.last_rid)
            elif model.pending:
                rid = rng.choice(list(model.pending.keys()))
                model.confirm(rid)
            else:
                model.confirm(int.from_bytes(take(2), "little"))
        elif op == 2:
            if model.supply > 0:
                frac = take(1)[0] % 100 + 1
                amount = max(1, (model.supply * frac) // 100)
                model.burn(amount)
            else:
                model.burn(int.from_bytes(take(4), "little"))
        else:
            model.advance_day()

        if not model.ok():
            raise RuntimeError(
                f"INVARIANT minted={model.total_minted} locked={model.total_locked} supply={model.supply}"
            )


def _run_demo(iterations: int = 5000) -> int:
    seeds = write_seed_corpus()
    model = BridgeModel()
    rng = random.Random(0xBA17)
    # Replay seeds first (stable coverage bootstrap)
    for s in seeds:
        run_biased_steps(model, s, rng)
    for _ in range(iterations):
        # Mutation strategies mixed:
        # 1) splice two seeds  2) bit flip  3) pure random  4) interesting integers
        strategy = rng.randint(0, 3)
        if strategy == 0 and len(seeds) >= 2:
            a, b = rng.choice(seeds), rng.choice(seeds)
            cut = rng.randint(0, min(len(a), len(b)))
            data = a[:cut] + b[cut:]
        elif strategy == 1 and seeds:
            data = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 8)):
                if not data:
                    break
                idx = rng.randrange(len(data))
                data[idx] ^= 1 << rng.randint(0, 7)
            data = bytes(data)
        elif strategy == 2:
            data = rng.randbytes(rng.randint(16, 128))
        else:
            # interesting constants (libFuzzer-style)
            data = struct.pack(
                "<BQQH",
                rng.randint(4, 12),
                rng.choice([0, 1, 2**32 - 1, 10**8, 100_000 * 10**8]),
                rng.randint(0, 7),
                rng.randint(0, 15),
            ) + rng.randbytes(32)
        run_biased_steps(model, data, rng)

    h = model.hits
    total = sum(h.values()) or 1
    print("=== Biased + seeded campaign ===")
    print(f"minted={model.total_minted} locked={model.total_locked} supply={model.supply} pending={len(model.pending)}")
    for k, v in sorted(h.items(), key=lambda x: -x[1]):
        print(f"  {k:16s} {v:8d}  ({100.0 * v / total:5.1f}%)")
    covered = sum(1 for v in h.values() if v > 0)
    print(f"branches {covered}/{len(h)} | conf_mint={h['conf_mint']} conf_inv_block={h['conf_inv_block']}")
    if h["conf_inv_block"] != 0:
        print("FAIL: invariant block path should stay 0 under correct model")
        return 1
    if h["conf_mint"] < 10:
        print("WARN: low conf_mint — seeds/bias may need stronger weight")
    else:
        print("OK: happy-path mint exercised")
    return 0


def _run_atheris() -> int:
    import atheris  # type: ignore

    write_seed_corpus()
    model = BridgeModel()

    def TestOneInput(data: bytes) -> None:
        # Keep assert strict
        run_biased_steps(model, data, random.Random(sum(data) & 0xFFFFFFFF))

    # Seed corpus directory for libFuzzer if supported via argv
    argv = [sys.argv[0], str(CORPUS_DIR), f"-max_total_time={os.environ.get('ATHERIS_MAX_TIME', '30')}"]
    atheris.Setup(argv, TestOneInput, enable_python_coverage=True)
    atheris.Fuzz()
    return 0


def _run_fallback(iterations: int = 20_000) -> int:
    print("atheris not installed — deterministic biased fallback")
    return _run_demo(iterations)


def main() -> int:
    if "--demo" in sys.argv:
        return _run_demo(int(os.environ.get("ATHERIS_DEMO_ITERS", "5000")))
    try:
        import atheris  # noqa: F401

        if os.environ.get("ATHERIS_DEMO_ONLY") == "1":
            return _run_demo()
        return _run_atheris()
    except ImportError:
        return _run_fallback(int(os.environ.get("ATHERIS_FALLBACK_ITERS", "20000")))


if __name__ == "__main__":
    sys.exit(main())
