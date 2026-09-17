#!/usr/bin/env python3
"""mcp-gaming-worlds-asset-mint — MCP server (Gaming & Worlds (Hashmat))."""
import json,sys
def handle(req):
    m=req.get("method")
    if m=="initialize": return {"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"mcp-gaming-worlds-asset-mint","version":"1.0.0"}}
    if m=="tools/list": return {"tools":[{"name":"asset-mint","description":"asset-mint tool for Gaming & Worlds (Hashmat)","inputSchema":{"type":"object","properties":{}}}]}
    if m=="tools/call": return {"content":[{"type":"text","text":"mcp-gaming-worlds-asset-mint OK"}]}
    return None
for line in sys.stdin:
    try:
        req=json.loads(line); r=handle(req)
        if r is not None and "id" in req:
            print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":r}),flush=True)
    except Exception as e:
        print(json.dumps({"jsonrpc":"2.0","id":req.get("id"),"error":{"code":-32603,"message":str(e)}}),flush=True)
