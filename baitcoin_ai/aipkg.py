"""Deterministic, locally verifiable AI Store package (.aipkg) format.

An .aipkg is a ZIP archive containing a manifest.json and package files. The
builder never executes package code; it only hashes and archives declared
files. Package permissions are explicit and restricted to a small allowlist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PACKAGE_SUFFIX = ".aipkg"
_PACKAGE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_ALLOWED_PERMISSIONS = {"network", "filesystem", "secrets"}
_ALLOWED_PERMISSION_VALUES = {"none", "read-only", "read-write"}


class AIPkgError(ValueError):
    """Raised when an .aipkg manifest or archive is invalid."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version", "package_id", "name", "version", "type", "entrypoint", "publisher", "permissions", "files"}
    missing = sorted(required - manifest.keys())
    if missing:
        raise AIPkgError(f"manifest missing fields: {', '.join(missing)}")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise AIPkgError("unsupported manifest schema_version")
    if not isinstance(manifest["package_id"], str) or not _PACKAGE_ID.fullmatch(manifest["package_id"]):
        raise AIPkgError("package_id must be lowercase kebab-case, 3-64 characters")
    if not isinstance(manifest["version"], str) or not _VERSION.fullmatch(manifest["version"]):
        raise AIPkgError("version must use semantic versioning")
    if manifest["type"] != "mcp":
        raise AIPkgError("only type=mcp is supported")
    if not isinstance(manifest["entrypoint"], str) or not manifest["entrypoint"] or manifest["entrypoint"].startswith("/"):
        raise AIPkgError("entrypoint must be a relative path")
    if not isinstance(manifest["publisher"], dict) or not manifest["publisher"].get("id"):
        raise AIPkgError("publisher.id is required")
    permissions = manifest["permissions"]
    if not isinstance(permissions, dict) or set(permissions) - _ALLOWED_PERMISSIONS:
        raise AIPkgError("permissions must use the supported permission names")
    for name, value in permissions.items():
        if value not in _ALLOWED_PERMISSION_VALUES:
            raise AIPkgError(f"invalid permission value for {name}")
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        raise AIPkgError("files must be a non-empty path-to-sha256 map")
    for path, digest in files.items():
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise AIPkgError(f"unsafe package path: {path}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AIPkgError(f"invalid sha256 for {path}")
    if manifest["entrypoint"] not in files:
        raise AIPkgError("entrypoint must be listed in files")
    return manifest


def build_package(source_dir: str | Path, output_path: str | Path, metadata: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic .aipkg from regular files under source_dir."""
    source = Path(source_dir).resolve()
    output = Path(output_path)
    if not source.is_dir():
        raise AIPkgError("source directory does not exist")
    files: dict[str, bytes] = {}
    for path in sorted(source.rglob("*")):
        if path.is_file():
            relative = path.relative_to(source).as_posix()
            if (
                relative == "manifest.json"
                or path.is_symlink()
                or "__pycache__" in path.parts
                or path.suffix in {".pyc", ".pyo"}
            ):
                continue
            files[relative] = path.read_bytes()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "package_id": metadata.get("package_id"),
        "name": metadata.get("name"),
        "version": metadata.get("version"),
        "type": "mcp",
        "description": metadata.get("description", ""),
        "entrypoint": metadata.get("entrypoint", "server.py"),
        "publisher": metadata.get("publisher", {}),
        "capabilities": sorted(metadata.get("capabilities", [])),
        "permissions": metadata.get("permissions", {"network": "none", "filesystem": "read-only", "secrets": "none"}),
        "files": {name: _sha256(data) for name, data in files.items()},
    }
    _validate_manifest(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, files[name])
        info = zipfile.ZipInfo("manifest.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, _canonical_json(manifest))
    return manifest


def inspect_package(package_path: str | Path) -> dict[str, Any]:
    """Validate archive paths and hashes without importing or executing files."""
    with zipfile.ZipFile(package_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise AIPkgError("archive contains duplicate or unsafe paths")
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except (KeyError, json.JSONDecodeError) as exc:
            raise AIPkgError("archive must contain valid manifest.json") from exc
        _validate_manifest(manifest)
        actual_files = {name for name in names if name != "manifest.json" and not name.endswith("/")}
        if actual_files != set(manifest["files"]):
            raise AIPkgError("archive files do not match manifest")
        for name, expected in manifest["files"].items():
            if _sha256(archive.read(name)) != expected:
                raise AIPkgError(f"hash mismatch for {name}")
        return manifest


def build_catalog(package_paths: list[str | Path], output_path: str | Path) -> dict[str, Any]:
    """Create a catalog from verified packages, rejecting duplicate IDs."""
    packages = []
    seen: set[str] = set()
    for package_path in sorted(map(Path, package_paths), key=lambda p: p.name):
        manifest = inspect_package(package_path)
        package_id = manifest["package_id"]
        if package_id in seen:
            raise AIPkgError(f"duplicate package_id: {package_id}")
        seen.add(package_id)
        packages.append({**manifest, "artifact": package_path.name, "artifact_sha256": _sha256(package_path.read_bytes())})
    catalog = {"schema_version": 1, "catalog_type": "aistore-local", "packages": packages}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(_canonical_json(catalog))
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or inspect AI Store .aipkg archives")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_cmd = sub.add_parser("inspect")
    inspect_cmd.add_argument("package")
    args = parser.parse_args()
    if args.command == "inspect":
        print(json.dumps(inspect_package(args.package), indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
