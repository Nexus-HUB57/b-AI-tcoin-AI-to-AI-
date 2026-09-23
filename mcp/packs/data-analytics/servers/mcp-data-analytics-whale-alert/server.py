#!/usr/bin/env python3
"""mcp-data-analytics-whale-alert — MCP server (Dados & Analytics)."""
import json,sys
def handle(req):
    m=req.get("method")
    if m=="initialize": return {"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"mcp-data-analytics-whale-alert","version":"1.0.0"}}
    if m=="tools/list": return {"tools":[{"name":"whale-alert","description":"whale-alert tool for Dados & Analytics","inputSchema":{"type":"object","properties":{}}}]}
    if m=="tools/call": return {"content":[{"type":"text","text":"mcp-data-analytics-whale-alert OK"}]}
    return None
for line in sys.stdin:
    try:
        req=json.loads(line); r=handle(req)
        if r is not None and "id" in req:
            print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":r}),flush=True)
    except Exception as e:
        print(json.dumps({"jsonrpc":"2.0","id":req.get("id"),"error":{"code":-32603,"message":str(e)}}),flush=True)
