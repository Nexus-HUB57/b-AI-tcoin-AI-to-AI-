#!/usr/bin/env python3
"""
Upgrade the 100 pack MCP servers from NDJSON framing to LSP Content-Length
framing (the MCP 2024-11-05 standard), so they're interoperable with
the b'AI'tcoin SDK and the ai_store orchestrator.

Each pack server.py is ~15 lines and looks like:

    #!/usr/bin/env python3
    import json,sys
    def handle(req):
        m=req.get("method")
        if m=="initialize": return {...}
        if m=="tools/list": return {...}
        if m=="tools/call": return {...}
    for line in sys.stdin:
        try:
            req=json.loads(line); r=handle(req)
            if r is not None and "id" in req:
                print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":r}),flush=True)
        except Exception as e:
            ...

The replacement uses the same `handle(req)` API but wraps stdio with
the LSP-style Content-Length header parser/writer that the b'AI'tcoin
SDK and ai_store McpClient both speak.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LSP_TEMPLATE = '''#!/usr/bin/env python3
"""{docstring}"""
import json
import sys


def handle(req):
    m = req.get("method")
    if m == "initialize":
        return {{"protocolVersion": "2024-11-05", "capabilities": {{"tools": {{}}}}, "serverInfo": {{"name": "{name}", "version": "{version}"}}}}
    if m == "tools/list":
        return {{"tools": [{tools_list}]}}
    if m == "tools/call":
        return {{"content": [{{"type": "text", "text": "{name} OK"}}]}}
    return None


def _read_message():
    headers = {{}}
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        line = line.rstrip("\\r\\n")
        if not line:
            break
        k, _, v = line.partition(":")
        headers[k.strip().lower()] = v.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(sys.stdin.read(length))


def _send(msg):
    body = json.dumps(msg).encode()
    sys.stdout.write(f"Content-Length: {{len(body)}}\\r\\n\\r\\n")
    sys.stdout.write(body.decode())
    sys.stdout.flush()


def main():
    while True:
        try:
            req = _read_message()
        except (EOFError, KeyboardInterrupt):
            return
        if req is None:
            return
        try:
            r = handle(req)
        except Exception as e:
            if "id" in req:
                _send({{"jsonrpc": "2.0", "id": req.get("id"), "error": {{"code": -32603, "message": str(e)}}}})
            continue
        if r is not None and "id" in req:
            _send({{"jsonrpc": "2.0", "id": req["id"], "result": r}})


if __name__ == "__main__":
    main()
'''


def parse_tools_list(src: str) -> str:
    """Extract the tools array from the existing tools/list handler."""
    # find `tools/list` branch and pull the list literal
    import re
    m = re.search(r'if\s+m\s*==\s*"tools/list"\s*:\s*return\s*(\{.*?\})\s*$',
                  src, re.MULTILINE | re.DOTALL)
    if not m:
        return '[{"name": "echo", "description": "echo", "inputSchema": {"type": "object", "properties": {}}}]'
    block = m.group(1)
    jm = re.search(r'"tools"\s*:\s*(\[.*\])', block, re.DOTALL)
    if not jm:
        return '[{"name": "echo", "description": "echo", "inputSchema": {"type": "object", "properties": {}}}]'
    raw = jm.group(1)
    # Convert the list back to a Python literal and re-serialize
    try:
        parsed = json.loads(raw.replace("'", '"'))
        return ", ".join(json.dumps(t) for t in parsed)
    except Exception:
        return '[{"name": "echo", "description": "echo", "inputSchema": {"type": "object", "properties": {}}}]'


def parse_name(src: str) -> str:
    """Extract MCP name from the tools/list branch or docstring."""
    import re
    m = re.search(r'if\s+m\s*==\s*"initialize".*?"name":\s*"([^"]+)"', src, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r'"""mcp-([\w-]+)', src)
    if m:
        return "mcp-" + m.group(1)
    return "mcp-unknown"


def parse_version(src: str) -> str:
    import re
    m = re.search(r'"version"\s*:\s*"([^"]+)"', src)
    return m.group(1) if m else "1.0.0"


def parse_docstring(src: str) -> str:
    import re
    m = re.match(r'"""(.+?)"""', src, re.DOTALL)
    return m.group(1).strip() if m else "MCP server (LSP-framed)"


def upgrade(path: Path) -> tuple[bool, str]:
    src = path.read_text()
    if "_read_message" in src:
        return False, "already LSP-framed"
    name = parse_name(src)
    version = parse_version(src)
    tools = parse_tools_list(src)
    doc = parse_docstring(src)
    # Template already uses {{...}} to escape braces; values must contain
    # raw single braces only (they will become literal {} in the output).
    # No extra escaping on values.
    new = LSP_TEMPLATE.format(
        docstring=doc + " (LSP-framed)",
        name=name,
        version=version,
        tools_list=tools,
    )
    path.write_text(new)
    return True, f"{name} v{version}"


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "mcp/packs")
    upgraded = 0
    cwd = Path.cwd()
    for p in sorted(root.rglob("server.py")):
        ok, msg = upgrade(p)
        if ok:
            upgraded += 1
            try:
                rel = p.relative_to(cwd)
            except ValueError:
                rel = p
            print(f"  ✓ {rel} → {msg}")
    print(f"\n✅ upgraded {upgraded} pack MCPs to LSP framing")


if __name__ == "__main__":
    main()