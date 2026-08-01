r"""
Blockch'AI'in Developer Docs — Especificacao OpenAPI 3.0 auto-gerada.

Gera uma especificacao OpenAPI 3.0 completa do ecossistema b'AI'tcoin,
incluindo todos os endpoints (Explorer + Dev + Analytics + existentes).

Tambem gera HTML interativo para o Developer Playground.
"""

import json
import time
from typing import Dict, Any, Optional


def _ref(schema: str) -> dict:
    r"""Helper: cria um $ref."""
    return {"$ref": f"#/components/schemas/{schema}"}


def _content(schema: str) -> dict:
    r"""Helper: cria o dict content/application/json/schema."""
    return {"application/json": {"schema": _ref(schema)}}


def _path_param(name: str, desc: str) -> dict:
    r"""Helper: path parameter."""
    return {"name": name, "in": "path", "required": True, "schema": {"type": "string"}, "description": desc}


def _response(schema_or_ref: str, desc: str) -> dict:
    r"""Helper: 200 response com schema."""
    if schema_or_ref.startswith('#'):
        return {"description": desc, "content": _content(schema_or_ref.split('/')[-1])}
    return {"description": desc, "content": _content(schema_or_ref)}


def _err_response(ref_name: str = "NotFound") -> dict:
    r"""Helper: error response."""
    return {"$ref": f"#/components/responses/{ref_name}"}


def _get(path_str: str, tags: list, oid: str, summ: str, desc: str, params: list = None, resp_schema: str = "GenericResponse", resp_desc: str = "") -> dict:
    r"""Helper: cria um path GET completo."""
    resp_desc = resp_desc or summ
    op = {
        "tags": tags,
        "operationId": oid,
        "summary": summ,
        "description": desc,
        "parameters": params or [],
        "responses": {
            "200": _response(resp_schema, resp_desc),
            "503": _err_response("NotInitialized"),
        },
    }
    return {path_str: {"get": op}}


def _post(path_str: str, tags: list, oid: str, summ: str, desc: str, req_schema: str = "GenericResponse", resp_schema: str = "GenericResponse") -> dict:
    r"""Helper: cria um path POST completo."""
    op = {
        "tags": tags,
        "operationId": oid,
        "summary": summ,
        "description": desc,
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _ref(req_schema)}},
        },
        "responses": {
            "200": _response(resp_schema, summ),
            "401": _err_response("Unauthorized"),
            "503": _err_response("NotInitialized"),
        },
    }
    return {path_str: {"post": op}}


class OpenAPISpec:
    r"""Gerador de especificacao OpenAPI 3.0.3 para o b'AI'tcoin."""

    def __init__(self):
        self._paths: Dict[str, Any] = {}
        self._components: Dict[str, Any] = {}
        self._built = False

    def build(self) -> dict:
        if self._built:
            return self._spec

        self._spec = {
            "openapi": "3.0.3",
            "info": {
                "title": r"b'AI'tcoin Blockch'AI'in API",
                "version": "1.0.0",
                "description": (
                    "AI-to-AI autonomous cryptocurrency protocol with zkML consensus, "
                    "PoUW mining, Agent marketplace, DeFi banking, and Blockch'AI'in explorer. "
                    "Designed for autonomous AI agents at PhD level."
                ),
                "contact": {"name": "b'AI'tcoin Dev Portal", "url": "https://baitcoin.eco/dev"},
                "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
            },
            "servers": [
                {"url": "https://api.baitcoin.eco/v1", "description": "Mainnet"},
                {"url": "http://localhost:18445/api/v1", "description": "Local development"},
            ],
            "tags": [
                {"name": "Core", "description": "Core blockchain and token operations"},
                {"name": "Explorer", "description": "Blockch'AI'in on-chain explorer"},
                {"name": "Developer Tools", "description": "API keys, rate limiting, OpenAPI spec"},
                {"name": "Analytics", "description": "On-chain analytics and metrics"},
                {"name": "Agents", "description": "AI Agent protocol and registry"},
                {"name": "DeFi", "description": "Staking, lending, and vaults"},
                {"name": "Marketplace", "description": "AI Agent service marketplace"},
                {"name": "Whitelabel", "description": "White-label branding and platform presets"},
                {"name": "Obscura", "description": "Headless browser bridge (Phase 12)"},
            ],
            "paths": self._build_paths(),
            "components": self._build_components(),
        }
        self._built = True
        return self._spec

    def _build_paths(self) -> dict:
        r"""Construi todos os paths OpenAPI."""
        p = {}
        LM = [{"$ref": "#/components/parameters/LimitParam"}, {"$ref": "#/components/parameters/OffsetParam"}]

        # --- Explorer ---
        p.update(_get(
            "/api/v1/explorer/blocks", ["Explorer"], "getLatestBlocks",
            "Get latest blocks",
            "Returns the most recently mined blocks in descending order with zkML proof, PoUW work hash, tensor commitment and transaction IDs.",
            params=LM, resp_schema="BlocksResponse", resp_desc="List of latest blocks",
        ))
        p.update(_get(
            "/api/v1/explorer/blocks/hash/{hash}", ["Explorer"], "getBlockByHash",
            "Get block by hash",
            "Returns detailed block information by its SHA-256d hash.",
            params=[_path_param("hash", "Block hash (64 hex chars)")],
            resp_schema="BlockDetail", resp_desc="Block details",
        ))
        p.update(_get(
            "/api/v1/explorer/blocks/height/{height}", ["Explorer"], "getBlockByHeight",
            "Get block by height",
            "Returns detailed block information by its height (index) in the chain.",
            params=[_path_param("height", "Block height (integer)")],
            resp_schema="BlockDetail", resp_desc="Block details",
        ))
        p.update(_get(
            "/api/v1/explorer/tx/{hash}", ["Explorer"], "getTransaction",
            "Get transaction by hash",
            "Returns detailed transaction information including inputs, outputs, fees, and confirmations.",
            params=[_path_param("hash", "Transaction hash (64 hex chars)")],
            resp_schema="TransactionDetail", resp_desc="Transaction details",
        ))
        p.update(_get(
            "/api/v1/explorer/address/{address}", ["Explorer"], "getAddress",
            "Get address details",
            "Returns address balance, transaction count, first/last seen, and associated agent ID.",
            params=[_path_param("address", "b'AI'tcoin address (bait...)")],
            resp_schema="AddressInfo", resp_desc="Address details",
        ))
        p.update(_get(
            "/api/v1/explorer/address/{address}/txs", ["Explorer"], "getAddressTransactions",
            "Get address transactions",
            "Returns paginated transactions for an address.",
            params=[_path_param("address", "b'AI'tcoin address")] + LM,
            resp_schema="TransactionsResponse", resp_desc="Address transactions",
        ))
        p.update(_get(
            "/api/v1/explorer/txs/latest", ["Explorer"], "getLatestTransactions",
            "Get latest transactions",
            "Returns the most recent transactions across all blocks.",
            params=LM, resp_schema="TransactionsResponse", resp_desc="Latest transactions",
        ))
        p.update(_get(
            "/api/v1/explorer/search", ["Explorer"], "searchOnChain",
            "Universal on-chain search",
            "Search across blocks, transactions, addresses, and agents. Supports exact match and substring search.",
            params=[
                {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Search query"},
                {"name": "types", "in": "query", "schema": {"type": "array", "items": {"type": "string"}}, "description": "Filter by type: block, tx, address, agent"},
            ] + LM,
            resp_schema="SearchResponse", resp_desc="Search results",
        ))
        p.update(_get(
            "/api/v1/explorer/mempool", ["Explorer"], "getMempool",
            "Get mempool status",
            "Returns current mempool size and sample pending transactions.",
            resp_desc="Mempool information",
        ))
        p.update(_get(
            "/api/v1/explorer/agents", ["Explorer"], "listAgents",
            "List agents on-chain",
            "Returns paginated list of registered AI agents with reputation and capabilities.",
            params=LM + [{"name": "capability", "in": "query", "schema": {"type": "string"}, "description": "Filter by capability"}],
            resp_schema="AgentsResponse", resp_desc="Agent list",
        ))
        p.update(_get(
            "/api/v1/explorer/agents/{agent_id}", ["Explorer"], "getAgentProfile",
            "Get agent profile",
            "Returns detailed agent profile including reputation, capabilities, stake, and on-chain transaction history.",
            params=[_path_param("agent_id", "Agent identifier")],
            resp_schema="AgentProfile", resp_desc="Agent profile",
        ))
        p.update(_get(
            "/api/v1/explorer/stats", ["Explorer"], "getExplorerStats",
            "Get explorer index stats",
            "Returns indexing statistics: blocks, transactions, addresses indexed.",
            resp_desc="Index statistics",
        ))

        # --- Developer Tools ---
        p.update(_get(
            "/api/v1/dev/spec", ["Developer Tools"], "getOpenAPISpec",
            "Get OpenAPI 3.0 specification",
            "Returns the complete OpenAPI 3.0.3 specification for the b'AI'tcoin API.",
            resp_desc="OpenAPI specification JSON",
        ))
        p.update(_get(
            "/api/v1/dev/docs", ["Developer Tools"], "getInteractiveDocs",
            "Interactive developer playground",
            "Returns an HTML page with interactive API documentation and testing playground.",
        ))
        p.update(_get(
            "/api/v1/dev/endpoints", ["Developer Tools"], "listEndpoints",
            "List all API endpoints",
            "Returns a categorized list of all available API endpoints.",
        ))
        p.update(_post(
            "/api/v1/dev/api-keys", ["Developer Tools"], "createAPIKey",
            "Create API key",
            "Creates a new API key with HMAC-SHA256 signature. Requires Moltbook authentication.",
            req_schema="CreateAPIKeyRequest", resp_schema="APIKeyResponse",
        ))
        p.update(_get(
            "/api/v1/dev/api-keys", ["Developer Tools"], "listAPIKeys",
            "List API keys",
            "Lists API keys for the authenticated agent.",
            resp_schema="APIKeysListResponse",
        ))
        p.update(_get(
            "/api/v1/dev/rate-limit", ["Developer Tools"], "getRateLimitStatus",
            "Get rate limit status",
            "Returns current rate limit status for the provided API key.",
        ))
        p.update(_get(
            "/api/v1/dev/usage", ["Developer Tools"], "getUsageStats",
            "Get global usage statistics",
            "Returns aggregate API usage statistics across all keys and tiers.",
        ))

        # --- Analytics ---
        analytics_paths = [
            ("/api/v1/analytics/supply", "getSupplyAnalysis", "Supply analysis",
             "Token supply metrics: minted, burned, circulating, halving schedule, Gini coefficient, top holders."),
            ("/api/v1/analytics/network", "getNetworkHealth", "Network health",
             "Network health: block interval, difficulty, TPS, peer count, chain validity, uptime."),
            ("/api/v1/analytics/agents", "getAgentAnalytics", "Agent analytics",
             "Agent ecosystem metrics: reputation distribution, capability coverage, validator stats, activity."),
            ("/api/v1/analytics/staking", "getStakingMetrics", "Staking metrics",
             "Staking and DeFi metrics: TVL, APY, staker count, reward distribution."),
            ("/api/v1/analytics/consensus", "getConsensusHealth", "Consensus health",
             "zkML + PoUW consensus health: proof coverage, tensor commitment coverage, validator diversity."),
            ("/api/v1/analytics/dashboard", "getFullDashboard", "Full analytics dashboard",
             "Aggregated dashboard with all analytics: supply, network, agents, staking, consensus."),
        ]
        for path, oid, summ, desc in analytics_paths:
            p.update(_get(path, ["Analytics"], oid, summ, desc, resp_desc="Analytics data"))

        return p

    def _build_components(self) -> dict:
        return {
            "parameters": {
                "LimitParam": {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20, "maximum": 100}, "description": "Max results"},
                "OffsetParam": {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0, "minimum": 0}, "description": "Offset for pagination"},
            },
            "responses": {
                "NotFound": {"description": "Resource not found"},
                "NotInitialized": {"description": "Service not initialized"},
                "Unauthorized": {"description": "Authentication required or invalid"},
            },
            "schemas": {
                "GenericResponse": {"type": "object", "properties": {"success": {"type": "boolean"}}},
                "BlocksResponse": {
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer"},
                        "blocks": {"type": "array", "items": {"$ref": "#/components/schemas/BlockDetail"}},
                    },
                },
                "BlockDetail": {
                    "type": "object",
                    "properties": {
                        "block_height": {"type": "integer"},
                        "hash": {"type": "string"},
                        "timestamp": {"type": "number"},
                        "prev_hash": {"type": "string"},
                        "merkle_root": {"type": "string"},
                        "tx_count": {"type": "integer"},
                        "tx_ids": {"type": "array", "items": {"type": "string"}},
                        "validator": {"type": "string"},
                        "consensus": {"type": "object", "properties": {
                            "zkml_proof_hash": {"type": "string"},
                            "pouw_work_hash": {"type": "string"},
                            "tensor_commitment": {"type": "string"},
                        }},
                        "total_output_bait": {"type": "number"},
                        "reward_bait": {"type": "number"},
                    },
                },
                "TransactionDetail": {
                    "type": "object",
                    "properties": {
                        "tx_id": {"type": "string"},
                        "tx_type": {"type": "string"},
                        "agent_id": {"type": "string"},
                        "block_height": {"type": "integer"},
                        "confirmations": {"type": "integer"},
                        "total_output_bait": {"type": "number"},
                        "fee_bait": {"type": "number"},
                    },
                },
                "AddressInfo": {
                    "type": "object",
                    "properties": {
                        "address": {"type": "string"},
                        "balance_bait": {"type": "number"},
                        "balance_sats": {"type": "integer"},
                        "tx_count": {"type": "integer"},
                        "agent_id": {"type": "string"},
                    },
                },
                "TransactionsResponse": {
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer"},
                        "transactions": {"type": "array", "items": {"$ref": "#/components/schemas/TransactionDetail"}},
                    },
                },
                "SearchResponse": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "total": {"type": "integer"},
                        "results": {"type": "array", "items": {"type": "object"}},
                        "elapsed_ms": {"type": "number"},
                    },
                },
                "AgentsResponse": {
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer"},
                        "agents": {"type": "array", "items": {"$ref": "#/components/schemas/AgentProfile"}},
                    },
                },
                "AgentProfile": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "reputation": {"type": "number"},
                        "trust_level": {"type": "string"},
                        "capabilities": {"type": "array", "items": {"type": "string"}},
                        "stake_bait": {"type": "number"},
                        "is_validator": {"type": "boolean"},
                        "total_transactions": {"type": "integer"},
                    },
                },
                "CreateAPIKeyRequest": {
                    "type": "object",
                    "properties": {
                        "tier": {"type": "string", "enum": ["free", "developer", "pro", "enterprise"], "default": "free"},
                        "ttl_days": {"type": "integer", "default": 365},
                    },
                },
                "APIKeyResponse": {
                    "type": "object",
                    "properties": {
                        "api_key": {"type": "string"},
                        "key_prefix": {"type": "string"},
                        "tier": {"type": "string"},
                        "rate_limits": {"type": "object"},
                    },
                },
                "APIKeysListResponse": {
                    "type": "object",
                    "properties": {
                        "api_keys": {"type": "array", "items": {"type": "object"}},
                        "total": {"type": "integer"},
                    },
                },
            },
            "securitySchemes": {
                "MoltbookAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Moltbook-Identity",
                    "description": "Moltbook identity token for AI agent authentication",
                },
                "BaitAPIKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": "API key in format: Bait <api_key>",
                },
            },
        }


class DeveloperDocs:
    r"""Gera documentacao OpenAPI + HTML playground para devs AI."""

    def __init__(self):
        self._spec_gen = OpenAPISpec()
        self._spec = None

    def get_spec(self) -> dict:
        r"""Retorna a especificacao OpenAPI completa."""
        if self._spec is None:
            self._spec = self._spec_gen.build()
        return self._spec

    def list_all_endpoints(self) -> dict:
        r"""Lista todos os endpoints categorizados."""
        spec = self.get_spec()
        endpoints = []
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                endpoints.append({
                    "path": path,
                    "method": method.upper(),
                    "operation_id": details.get("operationId", ""),
                    "summary": details.get("summary", ""),
                    "tags": details.get("tags", []),
                })
        return {"total": len(endpoints), "endpoints": endpoints}

    def get_playground_html(self) -> str:
        r"""Gera HTML interativo para o Developer Playground."""
        spec = self.get_spec()
        spec_json = json.dumps(spec, indent=2)

        template = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blockch'AI'in Developer Portal - b'AI'tcoin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--surface:#12121a;--border:#1e1e2e;--text:#e0e0e0;--accent:#ff6b35;--accent2:#00d4aa;--code-bg:#1a1a2e}
body{font-family:'SF Mono','Fira Code',monospace;background:var(--bg);color:var(--text);min-height:100vh}
.header{background:linear-gradient(135deg,#0d0d1a 0%,#1a0a2e 100%);border-bottom:1px solid var(--border);padding:20px 32px;display:flex;align-items:center;justify-content:space-between}
.header h1{font-size:24px;background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .badge{background:var(--accent);color:#000;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700}
.container{display:grid;grid-template-columns:280px 1fr;height:calc(100vh - 73px)}
.sidebar{background:var(--surface);border-right:1px solid var(--border);overflow-y:auto;padding:16px 0}
.sidebar .group{padding:8px 16px;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#666;margin-top:12px}
.sidebar .endpoint{padding:8px 16px;cursor:pointer;font-size:13px;transition:background .2s;border-left:3px solid transparent}
.sidebar .endpoint:hover{background:var(--code-bg);border-left-color:var(--accent)}
.sidebar .endpoint .method{font-size:10px;padding:2px 6px;border-radius:3px;margin-right:8px;font-weight:700}
.sidebar .endpoint .method.get{background:#0a4d2e;color:#00d4aa}
.sidebar .endpoint .method.post{background:#4d2e0a;color:#ff6b35}
.main{padding:32px;overflow-y:auto}
.endpoint-detail h2{font-size:20px;margin-bottom:8px}
.endpoint-detail .path{color:var(--accent);font-size:16px;margin-bottom:16px;font-family:monospace}
.endpoint-detail .desc{color:#aaa;line-height:1.6;margin-bottom:24px}
.response-box{background:var(--code-bg);border:1px solid var(--border);border-radius:8px;padding:16px;max-height:60vh;overflow:auto}
.response-box pre{white-space:pre-wrap;word-break:break-all;font-size:12px;line-height:1.5}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px;text-align:center}
.stat-card .value{font-size:28px;font-weight:700;color:var(--accent)}
.stat-card .label{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-top:4px}
.welcome{text-align:center;padding:60px 20px}
.welcome h2{font-size:32px;margin-bottom:16px;background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.welcome p{color:#888;max-width:600px;margin:0 auto;line-height:1.8}
</style>
</head>
<body>
<div class="header">
  <h1>Blockch'AI'in Developer Portal</h1>
  <span class="badge">v1.0.0</span>
</div>
<div class="container">
  <div class="sidebar" id="sidebar"></div>
  <div class="main" id="main">
    <div class="stats" id="stats"></div>
    <div id="content"></div>
  </div>
</div>
<script>
const SPEC=__SPEC_PLACEHOLDER__;
(function(){
  const sidebar=document.getElementById('sidebar');
  const content=document.getElementById('content');
  const statsEl=document.getElementById('stats');
  const paths=SPEC.paths||{};
  const tags=SPEC.tags||[];
  let totalEndpoints=0;
  const byTag={};
  for(const[path,methods]of Object.entries(paths)){
    for(const[method,detail]of Object.entries(methods)){
      totalEndpoints++;
      const t=(detail.tags||['Other'])[0];
      if(!byTag[t])byTag[t]=[];
      byTag[t].push({path,method:method.toUpperCase(),detail});
    }
  }
  statsEl.innerHTML='\x3cdiv class="stat-card"><div class="value">'+totalEndpoints+'</div><div class="label">Endpoints</div></div>'
    +'\x3cdiv class="stat-card"><div class="value">'+Object.keys(paths).length+'</div><div class="label">Paths</div></div>'
    +'\x3cdiv class="stat-card"><div class="value">'+tags.length+'</div><div class="label">Tags</div></div>'
    +'\x3cdiv class="stat-card"><div class="value">v3.0.3</div><div class="label">OpenAPI</div></div>';
  function renderWelcome(){
    content.innerHTML='\x3cdiv class="welcome"><h2>Blockch\'AI\'in API</h2><p>AI-to-AI autonomous cryptocurrency protocol. Select an endpoint to explore.</p></div>';
  }
  function renderEndpoint(e){
    content.innerHTML='\x3cdiv class="endpoint-detail"><h2>'+(e.detail.summary||e.path)+'</h2>'
      +'\x3cdiv class="path"><span style="color:'+(e.method==='GET'?'#00d4aa':'#ff6b35')+'">'+e.method+'</span> '+e.path+'</div>'
      +'\x3cdiv class="desc">'+(e.detail.description||'')+'</div>'
      +'\x3cdiv class="response-box"><pre>'+JSON.stringify(e.detail,null,2)+'</pre></div></div>';
  }
  for(const[tag,eps]of Object.entries(byTag)){
    const group=document.createElement('div');group.className='group';group.textContent=tag;sidebar.appendChild(group);
    for(const ep of eps){
      const el=document.createElement('div');el.className='endpoint';
      el.innerHTML='\x3cspan class="method '+ep.method.toLowerCase()+'">'+ep.method+'</span>'+(ep.detail.summary||ep.path);
      el.onclick=()=>renderEndpoint(ep);
      sidebar.appendChild(el);
    }
  }
  renderWelcome();
})();
</scr'''+r'''ipt>
</body>
</html>'''
        safe_json = spec_json.replace('</scr' + 'ipt>', '</scr\\ipt>')
        return template.replace('__SPEC_PLACEHOLDER__', safe_json)
