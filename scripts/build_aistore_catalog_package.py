#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from baitcoin_ai.aipkg import build_catalog, build_package

SOURCE = ROOT / "packages" / "mcp" / "aistore-catalog"
DIST = ROOT / "packages" / "dist"
ARTIFACT = DIST / "aistore-catalog-mcp-1.0.0.aipkg"


def main() -> int:
    build_package(SOURCE, ARTIFACT, {
        "package_id": "aistore-catalog-mcp",
        "name": "AI Store Catalog MCP",
        "version": "1.0.0",
        "description": "Read-only MCP catalog search for verified AI Store packages",
        "entrypoint": "server.py",
        "publisher": {"id": "nexus-hub57", "name": "Nexus-HUB57"},
        "capabilities": ["catalog_search", "package_metadata"],
        "permissions": {"network": "none", "filesystem": "read-only", "secrets": "none"},
    })
    catalog = build_catalog([ARTIFACT], DIST / "catalog.json")
    print(f"built {ARTIFACT} ({ARTIFACT.stat().st_size} bytes)")
    print(f"catalog packages: {len(catalog['packages'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
