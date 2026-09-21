# MCP Portfolio — Cross-Repo Seed

> **Mirror of the AI Store seed data for offline use.**

This folder ships the same data the AI Store uses to populate its Prisma
database, kept here so the b'AI'tcoin side can:

- preview what the AI Store will look like once the portfolio is installed
- share the SQL with anyone wanting to bootstrap a compatible store
- bundle a standalone SQLite fixture for demos

## Files

| File | Purpose |
|------|---------|
| `portfolio-cross-repo.json` | Full JSON with 34 packages + ~199 tools (28 baitcoin-side + 6 store-side) |
| `populate.sql`             | Idempotent INSERT OR IGNORE statements — apply to any Prisma/SQLite store |
| `README.md`                 | This file |

## Why `mcp/seed/` and not `mcp/dist/seed/`?

`mcp/dist/` is in `.gitignore` (it holds build artifacts: `.aipkg`, `portfolio.json`).
We mirror the seed to a tracked location so anyone cloning the repo can
bootstrap an AI Store without needing to rebuild from source.

## Apply to an AI Store

```bash
# Option 1 — use the AI Store installer (recommended, auto-regenerates from source):
#   cd ../AI_Store && bash scripts/mcp/install-portfolio.sh

# Option 2 — apply this snapshot directly:
sqlite3 /path/to/store.db < populate.sql
```

## Regenerate from source

The canonical seed lives in the AI Store repo. To regenerate from the latest
baitcoin portfolio:

```bash
cd ../AI_Store
node scripts/mcp/generate-seed.mjs --baitcoin-root .
cp scripts/mcp/seed/* ../b-AI-tcoin-AI-to-AI-/mcp/seed/
```

## Compatibility

- Prisma schema: 6 new models (`McpPackage`, `McpInstall`, `McpTool`, `McpCall`,
  `McpSelfHealEvent`, `McpRagFeedback`) — see AI Store PR #3.
- Engine: SQLite (default). Postgres/MySQL compatible with column-type adjustments.
- Spec: MCP 2024-11-05.

## Last regenerated

See the `generatedAt` field in `portfolio-cross-repo.json`.

## Spec

[MCP 2024-11-05](https://modelcontextprotocol.io/specification/2024-11-05)