#!/usr/bin/env python3
"""
build_all_manifests.py — Build the b'AI'tcoin MCP portfolio (.aipkg + portfolio.json).

Scans recursively:
  servers/<name>/manifest.json
  servers/<wave>/<name>/manifest.json   (wave3/wave4/wave5/wave6)

Produces:
  dist/portfolio.json
  dist/mcp-<name>-<version>.aipkg      (one per MCP)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVERS = ROOT / "servers"


def collect_manifests() -> list[dict]:
    """Walk SERVERS, pick up every server.py + manifest.json pair."""
    out = []
    if not SERVERS.exists():
        return out
    # Top-level servers (Wave 1+2)
    for d in sorted(SERVERS.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in ("__pycache__",):
            continue
        mp = d / "manifest.json"
        if not mp.exists():
            continue
        try:
            m = json.loads(mp.read_text())
        except json.JSONDecodeError as e:
            print(f"  ! {d.name}: {e}")
            continue
        out.append({"name": m["name"], "version": m["version"], "category": m["category"], "manifest": m, "server_dir": d, "wave": "core"})
        print(f"  ✓ {m['name']} v{m['version']} ({m['category']})")
    # Wave folders (wave3/wave4/wave5/wave6)
    for wave_dir in sorted([d for d in SERVERS.iterdir() if d.is_dir() and d.name.startswith("wave")]):
        wave_name = wave_dir.name
        for d in sorted(wave_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            mp = d / "manifest.json"
            if not mp.exists():
                continue
            try:
                m = json.loads(mp.read_text())
            except json.JSONDecodeError as e:
                print(f"  ! {wave_name}/{d.name}: {e}")
                continue
            out.append({"name": m["name"], "version": m["version"], "category": m["category"], "manifest": m, "server_dir": d, "wave": wave_name})
    return out


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def pack(entry: dict, out_dir: Path) -> Path:
    name = entry["name"]
    version = entry["version"]
    server_dir = entry["server_dir"]
    out_path = out_dir / f"{_safe_filename(name)}-{version}.aipkg"

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as z:
        z.writestr("manifest.json", json.dumps(entry["manifest"], indent=2))
        if server_dir.exists():
            for p in server_dir.glob("*.py"):
                z.write(p, arcname=f"server/{p.name}")
        if not [n for n in out_path.parent.glob(f"{_safe_filename(name)}-{version}.aipkg.tmp")]:
            pass
        # Compute checksum
        sha = hashlib.sha256()
        for info in z.infolist():
            if info.filename == "checksum.sha256":
                continue
            sha.update(info.filename.encode() + b"\n")
            sha.update(z.read(info.filename) + b"\n")
        z.writestr("checksum.sha256", f"{sha.hexdigest()}  .\n")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist", help="output directory")
    args = parser.parse_args()

    out_dir = ROOT / args.out
    out_dir.mkdir(exist_ok=True)

    print(f"▶ collecting from {SERVERS}")
    entries = collect_manifests()

    # Portfolio summary
    wave_counts = {}
    for e in entries:
        wave_counts[e["wave"]] = wave_counts.get(e["wave"], 0) + 1

    portfolio = {
        "name": "b'AI'tcoin MCP Portfolio",
        "version": "1.0.0",
        "description": "Massively scaled MCP portfolio across core, meta, and matrix-generated variants (Wave 1-6).",
        "publisher": "Nexus-HUB57",
        "count": len(entries),
        "waves": wave_counts,
        "servers": [e["manifest"] for e in entries],
    }
    portfolio_path = out_dir / "portfolio.json"
    portfolio_path.write_text(json.dumps(portfolio, indent=2))
    print(f"✓ portfolio → {portfolio_path} ({len(entries)} servers across {len(wave_counts)} wave folders)")
    print(f"  wave breakdown: {wave_counts}")

    print("▶ packing .aipkg archives...")
    packed = 0
    for entry in entries:
        try:
            pack(entry, out_dir)
            packed += 1
        except Exception as e:
            print(f"  ✗ {entry['name']}: {e}")
    print(f"\n✅ done. {packed}/{len(entries)} MCPs packed in {out_dir}")


if __name__ == "__main__":
    main()