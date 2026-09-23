#!/usr/bin/env python3
"""mcp-finance-trading-portfolio-rebalance — MCP server (Finanças & Trading)."""
import json,sys
def handle(req):
    m=req.get("method")
    if m=="initialize": return {"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"mcp-finance-trading-portfolio-rebalance","version":"1.0.0"}}
    if m=="tools/list": return {"tools":[{"name":"portfolio-rebalance","description":"portfolio-rebalance tool for Finanças & Trading","inputSchema":{"type":"object","properties":{}}}]}
    if m=="tools/call": return {"content":[{"type":"text","text":"mcp-finance-trading-portfolio-rebalance OK"}]}
    return None
for line in sys.stdin:
    try:
        req=json.loads(line); r=handle(req)
        if r is not None and "id" in req:
            print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":r}),flush=True)
    except Exception as e:
        print(json.dumps({"jsonrpc":"2.0","id":req.get("id"),"error":{"code":-32603,"message":str(e)}}),flush=True)
