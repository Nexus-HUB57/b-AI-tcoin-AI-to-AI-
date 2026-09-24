#!/usr/bin/env python3
"""
Atheris coverage-guided fuzzer for BAIT bridge *property predicates*
(pure Python model of conservation rules).

This does NOT execute EVM bytecode. It fuzzes the same logical invariants
that Echidna/Foundry enforce on-chain, as a fast offline gate + corpus seed.

Fallback: if atheris is not installed, runs a deterministic random campaign
and prints how to invoke Echidna.

Usage:
  pip install atheris
  python fuzz/atheris_bridge_props.py
  # or: ./fuzz/run_fuzzers.sh atheris
"""
from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass, field


@dataclass
class BridgeModel:
    """Minimal sequential model of lock/mint/burn conservation."""

    total_locked: int = 0
    total_minted: int = 0
    supply: int = 0
    rate_limit: int = 100_000 * 10**8
    daily_minted: dict = field(default_factory=dict)
    day: int = 0
    max_supply: int = 21_000_000 * 10**8
    consumed_l1: set = field(default_factory=set)
    pending: dict = field(default_factory=dict)  # id -> (recipient, amount, confs)

    def request(self, l1: bytes, recipient: int, amount: int) -> bool:
        if amount <= 0 or recipient == 0:
            return False
        if l1 in self.consumed_l1:
            return False
        if self.daily_minted.get(recipient, 0) + amount > self.rate_limit:
            return False
        self.consumed_l1.add(l1)
        self.total_locked += amount
        rid = len(self.pending)
        self.pending[rid] = [recipient, amount, 0]
        return True

    def confirm(self, rid: int) -> bool:
        if rid not in self.pending:
            return False
        p = self.pending[rid]
        if p[2] >= 3:
            return False
        p[2] += 1
        if p[2] >= 3:
            amount = p[1]
            recipient = p[0]
            if self.total_minted + amount > self.total_locked:
                return False  # would violate on-chain require
            if self.supply + amount > self.max_supply:
                return False
            self.total_minted += amount
            self.supply += amount
            self.daily_minted[recipient] = self.daily_minted.get(recipient, 0) + amount
            del self.pending[rid]
        return True

    def burn(self, amount: int) -> bool:
        if amount <= 0 or amount > self.supply:
            return False
        self.supply -= amount
        self.total_minted = max(0, self.total_minted - amount)
        return True

    def advance_day(self) -> None:
        self.day += 1
        self.daily_minted.clear()

    def ok(self) -> bool:
        return (
            self.total_minted <= self.total_locked
            and self.supply == self.total_minted
            and self.supply <= self.max_supply
        )


def _run_atheris() -> int:
    import atheris  # type: ignore

    model = BridgeModel()

    def TestOneInput(data: bytes) -> None:
        fdp = atheris.FuzzedDataProvider(data)
        steps = fdp.ConsumeIntInRange(1, 32)
        for _ in range(steps):
            op = fdp.ConsumeIntInRange(0, 3)
            if op == 0:
                l1 = fdp.ConsumeBytes(8)
                recipient = fdp.ConsumeIntInRange(1, 16)
                amount = fdp.ConsumeIntInRange(1, 50_000 * 10**8)
                model.request(l1, recipient, amount)
            elif op == 1:
                if model.pending:
                    rid = fdp.ConsumeIntInRange(0, max(model.pending.keys()))
                    model.confirm(rid)
            elif op == 2:
                amount = fdp.ConsumeIntInRange(0, max(1, model.supply))
                model.burn(amount)
            else:
                model.advance_day()
            if not model.ok():
                raise RuntimeError(
                    f"INVARIANT BROKEN minted={model.total_minted} "
                    f"locked={model.total_locked} supply={model.supply}"
                )

    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
    return 0


def _run_fallback(iterations: int = 20_000) -> int:
    """Deterministic random campaign without Atheris (CI / no deps)."""
    rng = random.Random(0xBA17)
    model = BridgeModel()
    for i in range(iterations):
        op = rng.randint(0, 3)
        if op == 0:
            model.request(rng.randbytes(8), rng.randint(1, 8), rng.randint(1, 10_000 * 10**8))
        elif op == 1 and model.pending:
            model.confirm(rng.choice(list(model.pending.keys())))
        elif op == 2:
            model.burn(rng.randint(0, max(1, model.supply)))
        else:
            model.advance_day()
        if not model.ok():
            print(f"FAIL at step {i}: {model}")
            return 1
    print(f"Atheris-fallback OK: {iterations} steps, minted={model.total_minted} locked={model.total_locked}")
    print("Echidna fallback:")
    print("  cd contracts && echidna . --contract EchidnaBridgeTester --config test/echidna.yaml")
    return 0


def main() -> int:
    try:
        import atheris  # noqa: F401

        return _run_atheris()
    except ImportError:
        print("atheris not installed — running deterministic fallback")
        return _run_fallback(int(os.environ.get("ATHERIS_FALLBACK_ITERS", "20000")))


if __name__ == "__main__":
    sys.exit(main())
