#!/usr/bin/env python3
"""
Generate .aipkg manifests for every MCP server in the b'AI'tcoin MCP portfolio.

Reads each `servers/<name>/server.py` and `servers/<name>/manifest.json`
and writes a consolidated `portfolio.json` plus individual `.aipkg` archives.

Usage:
    python scripts/build_all_manifests.py
    python scripts/build_all_manifests.py --out dist/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVERS = ROOT / "servers"


def sha256(buf: bytes) -> str:
    return hashlib.sha256(buf).hexdigest()


def collect_manifests() -> list[dict]:
    out = []
    for server_dir in sorted(SERVERS.iterdir()):
        if not server_dir.is_dir():
            continue
        mp = server_dir / "manifest.json"
        if not mp.exists():
            print(f"  skip {server_dir.name} (no manifest.json)")
            continue
        try:
            m = json.loads(mp.read_text())
        except json.JSONDecodeError as e:
            print(f"  ! {server_dir.name}: {e}")
            continue
        out.append({"name": m["name"], "version": m["version"], "category": m["category"], "manifest": m})
        print(f"  ✓ {m['name']} v{m['version']} ({m['category']})")
    return out


def pack(manifest_entry: dict, out_dir: Path) -> Path:
    name = manifest_entry["name"]
    version = manifest_entry["version"]
    server_dir = SERVERS / name.replace("mcp-", "")

    out_path = out_dir / f"{name}-{version}.aipkg"
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as z:
        # manifest.json
        z.writestr("manifest.json", json.dumps(manifest_entry["manifest"], indent=2))
        # server files
        if server_dir.exists():
            for p in server_dir.glob("*.py"):
                z.write(p, arcname=f"server/{p.name}")
        # checksum
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

    portfolio = {
        "name": "b'AI'tcoin MCP Portfolio",
        "version": "1.0.0",
        "description": "Full portfolio of MCP servers for the b'AI'tcoin / Nexus AI-OS ecosystem.",
        "publisher": "Nexus-HUB57",
        "count": len(entries),
        "servers": [e["manifest"] for e in entries],
    }
    portfolio_path = out_dir / "portfolio.json"
    portfolio_path.write_text(json.dumps(portfolio, indent=2))
    print(f"✓ portfolio → {portfolio_path} ({len(entries)} servers)")

    print("▶ packing .aipkg archives...")
    for entry in entries:
        p = pack(entry, out_dir)
        print(f"  ✓ {p.name} ({p.stat().st_size} bytes)")

    print(f"\n✅ done. {len(entries)} MCPs in {out_dir}")


if __name__ == "__main__":
    main()