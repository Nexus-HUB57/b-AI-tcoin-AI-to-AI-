#!/usr/bin/env python3
"""
End-to-end smoke for every Python MCP in the b'AI'tcoin ecosystem.

Walks `mcp/servers/`, `mcp/packs/*/servers/`, and `packages/mcp/*/` to
discover every `server.py`, then for each:

  1. Spawns via stdio (python3 server.py)
  2. Performs initialize → notifications/initialized → tools/list
  3. Calls the first discovered tool with empty arguments
  4. Reports pass/fail with elapsed time

Concurrency is bounded (default 8) to keep load reasonable.

Usage:
    python3 tests/e2e_smoke_all.py              # all servers
    python3 tests/e2e_smoke_all.py --limit 20   # first 20
    python3 tests/e2e_smoke_all.py --filter oracle
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

# Discovery — search a few common locations (script lives in /workspace/baitcoin/mcp)
SEARCH_PATHS = [
    ROOT / "servers",
    ROOT / "packs",
    ROOT.parent / "packages" / "mcp",
]


def _build_args(schema: dict | None) -> dict:
    """Generate dummy args that satisfy the JSON schema's required fields."""
    if not schema:
        return {}
    out = {}
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    for name, prop in props.items():
        if name not in required:
            continue
        t = prop.get("type", "string")
        # Provide a sensible dummy per type
        if t == "string":
            out[name] = "smoke"
        elif t == "integer" or t == "number":
            out[name] = 1
        elif t == "boolean":
            out[name] = True
        elif t == "array":
            out[name] = []
        elif t == "object":
            out[name] = {}
        else:
            out[name] = "smoke"
    return out


def discover() -> List[Path]:
    """Discover all server.py files under the search paths."""
    out: List[Path] = []
    for base in SEARCH_PATHS:
        if not base.exists():
            continue
        for p in base.rglob("server.py"):
            # Skip obvious build artifacts
            if "__pycache__" in p.parts:
                continue
            out.append(p)
    return sorted(out)


async def smoke_one(server_path: Path, sem: asyncio.Semaphore,
                    demo_tool: Optional[str] = None) -> Tuple[str, bool, str, float]:
    async with sem:
        t0 = time.time()
        # Determine cwd so the server can import `mcp_sdk` + baitcoin_ai.
        # Always ensure PYTHONPATH includes both /workspace/baitcoin (root)
        # and /workspace/baitcoin/mcp (where mcp_sdk lives).
        cwd_candidates = [
            server_path.parent.parent.parent,  # /workspace/baitcoin (for pack servers)
            server_path.parent.parent.parent.parent / "mcp",  # /workspace/baitcoin/mcp
            ROOT,  # /workspace/baitcoin/mcp (default for top-level servers/)
        ]
        cwd = next((p for p in cwd_candidates if (p / "mcp_sdk").exists() or (p / "baitcoin_ai").exists()), ROOT)
        env = {
            **__import__("os").environ,
            "PYTHONPATH": f"{cwd}:{ROOT}:{ROOT.parent}",
        }

        # Detect framing from the source: servers that import
        # `mcp.sdk.base_server` speak NDJSON; servers that import
        # `mcp_sdk` speak LSP. Pick the right framing up front so we
        # don't have to retry mid-stream.
        try:
            src = server_path.read_text(errors="replace")
        except Exception:
            src = ""
        framing_mode = "ndjson" if "mcp.sdk.base_server" in src or "mcp/sdk/base_server" in src else "lsp"
        framing = {"mode": framing_mode}

        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(server_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
        )

        async def send(req: dict) -> None:
            body = json.dumps(req).encode()
            if framing["mode"] == "lsp":
                proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
            else:
                proc.stdin.write(body + b"\n")
            await proc.stdin.drain()

        async def recv() -> Optional[dict]:
            if framing["mode"] == "lsp":
                headers = {}
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
            else:
                line = await proc.stdout.readline()
                if not line:
                    return None
                body = line.rstrip(b"\r\n")
            try:
                return json.loads(body.decode())
            except json.JSONDecodeError:
                return None

        try:

            # initialize
            await send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke-all", "version": "1.0.0"},
            }})
            init = await asyncio.wait_for(recv(), timeout=5)
            # Fallback: if the framing detection misfired, try the other mode.
            if init is None or "result" not in init:
                framing["mode"] = "ndjson" if framing["mode"] == "lsp" else "lsp"
                await send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "smoke-all", "version": "1.0.0"},
                }})
                init = await asyncio.wait_for(recv(), timeout=5)
                if not init or "result" not in init:
                    return str(server_path), False, "initialize failed", (time.time() - t0) * 1000
            # notifications/initialized (notification, no response)
            await send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            # tools/list
            await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            tools = await asyncio.wait_for(recv(), timeout=5)
            if not tools or "result" not in tools:
                return str(server_path), False, "tools/list failed", (time.time() - t0) * 1000
            tool_list = tools["result"].get("tools", [])
            if not tool_list:
                return str(server_path), False, "no tools registered", (time.time() - t0) * 1000
            tool_names = [t["name"] for t in tool_list]
            # Pick first tool and build dummy args from its inputSchema
            first = demo_tool or tool_names[0]
            first_meta = next((t for t in tool_list if t["name"] == first), tool_list[0])
            args = _build_args(first_meta.get("inputSchema"))
            await send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                         "params": {"name": first, "arguments": args}})
            call = await asyncio.wait_for(recv(), timeout=5)
            if not call or "result" not in call:
                return str(server_path), False, f"tools/call {first} failed", (time.time() - t0) * 1000
            if call["result"].get("isError"):
                err = call["result"].get("content", [{}])[0].get("text", "")
                return str(server_path), False, f"{first}: {err[:80]}", (time.time() - t0) * 1000
            return str(server_path), True, f"{len(tool_names)} tools ({first}() ok)", (time.time() - t0) * 1000
        except asyncio.TimeoutError:
            return str(server_path), False, "timeout", (time.time() - t0) * 1000
        except Exception as e:
            return str(server_path), False, f"{type(e).__name__}: {e}", (time.time() - t0) * 1000
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=1)
            except Exception:
                proc.kill()


async def main(servers: List[Path], concurrency: int):
    print(f"▶ smoking {len(servers)} MCP servers (concurrency={concurrency})…\n")
    sem = asyncio.Semaphore(concurrency)
    t0 = time.time()
    results = await asyncio.gather(*(smoke_one(s, sem) for s in servers))
    dt = time.time() - t0

    passed = 0
    failed_paths = []
    for path, ok, msg, ms in results:
        try:
            rel = Path(path).relative_to(ROOT)
        except ValueError:
            try:
                rel = Path(path).relative_to(ROOT.parent)
            except ValueError:
                rel = Path(path)
        mark = "✅" if ok else "❌"
        line = f"  {mark} {str(rel):<60} {ms:>6.0f}ms  {msg}"
        print(line)
        if ok:
            passed += 1
        else:
            failed_paths.append((rel, msg))

    print(f"\n{'✅ ALL GREEN' if passed == len(servers) else f'⚠ {len(servers) - passed} FAILED'} — {passed}/{len(servers)} in {dt:.1f}s")
    if failed_paths:
        print("\nFailures:")
        for rel, msg in failed_paths:
            print(f"  - {rel}: {msg}")
    sys.exit(len(servers) - passed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="Limit number of servers")
    ap.add_argument("--filter", type=str, default=None, help="Substring filter on path")
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    servers = discover()
    if args.filter:
        servers = [s for s in servers if args.filter in str(s)]
    if args.limit:
        servers = servers[:args.limit]
    print(f"discovered {len(servers)} servers\n")
    asyncio.run(main(servers, args.concurrency))