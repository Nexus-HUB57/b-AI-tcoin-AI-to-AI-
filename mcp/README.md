# b'AI'tcoin MCP Portfolio

> **Model Context Protocol servers for the b'AI'tcoin / Nexus AI-OS ecosystem.**
> Distributed as `.aipkg` packages via the Nexus AI-OS Store.

This module ships **28 production MCPs** spanning the entire b'AI'tcoin stack — from
on-chain primitives to AI/ML infra, web/agent tooling, dev/SRE, and security —
plus the **meta-layer** that drives agentic autoevolution.

## Production status

| Metric | Value |
|--------|-------|
| **Total MCPs (b'AI'tcoin side)** | **28** |
| **Total MCPs (cross-repo)**     | **34** (28 here + 6 in `AI_Store`) |
| **Total tools exposed**          | ~150 across all servers |
| **Categories**                   | 17 |
| **`.aipkg` archives generated**  | **28** in `dist/` |
| **Waves**                        | Wave 1 (11) + Wave 2 (17) |
| **Branches (preserved)**         | `feat/mcp-portfolio` (Wave 1), `feat/mcp-wave2` (Wave 2) |
| **Open PRs**                     | [#28 closed](https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/pull/28) (Wave 1), [#30 open](https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/pull/30) (Wave 2), [#29 open](https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/pull/29) (concurrent `.aipkg` work — different paths, no file conflicts) |
| **Last build**                   | 28 `.aipkg` + `dist/portfolio.json` (28 servers) |
| **Spec**                         | [MCP 2024-11-05](https://modelcontextprotocol.io/specification/2024-11-05) |

---

## Quick links

- [Architecture](#architecture)
- [SDK](#sdk)
- [The 28 MCPs](#the-28-mcps) — [Wave 1 core](#wave-1--core-on-chain) · [Wave 1 meta](#wave-1--meta-autoevolution) · [Wave 2 data](#wave-2--data--ai) · [Wave 2 web](#wave-2--web--agents) · [Wave 2 dev](#wave-2--dev--sre) · [Wave 2 sec](#wave-2--security--identity)
- [.aipkg schema](#aipkg-schema)
- [Build & distribute](#build--distribute)
- [Autoevolution loop](#autoevolution-loop)
- [Install on an agent host](#install-on-an-agent-host)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Host (Claude Desktop,                 │
│                  Cursor, custom, AI Store orchestrator)      │
└────────┬─────────────────────────────────────────────┬───────┘
         │ JSON-RPC 2.0 over stdio                       │ SSE / HTTP
         │                                              │
┌────────▼────────────────────────────────────────────────────┐
│                  MCP Servers (Python)                        │
│  28 servers across 17 categories                            │
│   • Wave 1 core: oracle, defi, bridge, faucet,              │
│     agent-registry, marketplace                              │
│   • Wave 1 meta: telemetry, rag-upgrader, skill-evolver,    │
│     self-heal, agentic-awareness                            │
│   • Wave 2 data: embeddings, synthetic-data, vision,       │
│     rag-core, finetune                                      │
│   • Wave 2 web:  browser, scraper, search, scheduler        │
│   • Wave 2 dev:  git-ops, git-ci, deploy, observability     │
│   • Wave 2 sec:  vault, attest, rate-limit, encryption      │
└────────┬────────────────────────────────────────────────────┘
         │ tools/call events
         ▼
┌─────────────────────────────────────────────────────────────┐
│            Autoevolution pipeline                           │
│   logs/mcp-telemetry.jsonl → RAG upgrader → skill store     │
└─────────────────────────────────────────────────────────────┘
```

## SDK (`mcp_sdk/`)

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

---

## The 28 MCPs

### Wave 1 · Core (on-chain)

| MCP | Category | Tools |
|-----|----------|-------|
| **mcp-oracle**          | oracle         | `get_price`, `get_prices_bulk`, `register_oracle`, `submit_report`, `list_oracles`, `market_summary` |
| **mcp-defi**            | defi           | `quote_swap`, `open_staking`, `open_lending`, `pool_apy`, `list_pools`, `position_status` |
| **mcp-bridge**          | bridge         | `initiate_bridge`, `sign_bridge`, `finalize_bridge`, `bridge_status`, `list_pending` |
| **mcp-faucet**          | faucet         | `request_drip`, `balance`, `drip_history`, `faucet_stats` |
| **mcp-agent-registry**  | agent-registry | `register_agent`, `lookup_agent`, `list_by_capability`, `update_reputation`, `agent_stats`, `discover_agents` |
| **mcp-marketplace**     | marketplace    | `list_listings`, `create_listing`, `purchase`, `rate_listing`, `listing_stats` |

### Wave 1 · Meta (autoevolution)

| MCP | Category | Tools |
|-----|----------|-------|
| **mcp-telemetry**        | telemetry         | `ingest_event`, `recent_calls`, `failure_rate`, `heatmap`, `feed_rag`, `pending_signals` |
| **mcp-rag-upgrader**     | rag-upgrader      | `pending_proposals`, `cluster_failures`, `propose_upgrade`, `apply_proposal`, `knowledge_base_stats` |
| **mcp-skill-evolver**    | skill-evolver     | `candidate_skills`, `promote_to_skill`, `list_skills`, `skill_stats` |
| **mcp-self-heal**        | self-heal         | `ping_mcp`, `health_check`, `drift_check`, `restart_mcp`, `heal_loop_status` |
| **mcp-agentic-awareness**| agentic-awareness | `introspect`, `context_window`, `recommend_tools`, `capability_gaps`, `consciousness_score` |

### Wave 2 · Data & AI

| MCP | Category | Tools |
|-----|----------|-------|
| **mcp-embeddings**       | embeddings        | `embed`, `embed_query`, `upsert`, `search`, `delete`, `collection_stats`, `hybrid_search` |
| **mcp-synthetic-data**   | synthetic-data    | `generate_tabular`, `generate_text`, `generate_timeseries`, `privacy_budget`, `differential_noise` |
| **mcp-vision**           | vision            | `classify_image`, `detect_objects`, `transcribe_audio`, `describe_image`, `ocr`, `similarity` |
| **mcp-rag-core**         | rag-core          | `ingest_document`, `chunk`, `retrieve`, `rerank`, `list_documents`, `document_summary` |
| **mcp-finetune**         | finetune          | `create_job`, `job_status`, `list_jobs`, `cancel_job`, `export_adapter`, `recommend_hyperparams` |

### Wave 2 · Web & Agents

| MCP | Category | Tools |
|-----|----------|-------|
| **mcp-browser**     | browser   | `new_session`, `navigate`, `click`, `fill`, `extract`, `screenshot`, `close_session`, `list_sessions` |
| **mcp-scraper**     | scraper   | `fetch`, `extract_structured`, `crawl`, `extract_links`, `extract_jsonld`, `extract_opengraph` |
| **mcp-search**      | search    | `search`, `news_search`, `image_search`, `video_search`, `suggest`, `answer` |
| **mcp-scheduler**   | scheduler | `schedule`, `list_jobs`, `get_job`, `cancel_job`, `run_now`, `job_history`, `next_run` |

### Wave 2 · Dev & SRE

| MCP | Category | Tools |
|-----|----------|-------|
| **mcp-git-ops**       | git-ops        | `status`, `log`, `diff`, `branch_list`, `create_branch`, `merge`, `stash`, `blame` |
| **mcp-git-ci**        | git-ci         | `trigger_workflow`, `workflow_status`, `workflow_logs`, `cancel_workflow`, `list_workflows`, `artifact_download`, `list_runs` |
| **mcp-deploy**        | deploy         | `deploy`, `list_targets`, `deploy_status`, `rollback`, `list_services`, `scale`, `env_set`, `logs` |
| **mcp-observability** | observability  | `query_prom`, `query_loki`, `list_metrics`, `alert_state`, `create_alert`, `trace_search`, `service_health`, `otel_ingest` |

### Wave 2 · Security & Identity

| MCP | Category | Tools |
|-----|----------|-------|
| **mcp-vault**       | vault         | `get_secret`, `set_secret`, `delete_secret`, `list_keys`, `rotate_secret`, `secret_metadata`, `bulk_get` |
| **mcp-attest**      | attest        | `issue`, `verify`, `revoke`, `list_for_agent`, `capabilities_of`, `sign_payload`, `verify_signature` |
| **mcp-rate-limit**  | rate-limit    | `check`, `consume`, `reset`, `status`, `list_keys`, `set_policy`, `get_policy` |
| **mcp-encryption**  | encryption  | `encrypt`, `decrypt`, `sign`, `verify`, `hash`, `hmac_sign`, `generate_keypair`, `key_fingerprint` |

---

## `.aipkg` schema

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

## Build & distribute

```bash
# Generate per-server manifests
python scripts/generate_manifests.py

# Build the portfolio (.aipkg archives + portfolio.json)
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

## Autoevolution loop

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

## Install on an agent host

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

## Stats

```
Wave 1 (11 MCPs)  + Wave 2 (17 MCPs)  =  28 MCPs total
                                          ~150 tools across all servers
                                          17 categories
                                          1 unified .aipkg distribution
```

## License

MIT © Nexus-HUB57 — b'AI'tcoin ecosystem.