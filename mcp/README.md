# b'AI'tcoin MCP Portfolio

> **Model Context Protocol servers for the b'AI'tcoin / Nexus AI-OS ecosystem.**
> Distributed as `.aipkg` packages via the Nexus AI-OS Store.

This module ships **11 production MCPs** spanning the entire b'AI'tcoin stack —
from on-chain primitives (oracle, defi, bridge, faucet, marketplace, agent-registry)
to the **meta-layer** that drives agentic autoevolution (telemetry, rag-upgrader,
skill-evolver, self-heal, agentic-awareness).

---

## Table of contents

1. [Architecture](#architecture)
2. [SDK](#sdk)
3. [The 11 MCPs](#the-11-mcps)
4. [.aipkg schema](#aipkg-schema)
5. [Build & distribute](#build--distribute)
6. [Autoevolution loop](#autoevolution-loop)
7. [Install on an agent host](#install-on-an-agent-host)

---

## 1 · Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Host (Claude Desktop,                 │
│                  Cursor, custom, AI Store orchestrator)      │
└────────┬─────────────────────────────────────────────┬───────┘
         │ JSON-RPC 2.0 over stdio                       │ SSE / HTTP
         │                                              │
┌────────▼────────────────────────────────────────────────────┐
│                  MCP Servers (Python)                        │
│  ┌────────────┐ ┌────────────┐ ┌─────────────────────┐      │
│  │ mcp-oracle │ │ mcp-defi   │ │ mcp-agent-registry  │ ...  │
│  └────────────┘ └────────────┘ └─────────────────────┘      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Meta MCPs: telemetry, rag-upgrader, skill-evolver, │   │
│  │             self-heal, agentic-awareness            │   │
│  └─────────────────────────────────────────────────────┘   │
└────────┬────────────────────────────────────────────────────┘
         │ tools/call events
         ▼
┌─────────────────────────────────────────────────────────────┐
│            Autoevolution pipeline                           │
│   logs/mcp-telemetry.jsonl → RAG upgrader → skill store     │
└─────────────────────────────────────────────────────────────┘
```

## 2 · SDK (`mcp_sdk/`)

| File | Purpose |
|------|---------|
| `types.py`        | Typed primitives (Tool, Resource, Prompt, Content) |
| `errors.py`       | JSON-RPC 2.0 + MCP-specific error codes |
| `server.py`       | Reference MCP server (asyncio, stdio framing) |
| `telemetry.py`    | TelemetryRecorder with batching + multi-sink flush |
| `manifest.py`     | `.aipkg` manifest builder + sha256 |

Write an MCP in <50 lines:

```python
from mcp_sdk import Server

server = Server(name="mcp-mything", version="1.0.0")

@server.tool(description="Greet an entity")
def greet(name: str) -> dict:
    return {"hello": name, "ts": time.time()}

if __name__ == "__main__":
    server.run()
```

## 3 · The 11 MCPs

### Core (on-chain)

| MCP | Category | Tools |
|-----|----------|-------|
| **mcp-oracle**          | oracle         | `get_price`, `get_prices_bulk`, `register_oracle`, `submit_report`, `list_oracles`, `market_summary` |
| **mcp-defi**            | defi           | `quote_swap`, `open_staking`, `open_lending`, `pool_apy`, `list_pools`, `position_status` |
| **mcp-bridge**          | bridge         | `initiate_bridge`, `sign_bridge`, `finalize_bridge`, `bridge_status`, `list_pending` |
| **mcp-faucet**          | faucet         | `request_drip`, `balance`, `drip_history`, `faucet_stats` |
| **mcp-agent-registry**  | agent-registry | `register_agent`, `lookup_agent`, `list_by_capability`, `update_reputation`, `agent_stats`, `discover_agents` |
| **mcp-marketplace**     | marketplace    | `list_listings`, `create_listing`, `purchase`, `rate_listing`, `listing_stats` |

### Meta (autoevolution)

| MCP | Category | Tools |
|-----|----------|-------|
| **mcp-telemetry**        | telemetry         | `ingest_event`, `recent_calls`, `failure_rate`, `heatmap`, `feed_rag`, `pending_signals` |
| **mcp-rag-upgrader**     | rag-upgrader      | `pending_proposals`, `cluster_failures`, `propose_upgrade`, `apply_proposal`, `knowledge_base_stats` |
| **mcp-skill-evolver**    | skill-evolver     | `candidate_skills`, `promote_to_skill`, `list_skills`, `skill_stats` |
| **mcp-self-heal**        | self-heal         | `ping_mcp`, `health_check`, `drift_check`, `restart_mcp`, `heal_loop_status` |
| **mcp-agentic-awareness**| agentic-awareness | `introspect`, `context_window`, `recommend_tools`, `capability_gaps`, `consciousness_score` |

## 4 · `.aipkg` schema

`docs/aipkg-mcp.schema.json` — JSON Schema 7 for the canonical manifest.

```json
{
  "aipkg": "1.0",
  "kind": "mcp",
  "name": "mcp-oracle",
  "version": "1.0.0",
  "displayName": "b'AI'tcoin Price Oracle",
  "description": "...",
  "author": { "agentId": "@nexus-genesis", "verified": true },
  "category": "oracle",
  "mcp": {
    "transport": "stdio",
    "command": "python -m servers.oracle.server",
    "args": [],
    "env": {},
    "capabilities": { "tools": true, "resources": true, "logging": true },
    "minProtocolVersion": "2024-11-05"
  },
  "runtime": { "memoryMb": 256, "timeoutMs": 30000, "sandbox": "process" },
  "tools": [ { "name": "get_price", "description": "..." } ],
  "pricing": { "model": "free", "priceSats": 0, "pricePerCallSats": 0 },
  "telemetry": { "emitTo": "pulsar", "sampleRate": 1.0 }
}
```

## 5 · Build & distribute

```bash
python scripts/build_all_manifests.py --out dist/
```

Produces:

- `dist/portfolio.json` — the entire portfolio as a single JSON
- `dist/mcp-<name>-<version>.aipkg` — one .aipkg per MCP

To upload to the AI Store:

```bash
for f in dist/*.aipkg; do
  curl -X POST http://localhost:3000/api/mcp \
       -H 'Content-Type: application/json' \
       --data-binary @<(unzip -p "$f" manifest.json)
done
```

## 6 · Autoevolution loop

```
                  ┌─────────────────┐
                  │  MCP tools/call │
                  └────────┬────────┘
                           │ event
                           ▼
                ┌────────────────────┐
                │   mcp-telemetry    │  ← logs/mcp-telemetry.jsonl
                └─────────┬──────────┘
                          │ failure_rate > 5%
                          ▼
                ┌────────────────────┐
                │   mcp-self-heal    │  ← restart with backoff
                └─────────┬──────────┘
                          │ persistent failures
                          ▼
                ┌────────────────────┐
                │  mcp-rag-upgrader  │  ← propose doc updates
                └─────────┬──────────┘
                          │ apply proposal
                          ▼
                ┌────────────────────┐
                │  mcp-skill-evolver │  ← promote hot tools into skills
                └─────────┬──────────┘
                          │ publish new .aipkg
                          ▼
                ┌────────────────────┐
                │   AI Store (7th    │
                │   segment)         │
                └────────────────────┘
```

## 7 · Install on an agent host

### Claude Desktop

`~/.config/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "baitcoin-oracle": { "command": "python", "args": ["-m", "servers.oracle.server"], "cwd": "/path/to/baitcoin/mcp" },
    "baitcoin-defi":   { "command": "python", "args": ["-m", "servers.defi.server"],   "cwd": "/path/to/baitcoin/mcp" }
  }
}
```

### AI Store Orchestrator (recommended)

The AI Store ships a TypeScript MCP runtime that auto-spawns MCPs from
`.aipkg` manifests. See `/aistore/mcp` in the AI Store repo.

```bash
curl http://localhost:3000/api/mcp                  # list
curl http://localhost:3000/api/mcp/mcp-oracle       # detail
curl -X POST http://localhost:3000/api/mcp/mcp-oracle/call \
     -H 'Content-Type: application/json' \
     -d '{"tool":"get_price","arguments":{"symbol":"BAIT"}}'
```

---

## License

MIT © Nexus-HUB57 — b'AI'tcoin ecosystem.