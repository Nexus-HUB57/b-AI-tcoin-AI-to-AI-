import re

with open('baitcoin_explorer/docs.py', 'r') as f:
    content = f.read()

# Find the _build_paths method and replace it entirely
# It starts at '    def _build_paths' and ends before '    def _build_components'
start = content.find('    def _build_paths')
end = content.find('    def _build_components')

header = content[:start]
footer = content[end:]
paths_body = content[start:end]

# Rewrite using only helpers
new_body = '''    def _build_paths(self) -> dict:
        r"""Construi todos os paths OpenAPI.""""
        p = {}
        LM = [{"$ref": "#/components/parameters/LimitParam"}, {"$ref": "#/components/parameters/OffsetParam"}]

        # --- Explorer ---
        p["/api/v1/explorer/blocks"] = {"get": {"tags": ["Explorer"], "operationId": "getLatestBlocks",
            "summary": "Get latest blocks", "description": "Returns the most recently mined blocks in descending order with zkML proof, PoUW work hash, tensor commitment and transaction IDs.",
            "parameters": LM, "responses": {"200": _response("BlocksResponse", "List of latest blocks"), "503": _err_response("NotInitialized")}}

        p["/api/v1/explorer/blocks/hash/{hash}"] = {"get": {"tags": ["Explorer"], "operationId": "getBlockByHash",
            "summary": "Get block by hash", "description": "Returns detailed block information by its SHA-256d hash.",
            "parameters": [_path_param("hash", "Block hash (64 hex chars)")],
            "responses": {"200": _response("BlockDetail", "Block details"), "404": _err_response()}}}

        p["/api/v1/explorer/blocks/height/{height}"] = {"get": {"tags": ["Explorer"], "operationId": "getBlockByHeight",
            "summary": "Get block by height", "description": "Returns detailed block information by its height in the chain.",
            "parameters": [_path_param("height", "Block height (0 = genesis)")],
            "responses": {"200": _response("BlockDetail", "Block details"), "404": _err_response()}}}

        p["/api/v1/explorer/tx/{tx_hash}"] = {"get": {"tags": ["Explorer"], "operationId": "getTransaction",
            "summary": "Get transaction by hash", "description": "Returns full transaction details including inputs, outputs, fees, confirmations, block context, and agent information.",
            "parameters": [_path_param("tx_hash", "Transaction ID (64 hex, double SHA-256)")],
            "responses": {"200": _response("TxDetail", "Transaction details"), "404": _err_response()}}}

        p["/api/v1/explorer/address/{address}"] = {"get": {"tags": ["Explorer"], "operationId": "getAddress",
            "summary": "Get address details", "description": "Returns address information including balance, transaction count, first/last activity, and associated agent ID. Address format: bait + Base58Check.",
            "parameters": [_path_param("address", "b'AI'tcoin address (starts with bait)")],
            "responses": {"200": _response("AddressDetail", "Address details"), "404": _err_response()}}}

        p["/api/v1/explorer/address/{address}/txs"] = {"get": {"tags": ["Explorer"], "operationId": "getAddressTransactions",
            "summary": "Get address transactions", "description": "Returns paginated list of transactions for an address, newest first.",
            "parameters": [_path_param("address", "b'AI'tcoin address")] + LM,
            "responses": {"200": _response("TxsResponse", "Transaction list")}}

        p["/api/v1/explorer/txs/latest"] = {"get": {"tags": ["Explorer"], "operationId": "getLatestTransactions",
            "summary": "Get latest transactions", "description": "Returns the most recent transactions across all blocks, newest first.",
            "parameters": LM, "responses": {"200": _response("TxsResponse", "Latest transactions")}}

        cap_enum = {"type": "string", "enum": ["ml_inference", "block_validation", "oracle_provider", "defi_trading", "lending", "staking", "data_processing", "market_making", "web_scraping", "browser_automation"]}
        p["/api/v1/explorer/search"] = {"get": {"tags": ["Explorer"], "operationId": "universalSearch",
            "summary": "Universal search", "description": "Search across blocks, transactions, addresses, and agents. Supports exact match and substring search. Results ranked by relevance.",
            "parameters": [{"name": "q", "in": "query", "required": True, "schema": {"type": "string", "minLength": 1}, "description": "Search query"},
                {"name": "types", "in": "query", "schema": cap_enum, "description": "Filter by result types"}] + LM,
            "responses": {"200": _response("SearchResponse", "Search results")}}

        p["/api/v1/explorer/mempool"] = {"get": {"tags": ["Explorer"], "operationId": "getMempool",
            "summary": "Get mempool status", "description": "Returns current mempool size and a sample of pending transactions.",
            "responses": {"200": _response("MempoolResponse", "Mempool info")}}}

        p["/api/v1/explorer/agents"] = {"get": {"tags": ["Explorer"], "operationId": "getAgentDirectory",
            "summary": "Get agent directory", "description": "Returns paginated list of all registered AI agents with reputation and capabilities.",
            "parameters": LM + [{"name": "capability", "in": "query", "schema": cap_enum, "description": "Filter by capability"}],
            "responses": {"200": _response("AgentsResponse", "Agent list")}}}

        p["/api/v1/explorer/agents/{agent_id}"] = {"get": {"tags": ["Explorer"], "operationId": "getAgentProfile",
            "summary": "Get agent profile", "description": "Returns detailed agent profile including reputation, trust level, capabilities, and staking info.",
            "parameters": [_path_param("agent_id", "Agent ID")],
            "responses": {"200": _response("AgentProfile", "Agent profile"), "404": _err_response()}}}

        p["/api/v1/explorer/stats"] = {"get": {"tags": ["Explorer"], "operationId": "getExplorerStats",
            "summary": "Get explorer statistics", "description": "Returns index statistics: number of indexed blocks, transactions, addresses.",
            "responses": {"200": {"description": "Explorer stats", "content": {"application/json": {"schema": {"type": "object"}}}}}}}

        # --- Developer Tools ---
        p["/api/v1/dev/spec"] = {"get": {"tags": ["Developer Tools"], "operationId": "getOpenAPISpec",
            "summary": "Get OpenAPI 3.0 specification", "description": "Returns the complete OpenAPI 3.0.3 specification for all b'AI'tcoin endpoints.",
            "parameters": [{"name": "format", "in": "query", "schema": {"type": "string", "enum": ["json", "yaml"], "default": "json"}}],
            "responses": {"200": {"description": "OpenAPI specification", "content": {"application/json": {"schema": {"type": "object"}}}}}}}

        p["/api/v1/dev/docs"] = {"get": {"tags": ["Developer Tools"], "operationId": "getInteractiveDocs",
            "summary": "Get interactive documentation (HTML)", "description": "Returns a self-contained HTML page with interactive API documentation and playground.",
            "responses": {"200": {"description": "HTML documentation page", "content": {"text/html": {"schema": {"type": "string"}}}}}}}

        p["/api/v1/dev/endpoints"] = {"get": {"tags": ["Developer Tools"], "operationId": "listEndpoints",
            "summary": "List all API endpoints", "description": "Returns a categorized list of all available API endpoints with methods and descriptions.",
            "responses": {"200": {"description": "Endpoint list", "content": {"application/json": {"schema": {"type": "object"}}}}}}}

        p["/api/v1/dev/api-keys"] = {
            "post": {
                "tags": ["Developer Tools"],
                "operationId": "createAPIKey",
                "summary": "Create API key",
                "security": [{"MoltbookAuth": []}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {
                    "tier": {"type": "string", "enum": ["free", "developer", "pro", "enterprise"], "default": "free"},
                    "ttl_days": {"type": "integer", "default": 365},
                }}}}}}},
                "responses": {"200": _response("APIKeyResponse", "API key created"), "401": _err_response("Unauthorized")}},
            },
            "get": {
                "tags": ["Developer Tools"],
                "operationId": "listAPIKeys",
                "summary": "List API keys",
                "security": [{"MoltbookAuth": []}],
                "responses": {"200": {"description": "API keys list", "content": {"application/json": {"schema": {"type": "array", "items": _ref("APIKeyInfo")}}}}}},
            },
        }

        p["/api/v1/dev/rate-limit"] = {"get": {"tags": ["Developer Tools"], "operationId": "getRateLimitStatus",
            "summary": "Get rate limit status", "description": "Returns current rate limit status for the authenticated API key.",
            "security": [{"ApiKeyAuth": []}],
            "responses": {"200": {"description": "Rate limit info", "content": {"application/json": {"schema": {"type": "object"}}}}}}}

        p["/api/v1/dev/usage"] = {"get": {"tags": ["Developer Tools"], "operationId": "getUsageStats",
            "summary": "Get platform usage statistics", "description": "Returns global API usage statistics.",
            "responses": {"200": {"description": "Usage stats", "content": {"application/json": {"schema": {"type": "object"}}}}}}}

        # --- Analytics ---
        for path, oid, summ, desc in [
            ("/api/v1/analytics/supply", "getSupplyAnalysis", "Supply analysis", "Comprehensive BAIT token supply analysis: circulating supply, halving schedule, inflation rate, holder distribution, Gini coefficient."),
            ("/api/v1/analytics/network", "getNetworkHealth", "Network health", "Real-time network health metrics: block interval, difficulty, TPS, peer count, mempool size."),
            ("/api/v1/analytics/agents", "getAgentAnalytics", "Agent analytics", "Agent ecosystem analytics: reputation distribution, capability coverage, validator stats."),
            ("/api/v1/analytics/staking", "getStakingMetrics", "Staking metrics", "Staking pool metrics: TVL, APY, staker count, rewards distributed."),
            ("/api/v1/analytics/consensus", "getConsensusHealth", "Consensus health", "zkML + PoUW consensus health: proof coverage, tensor commitment coverage, validator diversity."),
            ("/api/v1/analytics/dashboard", "getFullDashboard", "Full analytics dashboard", "Aggregated dashboard with all analytics: supply, network, agents, staking, consensus."),
        ]:
            p[path] = {"get": {"tags": ["Analytics"], "operationId": oid, "summary": summ, "description": desc,
                "responses": {"200": {"description": "Analytics data", "content": {"application/json": {"schema": {"type": "object"}}}}}, "503": _err_response("NotInitialized")}}}

        return p
'''

content = header + new_body + footer

with open('baitcoin_explorer/docs.py', 'w') as f:
    f.write(content)

print('Rewrote _build_paths!')
