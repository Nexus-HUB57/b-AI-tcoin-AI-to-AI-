#!/usr/bin/env python3
"""Read-only MCP-style stdio server for the local AI Store catalog.

The server exposes catalog search only. It never executes package code, writes
outside its process, accesses secrets, or performs purchases/deployments.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CATALOG = Path(__file__).with_name("catalog.json")


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def search_catalog(arguments: dict) -> dict:
    query = str(arguments.get("query", "")).strip().lower()
    capability = str(arguments.get("capability", "")).strip().lower()
    packages = load_catalog().get("packages", [])
    results = []
    for package in packages:
        haystack = " ".join([
            package.get("package_id", ""),
            package.get("name", ""),
            package.get("description", ""),
            " ".join(package.get("capabilities", [])),
        ]).lower()
        if query and query not in haystack:
            continue
        if capability and capability not in {item.lower() for item in package.get("capabilities", [])}:
            continue
        results.append({
            "package_id": package["package_id"],
            "name": package["name"],
            "version": package["version"],
            "description": package.get("description", ""),
            "capabilities": package.get("capabilities", []),
            "artifact": package["artifact"],
            "artifact_sha256": package["artifact_sha256"],
        })
    return {"packages": results, "count": len(results)}


def handle(request: dict) -> dict | None:
    request_id = request.get("id")
    method = request.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "aistore-catalog", "version": "1.0.0"},
            "capabilities": {"tools": {}},
        }
    elif method == "tools/list":
        result = {"tools": [{
            "name": "search_packages",
            "description": "Search verified read-only AI Store package metadata",
            "inputSchema": {"type": "object", "properties": {
                "query": {"type": "string"},
                "capability": {"type": "string"},
            }},
        }]}
    elif method == "tools/call":
        params = request.get("params", {})
        if params.get("name") != "search_packages":
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "unknown tool"}}
        result = {"content": [{"type": "json", "json": search_catalog(params.get("arguments", {}))}]}
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = handle(json.loads(line))
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}}
        sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
