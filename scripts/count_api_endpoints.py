#!/usr/bin/env python3
"""
count_api_endpoints.py — Singleton source of truth for the REST endpoint count.

Reads `baitcoin_api/server.py` and computes the number of unique HTTP
endpoint paths reachable through the `BaitcoinAPI` daemon:

  - GET routes dict (do_GET, ~46 entries)
  - POST routes dict (do_POST, ~15 entries)
  - Dynamic parameterized paths de-duplicated by pattern
  - OPTIONS pre-flight endpoint (CORS)

The result is written as a "N endpoints REST" string into:
  - netlify/index.html (deploy via mybait.org)
  - frontend/index.html (deploy via render.com)

…so the CI check in `.github/workflows/deploy-render.yml` stays in lock-step
with reality even as routes are added or removed. The CI check itself is
also driven by this script (see --gate).

Usage:
    python3 scripts/count_api_endpoints.py                # print paths
    python3 scripts/count_api_endpoints.py --update-html  # patch HTMLs
    python3 scripts/count_api_endpoints.py --gate 60      # exit 0 if >= N
    python3 scripts/count_api_endpoints.py --json          # JSON output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "baitcoin_api" / "server.py"

# Patterns we consider an endpoint entry in *either* routes dict:
#   '/api/...': self._handler
#   '/api/...': self._handler_method
ROUTE_RE = re.compile(
    r"""['"](?P<path>/[a-zA-Z0-9_\-/<>{}]+)['"]\s*:\s*self\._(?P<handler>[a-zA-Z0-9_]+)"""
)

# Normalize dynamic path segments: /api/v1/block/<height> -> /api/v1/block/<param>
DYNAMIC_SEGMENT_RE = re.compile(r"/<[^>]+>")


def _dedupe_dynamic(paths: list[str]) -> list[str]:
    """Collapse parameterized segments (<height>, <txid>, ...) to a single token."""
    out: list[str] = []
    seen: set[str] = set()
    for p in paths:
        norm = DYNAMIC_SEGMENT_RE.sub("/<param>", p)
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    return sorted(out)


def count() -> tuple[int, list[str]]:
    if not SERVER.exists():
        print(f"server.py not found at {SERVER}", file=sys.stderr)
        sys.exit(2)
    src = SERVER.read_text()
    raw = [m.group("path") for m in ROUTE_RE.finditer(src)]
    paths = _dedupe_dynamic(raw)
    # +1 for the implicit OPTIONS pre-flight (CORS)
    return len(paths) + 1, paths + ["<OPTIONS pre-flight (CORS)>"]


def update_html(n: int) -> int:
    """Replace '<digits>+? endpoints? REST' (any prior phrasing) with the new count."""
    pattern = re.compile(r"\b\d+\+? *endpoints? *REST\b", re.IGNORECASE)
    replaced = 0
    for rel in ("netlify/index.html", "frontend/index.html"):
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text()
        new_text = pattern.sub(f"{n} endpoints REST", text)
        if new_text != text:
            p.write_text(new_text)
            replaced += 1
            print(f"  ✓ {rel}: updated to \"{n} endpoints REST\"")
    return replaced


def gate(min_required: int, actual: int) -> int:
    """Exit 0 if actual >= min_required. Print useful diagnostics."""
    print(f"  endpoint count: {actual}")
    print(f"  threshold:     >= {min_required}")
    if actual < min_required:
        print(f"  ❌ FAIL: endpoint count {actual} < threshold {min_required}")
        return 1
    print(f"  ✅ PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-html", action="store_true",
                    help="Patch netlify/index.html + frontend/index.html in place")
    ap.add_argument("--json", action="store_true", help="Output JSON to stdout")
    ap.add_argument("--gate", type=int, metavar="MIN", default=None,
                    help="Exit 0 if endpoint count >= MIN, else 1 (for CI)")
    args = ap.parse_args()

    n, paths = count()

    if args.update_html:
        update_html(n)
    elif args.gate is not None:
        sys.exit(gate(args.gate, n))
    elif args.json:
        print(json.dumps({"count": n, "paths": paths}, indent=2))
    else:
        print(f"  baitcoin_api REST endpoints: {n}")
        for p in paths:
            print(f"    {p}")


if __name__ == "__main__":
    main()