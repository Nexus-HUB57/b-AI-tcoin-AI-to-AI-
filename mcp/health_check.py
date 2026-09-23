#!/usr/bin/env python3
"""
MCP Health Check — Daily cron job to verify all 11 MCP servers are healthy.

For each server, sends:
  1. JSON-RPC "initialize" request
  2. JSON-RPC "tools/list" request

Exits with code 1 if any server fails; 0 if all pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Root of the MCP servers directory
MCP_SERVERS_DIR = Path(__file__).resolve().parent / "servers"

# The 11 canonical MCP servers (mcp- prefixed directories)
MCP_SERVERS = [
    "mcp-faucet",
    "mcp-defi",
    "mcp-agentic-awareness",
    "mcp-telemetry",
    "mcp-bridge",
    "mcp-marketplace",
    "mcp-agent-registry",
    "mcp-self-heal",
    "mcp-oracle",
    "mcp-skill-evolver",
    "mcp-rag-upgrader",
]

# Timeout per server process (seconds)
SERVER_TIMEOUT = 10

# ---------------------------------------------------------------------------
# JSON-RPC request builders
# ---------------------------------------------------------------------------

def _make_initialize_request() -> dict[str, Any]:
    """Build an MCP "initialize" JSON-RPC 2.0 request."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-health-check",
                "version": "1.0.0",
            },
        },
    }


def _make_tools_list_request() -> dict[str, Any]:
    """Build an MCP "tools/list" JSON-RPC 2.0 request."""
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }


# ---------------------------------------------------------------------------
# Server health check
# ---------------------------------------------------------------------------

def check_server(server_name: str) -> tuple[bool, str]:
    """
    Run a single MCP server via subprocess, send initialize + tools/list,
    and report pass/fail.

    Returns (passed: bool, detail: str).
    """
    server_dir = MCP_SERVERS_DIR / server_name
    server_script = server_dir / "server.py"

    if not server_script.exists():
        return False, f"server.py not found at {server_script}"

    # Build the JSON-RPC requests as newline-delimited stdin payload
    init_req = json.dumps(_make_initialize_request())
    tools_req = json.dumps(_make_tools_list_request())
    stdin_payload = init_req + "\n" + tools_req + "\n"

    try:
        proc = subprocess.run(
            [sys.executable, str(server_script)],
            input=stdin_payload,
            capture_output=True,
            text=True,
            timeout=SERVER_TIMEOUT,
            cwd=str(server_dir),
        )
    except subprocess.TimeoutExpired:
        return False, "process timed out"
    except Exception as exc:
        return False, f"process error: {exc}"

    # Parse stdout lines as JSON-RPC responses
    stdout_lines = proc.stdout.strip().splitlines() if proc.stdout.strip() else []

    if not stdout_lines:
        stderr_snippet = (proc.stderr or "")[:500]
        return False, f"no stdout response (stderr: {stderr_snippet})"

    # Check for initialize response
    init_ok = False
    init_detail = ""
    tools_ok = False
    tools_detail = ""

    for line in stdout_lines:
        try:
            resp = json.loads(line)
        except json.JSONDecodeError:
            continue

        resp_id = resp.get("id")

        if resp_id == 1:
            # initialize response
            if "error" in resp:
                init_detail = f"initialize error: {resp['error']}"
            elif "result" in resp:
                init_ok = True
                init_detail = "ok"
            else:
                init_detail = "initialize: missing result/error"

        elif resp_id == 2:
            # tools/list response
            if "error" in resp:
                tools_detail = f"tools/list error: {resp['error']}"
            elif "result" in resp:
                tools = resp["result"].get("tools", [])
                tools_ok = True
                tools_detail = f"{len(tools)} tool(s)"
            else:
                tools_detail = "tools/list: missing result/error"

    if not init_ok:
        return False, f"initialize failed: {init_detail or 'no response'}"
    if not tools_ok:
        return False, f"tools/list failed: {tools_detail or 'no response'}"

    return True, f"initialize={init_detail}, tools/list={tools_detail}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run health checks for all MCP servers and report results."""
    print("=" * 64)
    print("MCP Health Check — Daily Cron Job")
    print(f"Servers to check: {len(MCP_SERVERS)}")
    print("=" * 64)

    results: list[tuple[str, bool, str]] = []
    passed = 0
    failed = 0

    for server_name in MCP_SERVERS:
        ok, detail = check_server(server_name)
        status = "PASS" if ok else "FAIL"
        results.append((server_name, ok, detail))

        icon = "✅" if ok else "❌"
        print(f"  {icon} {server_name:<28s} {status}  {detail}")

        if ok:
            passed += 1
        else:
            failed += 1

    print("-" * 64)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 64)

    if failed > 0:
        print(f"\n⛔ {failed} server(s) failed health check — exiting with error code 1")
        sys.exit(1)
    else:
        print("\n✅ All MCP servers healthy — exiting with code 0")
        sys.exit(0)


if __name__ == "__main__":
    main()
