#!/usr/bin/env python3
"""mcp-legal-compliance-privacy-guard — MCP server (Legal & Compliance)."""
import json,sys
def handle(req):
    m=req.get("method")
    if m=="initialize": return {"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"mcp-legal-compliance-privacy-guard","version":"1.0.0"}}
    if m=="tools/list": return {"tools":[{"name":"privacy-guard","description":"privacy-guard tool for Legal & Compliance","inputSchema":{"type":"object","properties":{}}}]}
    if m=="tools/call": return {"content":[{"type":"text","text":"mcp-legal-compliance-privacy-guard OK"}]}
    return None
for line in sys.stdin:
    try:
        req=json.loads(line); r=handle(req)
        if r is not None and "id" in req:
            print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":r}),flush=True)
    except Exception as e:
        print(json.dumps({"jsonrpc":"2.0","id":req.get("id"),"error":{"code":-32603,"message":str(e)}}),flush=True)
