#!/usr/bin/env python3
"""
validate_baith.py — Standalone test runner for BAITHex (no pytest required).

Discovers and executes every `def test_*` function in:
  tests/baith_hex/test_exchange_policy.py
  tests/baith_hex/test_psbt_structure.py
  tests/baith_hex/test_obscura_baith_e2e.py
  tests/security/test_hsm_mpc.py

Reports per-test pass/fail + aggregate stats. Exits 0 on all pass, 1 on
any failure.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
import traceback
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

TEST_FILES = [
    "tests/baith_hex/test_exchange_policy.py",
    "tests/baith_hex/test_psbt_structure.py",
    "tests/baith_hex/test_obscura_baith_e2e.py",
    "tests/security/test_hsm_mpc.py",
]


def _install_pytest_stub():
    """Provide just enough pytest API used by the test files."""
    if "pytest" in sys.modules:
        return
    fake = types.ModuleType("pytest")

    def _raises(exc, match=None):
        class _Ctx:
            def __enter__(self):
                return self

            def __exit__(self, et, ev, tb):
                if et is None:
                    raise AssertionError(f"DID NOT RAISE {exc.__name__}")
                if not issubclass(et, exc):
                    return False
                if match is not None:
                    msg = str(ev) if ev else ""
                    import re
                    if not re.search(match, msg):
                        raise AssertionError(f"pattern {match!r} did not match {msg!r}")
                return True
        return _Ctx()

    fake.raises = _raises

    class _MonkeyPatch:
        """Minimal monkeypatch fixture."""
        _SENTINEL = object()

        def __init__(self):
            self._undo = []

        def setenv(self, name, value):
            old = os.environ.get(name)
            os.environ[name] = value
            self._undo.append(("env", name, old))

        def delenv(self, name, raising=True):
            old = os.environ.get(name)
            if name in os.environ:
                del os.environ[name]
            elif raising:
                raise AssertionError(f"env var {name!r} did not exist")
            self._undo.append(("env", name, old))

        def setattr(self, target, name, value):
            old = getattr(target, name, _MonkeyPatch._SENTINEL)
            setattr(target, name, value)
            self._undo.append(("attr", target, name, old))

        def undo(self):
            while self._undo:
                entry = self._undo.pop()
                if entry[0] == "env":
                    _, name, old = entry
                    if old is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = old
                elif entry[0] == "attr":
                    _, target, name, old = entry
                    if old is _MonkeyPatch._SENTINEL:
                        try:
                            delattr(target, name)
                        except AttributeError:
                            pass
                    else:
                        setattr(target, name, old)

    fake.MonkeyPatch = _MonkeyPatch

    def _fixture(fn):
        # Decorator form, not used by these tests but kept for completeness
        return fn

    fake.fixture = _fixture

    # Expose fixtures as module-level so tests can import them if they want
    fake.monkeypatch = _MonkeyPatch

    sys.modules["pytest"] = fake


# Fixtures available to inject into test functions by parameter name
_FIXTURES = {
    "monkeypatch": "monkeypatch",  # sentinel — actual class loaded lazily
}


def _make_monkeypatch():
    """Build a MonkeyPatch instance via the stub installed in sys.modules."""
    return sys.modules["pytest"].MonkeyPatch()


def _invoke(fn):
    """Invoke a test function, injecting known fixtures by parameter name."""
    sig = inspect.signature(fn)
    kwargs = {}
    mp = None
    for pname in sig.parameters:
        if pname == "monkeypatch":
            mp = _make_monkeypatch()
            kwargs[pname] = mp
    try:
        return fn(**kwargs)
    finally:
        if mp is not None:
            mp.undo()


def _load(unique: str, path: Path):
    spec = importlib.util.spec_from_file_location(unique, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    _install_pytest_stub()

    tests = []
    for i, rel in enumerate(TEST_FILES):
        path = ROOT / rel
        if not path.exists():
            print(f"  ✗ missing: {rel}")
            continue
        mod = _load(f"_baith_test_{i}", path)
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("test_"):
                tests.append((rel, name, fn))

    print(f"▶ discovered {len(tests)} tests across {len(TEST_FILES)} files")
    print()

    passed = []
    failed = []
    for rel, name, fn in tests:
        try:
            _invoke(fn)
            passed.append((rel, name))
            print(f"  ✓ {rel}:{name}")
        except Exception as e:
            failed.append((rel, name, e))
            tb_lines = traceback.format_exc().splitlines()
            tail = [l for l in tb_lines if "/baitcoin/" in l or "baith" in l.lower()][:2]
            print(f"  ✗ {rel}:{name} — {type(e).__name__}: {e}")
            for line in tail:
                print(f"      {line.strip()}")

    print()
    print("═══════════════════════════════════════════════════════════")
    print(f"  Passed: {len(passed)}/{len(tests)}")
    print(f"  Failed: {len(failed)}/{len(tests)}")
    if failed:
        print()
        print("  Failures:")
        for rel, name, e in failed:
            print(f"    ✗ {rel}:{name}: {type(e).__name__}: {e}")
        sys.exit(1)
    else:
        print("  ✅ BAITHex + HSM/MPC + Obscura suite PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()