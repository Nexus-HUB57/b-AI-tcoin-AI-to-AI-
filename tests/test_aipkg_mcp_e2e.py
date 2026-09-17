import json
import subprocess
import sys
import zipfile
from pathlib import Path

from baitcoin_ai.aipkg import AIPkgError, build_catalog, build_package, inspect_package


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SOURCE = ROOT / "packages" / "mcp" / "aistore-catalog"


def _metadata():
    return {
        "package_id": "aistore-catalog-mcp",
        "name": "AI Store Catalog MCP",
        "version": "1.0.0",
        "description": "Read-only MCP catalog search for verified AI Store packages",
        "entrypoint": "server.py",
        "publisher": {"id": "nexus-hub57", "name": "Nexus-HUB57"},
        "capabilities": ["catalog_search", "package_metadata"],
        "permissions": {"network": "none", "filesystem": "read-only", "secrets": "none"},
    }


def test_build_and_inspect_aipkg_is_hash_verified(tmp_path):
    artifact = tmp_path / "aistore-catalog-mcp.aipkg"
    manifest = build_package(PACKAGE_SOURCE, artifact, _metadata())
    assert manifest["package_id"] == "aistore-catalog-mcp"
    inspected = inspect_package(artifact)
    assert inspected["files"]["server.py"]
    assert inspected["permissions"]["network"] == "none"

    catalog = tmp_path / "catalog.json"
    result = build_catalog([artifact], catalog)
    assert result["packages"][0]["artifact"] == artifact.name
    assert json.loads(catalog.read_text())["packages"][0]["artifact_sha256"]


def test_inspect_rejects_tampered_aipkg(tmp_path):
    artifact = tmp_path / "tampered.aipkg"
    build_package(PACKAGE_SOURCE, artifact, _metadata())
    tampered = tmp_path / "tampered-rebuilt.aipkg"
    with zipfile.ZipFile(artifact) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "server.py":
                content += b"\n# unauthorized change\n"
            target.writestr(info, content)
    tampered.replace(artifact)
    try:
        inspect_package(artifact)
    except AIPkgError:
        pass
    else:
        raise AssertionError("tampered archive was accepted")


def test_mcp_catalog_server_searches_without_network(tmp_path):
    # Build a verified artifact and place its catalog next to the server copy.
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    for name in ("server.py", "catalog.json"):
        (package_dir / name).write_bytes((PACKAGE_SOURCE / name).read_bytes())
    catalog = {
        "schema_version": 1,
        "catalog_type": "aistore-local",
        "packages": [{
            "package_id": "demo-agent",
            "name": "Demo Agent",
            "version": "1.0.0",
            "description": "A catalog demo",
            "capabilities": ["catalog_search"],
            "artifact": "demo-agent.aipkg",
            "artifact_sha256": "a" * 64,
        }],
    }
    (package_dir / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "search_packages", "arguments": {"capability": "catalog_search"}
    }}
    proc = subprocess.run(
        [sys.executable, str(package_dir / "server.py")],
        input=json.dumps(request) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    response = json.loads(proc.stdout)
    packages = response["result"]["content"][0]["json"]["packages"]
    assert [item["package_id"] for item in packages] == ["demo-agent"]
