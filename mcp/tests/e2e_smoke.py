#!/usr/bin/env python3
"""
End-to-end smoke test for the b'AI'tcoin MCP portfolio.

Spawns each MCP server in turn via stdio, runs the full JSON-RPC 2.0
handshake (initialize → notifications/initialized → tools/list → tools/call),
and reports per-server pass/fail.

Exit code is the number of failed servers (0 = all green).

Usage:
    python tests/e2e_smoke.py                # all servers
    python tests/e2e_smoke.py mcp-oracle     # single server
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_TOOL_CALL: Dict[str, tuple[str, dict]] = {
    # server_name      → (tool_name, arguments)
    "mcp-oracle":           ("get_price", {"symbol": "BAIT"}),
    "mcp-defi":             ("pool_apy", {"pool_name": "BAIT-USDC"}),
    "mcp-bridge":           ("list_pending", {}),
    "mcp-faucet":           ("faucet_stats", {}),
    "mcp-agent-registry":   ("discover_agents", {}),
    "mcp-marketplace":      ("list_listings", {}),
    "mcp-telemetry":        ("failure_rate", {"mcp": "mcp-oracle"}),
    "mcp-rag-upgrader":     ("knowledge_base_stats", {}),
    "mcp-skill-evolver":    ("candidate_skills", {}),
    "mcp-self-heal":        ("health_check", {"name": "mcp-oracle"}),
    "mcp-agentic-awareness":("introspect", {"agent_id": "@test"}),
}

ALL_SERVERS = list(DEFAULT_TOOL_CALL.keys())


async def handshake(proc, module: str) -> Dict[str, Any]:
    async def send(req):
        body = json.dumps(req).encode()
        proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
        await proc.stdin.drain()

    async def recv() -> Dict[str, Any]:
        headers: Dict[str, str] = {}
        while True:
            line = await proc.stdout.readline()
            if not line:
                return None
            line = line.rstrip(b"\r\n")
            if not line:
                break
            k, _, v = line.partition(b":")
            headers[k.decode().strip().lower()] = v.decode().strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        body = await proc.stdout.readexactly(length)
        return json.loads(body.decode())

    await send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                 "params": {"protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "smoke", "version": "1.0.0"}}})
    init = await recv()
    if not init or "result" not in init:
        raise RuntimeError(f"initialize failed: {init}")

    await send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = await recv()
    if not tools or "result" not in tools:
        raise RuntimeError(f"tools/list failed: {tools}")

    return {
        "init": init["result"]["serverInfo"],
        "tools": [t["name"] for t in tools["result"]["tools"]],
    }


async def call_tool(proc, name: str, args: dict, id_: int = 3) -> Dict[str, Any]:
    body = json.dumps({"jsonrpc": "2.0", "id": id_, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    await proc.stdin.drain()

    headers: Dict[str, str] = {}
    while True:
        line = await proc.stdout.readline()
        if not line:
            return None
        line = line.rstrip(b"\r\n")
        if not line:
            break
        k, _, v = line.partition(b":")
        headers[k.decode().strip().lower()] = v.decode().strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = await proc.stdout.readexactly(length)
    return json.loads(body.decode())


async def smoke_one(server: str) -> tuple[bool, str]:
    # Directory uses dashes for some, underscores for others; python modules
    # require underscores. Map names explicitly.
    slug = server.replace("mcp-", "")
    module_dir = {
        "agent-registry": "agent_registry",
        "agentic-awareness": "agentic_awareness",
        "rag-upgrader": "rag_upgrader",
        "skill-evolver": "skill_evolver",
        "self-heal": "self_heal",
        "oracle": "oracle",
        "defi": "defi",
        "bridge": "bridge",
        "faucet": "faucet",
        "marketplace": "marketplace",
        "telemetry": "telemetry",
    }.get(slug, slug)
    module = f"servers.{module_dir}.server"
    t0 = time.time()
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", module,
        cwd=str(ROOT),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        info = await asyncio.wait_for(handshake(proc, module), timeout=10)
        tool_name, tool_args = DEFAULT_TOOL_CALL[server]
        if tool_name not in info["tools"]:
            raise RuntimeError(f"expected tool {tool_name} missing — got {info['tools']}")
        call = await asyncio.wait_for(call_tool(proc, tool_name, tool_args), timeout=10)
        if not call or "result" not in call:
            raise RuntimeError(f"tools/call failed: {call}")
        if call["result"].get("isError"):
            err = call["result"].get("content", [{}])[0].get("text", "")
            raise RuntimeError(f"tool error: {err[:200]}")
        dt = (time.time() - t0) * 1000
        return True, f"{info['init']['name']} v{info['init']['version']} — {len(info['tools'])} tools — {dt:.0f}ms"
    except Exception as e:
        stderr = b""
        try:
            stderr = await asyncio.wait_for(proc.stderr.read(), timeout=0.5)
        except Exception:
            pass
        return False, f"FAIL: {e} | stderr={stderr.decode()[-200:]}"
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=2)
        except Exception:
            proc.kill()


async def main(servers: List[str]):
    print(f"▶ smoking {len(servers)} MCP servers…")
    results = await asyncio.gather(*(smoke_one(s) for s in servers))
    passed = 0
    for server, (ok, msg) in zip(servers, results):
        mark = "✅" if ok else "❌"
        print(f"  {mark} {server:<28} {msg}")
        if ok:
            passed += 1
    print(f"\n{'✅ ALL GREEN' if passed == len(servers) else f'⚠ {len(servers) - passed} FAILED'} — {passed}/{len(servers)}")
    sys.exit(len(servers) - passed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("servers", nargs="*", default=ALL_SERVERS)
    args = ap.parse_args()
    asyncio.run(main(args.servers))