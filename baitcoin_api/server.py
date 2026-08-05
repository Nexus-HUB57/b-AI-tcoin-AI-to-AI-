r"""
API REST b'AI'tcoin - Interface HTTP para o ecossistema.

Endpoints (56 total):
  --- Core (25) ---
  GET  /api/v1/status          - Status da rede (com whitelabel)
  GET  /api/v1/blockchain      - Info da blockchain
  GET  /api/v1/block/:height   - Bloco por altura
  GET  /api/v1/token           - Info do token
  GET  /api/v1/balance/:agent  - Saldo de agente
  POST /api/v1/transfer        - Transferir BAIT (Moltbook protected)
  POST /api/v1/faucet/claim    - Reclamar BAIT do faucet (Moltbook protected)
  GET  /api/v1/faucet/balance/:agent - Saldo via faucet
  GET  /api/v1/staking         - Info do staking
  POST /api/v1/staking/stake   - Fazer stake (Moltbook protected)
  GET  /api/v1/agents          - Lista de agentes
  GET  /api/v1/marketplace          - Servicos do AI Store (com listings ativos)
  POST /api/v1/marketplace/list     - Listar novo servico no AI Store
  POST /api/v1/marketplace/purchase - Comprar servico
  POST /api/v1/marketplace/rate     - Avaliar servico comprado
  POST /api/v1/marketplace/search   - Buscar servicos com filtros
  GET  /api/v1/oracle/:symbol  - Preco de ativo
  POST /api/v1/zkml/proof      - Verificar prova zkML (Moltbook protected)
  GET  /api/v1/p2p/peers       - Lista de peers
  GET  /api/v1/moltbook/auth-stats - Stats do middleware Moltbook
  GET  /api/v1/auth/status     - Status auth Moltbook do request
  POST /api/v1/platform-faucets    - Lista faucets por plataforma IA (filtro)
  GET  /api/v1/platform-faucets/:platform - Faucet de plataforma especifica
  GET  /api/v1/whitelabel      - Info de whitelabel da deploy atual
  GET  /api/v1/whitelabel/css  - CSS variables do tema whitelabel
  GET  /api/v1/whitelabel/presets - Lista presets de whitelabel (70 plataformas)
  GET  /api/v1/obscura/status  - Status do Obscura browser bridge
  POST /api/v1/obscura/fetch   - Fetch pagina via Obscura (Moltbook protected)
  POST /api/v1/obscura/scrape  - Scrape paginas em paralelo (Moltbook protected)
  GET  /api/v1/obscura/tasks   - Lista tarefas de scraping do agente

  --- Blockch'AI'in Explorer (12) ---
  GET  /api/v1/explorer/blocks            - Ultimos blocos (paginado)
  GET  /api/v1/explorer/blocks/hash/{hash}  - Bloco por hash
  GET  /api/v1/explorer/blocks/height/{h}  - Bloco por altura
  GET  /api/v1/explorer/tx/{hash}          - Transacao por hash
  GET  /api/v1/explorer/address/{addr}     - Endereco (saldo, txs)
  GET  /api/v1/explorer/address/{addr}/txs - Txs do endereco
  GET  /api/v1/explorer/txs/latest         - Ultimas transacoes
  GET  /api/v1/explorer/search             - Busca universal on-chain
  GET  /api/v1/explorer/mempool            - Mempool status
  GET  /api/v1/explorer/agents             - Diretorio de agentes
  GET  /api/v1/explorer/agents/{id}         - Perfil do agente
  GET  /api/v1/explorer/stats              - Stats do explorer

  --- Developer Tools (7) ---
  GET  /api/v1/dev/spec          - OpenAPI 3.0 spec (JSON)
  GET  /api/v1/dev/docs          - Interactive docs (HTML playground)
  GET  /api/v1/dev/endpoints     - Lista todos os endpoints
  POST /api/v1/dev/api-keys      - Criar API key (Moltbook protected)
  GET  /api/v1/dev/api-keys      - Listar API keys
  GET  /api/v1/dev/rate-limit    - Rate limit status
  GET  /api/v1/dev/usage         - Stats de uso global

  --- Paper Wallet (2, public) ---
  GET  /api/v1/wallet/paper     - Generate paper wallet JSON (no auth)
  GET  /api/v1/wallet/paper/html - Generate paper wallet HTML for printing (no auth)

  --- Analytics (6) ---
  GET  /api/v1/analytics/supply      - Supply analysis
  GET  /api/v1/analytics/network     - Network health
  GET  /api/v1/analytics/agents      - Agent analytics
  GET  /api/v1/analytics/staking     - Staking metrics
  GET  /api/v1/analytics/consensus   - Consensus health
  GET  /api/v1/analytics/dashboard   - Full dashboard

Moltbook Auth:
  Headers: X-Moltbook-Identity (JWT token)
  Env: MOLTBOOK_APP_KEY (chave da app no Moltbook)
  Ref: https://moltbook.com/developers.md

Whitelabel:
  Todas as respostas incluem headers X-Network-Name, X-Token-Symbol, X-Deployment-Hash.
  70 presets prontos para plataformas IA (Manus, DeepSeek, Grok, etc.)

Sem dependencia de framework - usa apenas http.server.
"""
import json
import os
import hashlib
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from baitcoin_api.moltbook_auth import MoltbookAuthMiddleware
from baitcoin_whitelabel import WhitelabelEngine, WhitelabelConfig

logger = logging.getLogger(__name__)

# Instancia global do middleware Moltbook
moltbook_auth = MoltbookAuthMiddleware(
    app_key=os.environ.get('MOLTBOOK_APP_KEY', ''),
    audience='baitcoin.ecosystem',
)

# Whitelabel engine (default b'AI'tcoin branding)
_whitelabel_engine = None


def init_whitelabel(config=None):
    r"""Initialize whitelabel branding. Call once at startup."""
    global _whitelabel_engine
    from baitcoin_whitelabel.config import WhitelabelConfig as WC
    cfg = config or WC()
    _whitelabel_engine = WhitelabelEngine(cfg)
    return _whitelabel_engine


def get_whitelabel():
    r"""Get current whitelabel engine (lazy init with defaults)."""
    global _whitelabel_engine
    if _whitelabel_engine is None:
        from baitcoin_whitelabel.config import WhitelabelConfig as WC
        _whitelabel_engine = WhitelabelEngine(WC())
    return _whitelabel_engine


class BaitcoinAPIHandler(BaseHTTPRequestHandler):
    r"""Handler HTTP para a API REST b'AI'tcoin com Moltbook Auth + Whitelabel."""

    # Shared state (set by create_app)
    blockchain = None
    token = None
    faucet = None
    staking_pool = None
    agent_registry = None
    marketplace = None
    oracle = None
    zkml_verifier = None
    p2p_node = None
    platform_faucets = None  # Dict de faucets por plataforma IA
    obscura_bridge = None  # ObscuraBrowserBridge instance

    # Blockch'AI'in Explorer (set by create_app)
    explorer_index = None      # BlockchAInIndex instance
    explorer_search = None    # UniversalSearch instance
    explorer_analytics = None # OnChainAnalytics instance
    explorer_docs = None      # DeveloperDocs instance
    rate_limiter = None       # RateLimiter instance

    # Moltbook-protected routes (requerem X-Moltbook-Identity header)
    MOLTBOOK_PROTECTED_POST = {
        '/api/v1/transfer',
        '/api/v1/faucet/claim',
        '/api/v1/staking/stake',
        '/api/v1/zkml/proof',
        '/api/v1/obscura/fetch',
        '/api/v1/obscura/scrape',
        '/api/v1/dev/api-keys',
    }

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        # Whitelabel branding headers em todas as respostas
        try:
            wl = get_whitelabel()
            for k, v in wl.api_headers().items():
                self.send_header(k, v)
        except Exception:
            pass
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _read_body(self) -> bytes:
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length)

    def _parse_path(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def do_GET(self):
        path, query = self._parse_path()
        routes = {
            '/api/v1/status': self._get_status,
            '/api/v1/blockchain': self._get_blockchain,
            '/api/v1/token': self._get_token,
            '/api/v1/staking': self._get_staking,
            '/api/v1/agents': self._get_agents,
            '/api/v1/marketplace': self._get_marketplace,
            '/api/v1/p2p/peers': self._get_peers,
            '/api/v1/moltbook/auth-stats': self._get_moltbook_stats,
            '/api/v1/auth/status': self._get_auth_status_handler,
            '/api/v1/whitelabel': self._get_whitelabel_info,
            '/api/v1/whitelabel/css': self._get_whitelabel_css,
            '/api/v1/whitelabel/presets': self._get_whitelabel_presets,
            '/api/v1/obscura/status': self._get_obscura_status,
            '/api/v1/obscura/tasks': self._get_obscura_tasks,
            # Blockch'AI'in Explorer
            '/api/v1/explorer/blocks': self._get_explorer_blocks,
            '/api/v1/explorer/txs/latest': self._get_explorer_latest_txs,
            '/api/v1/explorer/search': self._get_explorer_search,
            '/api/v1/explorer/mempool': self._get_explorer_mempool,
            '/api/v1/explorer/agents': self._get_explorer_agents,
            '/api/v1/explorer/stats': self._get_explorer_stats,
            # Developer Tools
            '/api/v1/dev/spec': self._get_dev_spec,
            '/api/v1/dev/docs': self._get_dev_docs_html,
            '/api/v1/dev/endpoints': self._get_dev_endpoints,
            '/api/v1/dev/api-keys': self._get_dev_api_keys,
            '/api/v1/dev/rate-limit': self._get_dev_rate_limit,
            '/api/v1/dev/usage': self._get_dev_usage,
            # Paper Wallet (public, no auth)
            '/api/v1/wallet/paper': self._get_wallet_paper_json,
            '/api/v1/wallet/paper/html': self._get_wallet_paper_html,
            # Analytics
            '/api/v1/analytics/supply': self._get_analytics_supply,
            '/api/v1/analytics/network': self._get_analytics_network,
            '/api/v1/analytics/agents': self._get_analytics_agents,
            '/api/v1/analytics/staking': self._get_analytics_staking,
            '/api/v1/analytics/consensus': self._get_analytics_consensus,
            '/api/v1/analytics/dashboard': self._get_analytics_dashboard,
        }

        # Dynamic routes (core)
        if path.startswith('/api/v1/block/'):
            return self._get_block(path.split('/')[-1])
        if path.startswith('/api/v1/balance/'):
            return self._get_balance(path.split('/')[-1])
        if path.startswith('/api/v1/faucet/balance/'):
            return self._get_faucet_balance(path.split('/')[-1])
        if path.startswith('/api/v1/oracle/'):
            return self._get_oracle_price(path.split('/')[-1])
        if path.startswith('/api/v1/platform-faucets/'):
            return self._get_platform_faucet(path)

        # Dynamic routes (Blockch'AI'in Explorer)
        if path.startswith('/api/v1/explorer/blocks/hash/'):
            h = path.replace('/api/v1/explorer/blocks/hash/', '').strip('/')
            return self._get_explorer_block_by_hash(h)
        if path.startswith('/api/v1/explorer/blocks/height/'):
            h = path.replace('/api/v1/explorer/blocks/height/', '').strip('/')
            return self._get_explorer_block_by_height(h)
        if path.startswith('/api/v1/explorer/tx/'):
            tx_hash = path.replace('/api/v1/explorer/tx/', '').strip('/')
            return self._get_explorer_tx(tx_hash)
        if path.startswith('/api/v1/explorer/address/'):
            remainder = path.replace('/api/v1/explorer/address/', '')
            if '/txs' in remainder:
                addr = remainder.replace('/txs', '').strip('/')
                return self._get_explorer_address_txs(addr, query)
            else:
                return self._get_explorer_address(remainder.strip('/'))
        if path.startswith('/api/v1/explorer/agents/'):
            agent_id = path.replace('/api/v1/explorer/agents/', '').strip('/')
            return self._get_explorer_agent_profile(agent_id)

        handler = routes.get(path)
        if handler:
            handler()
        else:
            self._send_json({'error': 'not_found', 'path': path}, 404)

    def do_POST(self):
        path, _ = self._parse_path()
        routes = {
            '/api/v1/transfer': self._post_transfer,
            '/api/v1/faucet/claim': self._post_faucet_claim,
            '/api/v1/staking/stake': self._post_stake,
            '/api/v1/zkml/proof': self._post_zkml_proof,
            '/api/v1/platform-faucets': self._post_platform_faucets,
            '/api/v1/obscura/fetch': self._post_obscura_fetch,
            '/api/v1/obscura/scrape': self._post_obscura_scrape,
            '/api/v1/dev/api-keys': self._post_dev_api_key_create,
            '/api/v1/marketplace/list': self._post_marketplace_list,
            '/api/v1/marketplace/purchase': self._post_marketplace_purchase,
            '/api/v1/marketplace/rate': self._post_marketplace_rate,
            '/api/v1/marketplace/search': self._post_marketplace_search,
        }
        handler = routes.get(path)
        if handler:
            # Verificar Moltbook auth para rotas protegidas
            if path in self.MOLTBOOK_PROTECTED_POST:
                auth_error = self._verify_moltbook()
                if auth_error:
                    return self._send_json(auth_error, auth_error.pop('status', 401))
            handler()
        else:
            self._send_json({'error': 'not_found'}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Moltbook-Identity, Authorization')
        self.end_headers()

    # --- Moltbook Auth ---
    def _verify_moltbook(self) -> Optional[dict]:
        r"""Verifica identidade Moltbook. Retorna None se OK, ou dict de erro."""
        headers_dict = {k: v for k, v in self.headers.items()}
        token = moltbook_auth.extract_token(headers_dict)
        if not token:
            return {'success': False, 'error': 'No identity token provided',
                    'error_code': 'missing_token', 'hint': 'Include X-Moltbook-Identity header',
                    'status': 401}
        result = moltbook_auth.verify(token)
        if not result.success:
            resp = result.to_dict()
            resp['status'] = result.status_code
            if result.retry_after:
                resp['retry_after'] = result.retry_after
            return resp
        # Anexar agente verificado ao handler
        self.moltbook_agent = result.agent
        self.moltbook_headers = headers_dict
        return None

    def _get_auth_status(self):
        r"""Retorna info do agente Moltbook autenticado (se houver)."""
        headers_dict = {k: v for k, v in self.headers.items()}
        token = moltbook_auth.extract_token(headers_dict)
        if not token:
            return {'authenticated': False, 'moltbook_configured': moltbook_auth.is_configured}
        result = moltbook_auth.verify(token)
        if result.success and result.agent:
            return {
                'authenticated': True,
                'agent': result.agent.to_dict(),
                'trust_score': result.agent.trust_score,
                'moltbook_configured': moltbook_auth.is_configured,
            }
        return {'authenticated': False, 'moltbook_configured': moltbook_auth.is_configured}

    # --- GET handlers ---
    def _get_status(self):
        try:
            wl = get_whitelabel()
            network_name = wl.config.network_name
            branding = wl.branding_summary()
        except Exception:
            network_name = r"b'AI'tcoin"
            branding = {}
        self._send_json({
            'network': network_name,
            'version': '0.2.0',
            'timestamp': time.time(),
            'blockchain_height': self.blockchain.height if self.blockchain else 0,
            'agents': len(self.agent_registry.agents) if self.agent_registry else 0,
            'peers': len(self.p2p_node._connections) if self.p2p_node else 0,
            'whitelabel': branding,
        })

    def _get_blockchain(self):
        if not self.blockchain:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.blockchain.to_dict())

    def _get_block(self, height_str):
        if not self.blockchain:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            h = int(height_str)
            if 0 <= h < len(self.blockchain.chain):
                self._send_json(self.blockchain.chain[h].to_dict())
            else:
                self._send_json({'error': 'block_not_found'}, 404)
        except ValueError:
            self._send_json({'error': 'invalid_height'}, 400)

    def _get_token(self):
        if not self.token:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.token.to_dict())

    def _get_balance(self, agent_id):
        if not self.token:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json({
            'agent_id': agent_id,
            'balance_sats': self.token.balance_of(agent_id),
            'balance_bait': self.token.balance_bait(agent_id),
        })

    def _get_staking(self):
        if not self.staking_pool:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.staking_pool.to_dict())

    def _get_agents(self):
        if not self.agent_registry:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json({'agents': self.agent_registry.list_agents()})

    def _get_marketplace(self):
        if not self.marketplace:
            return self._send_json({'error': 'not_initialized'}, 503)
        mp = self.marketplace.to_dict()
        # Incluir listings ativos com detalhes
        mp['services'] = self.marketplace.search() if hasattr(self.marketplace, 'search') else []
        self._send_json(mp)

    def _get_peers(self):
        if not self.p2p_node:
            return self._send_json({'error': 'not_initialized'}, 503)
        # P2PNetwork usa get_stats(), P2PNode usa get_status()
        if hasattr(self.p2p_node, 'get_status'):
            self._send_json(self.p2p_node.get_status())
        elif hasattr(self.p2p_node, 'get_stats'):
            self._send_json(self.p2p_node.get_stats())
        else:
            self._send_json({'peers': [], 'node_id': getattr(self.p2p_node, 'node_id', 'unknown')})

    def _get_faucet_balance(self, agent_id):
        if not self.faucet:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json({
            'agent_id': agent_id,
            'balance_bait': self.faucet.get_balance(agent_id),
        })

    def _get_oracle_price(self, symbol):
        if not self.oracle:
            return self._send_json({'error': 'not_initialized'}, 503)
        price = self.oracle.get_price(symbol.upper())
        if price is None:
            return self._send_json({'error': 'price_unavailable', 'symbol': symbol}, 404)
        self._send_json({'symbol': symbol.upper(), 'price': price})

    # --- POST handlers ---
    def _post_transfer(self):
        if not self.token:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            body = json.loads(self._read_body())
            ok = self.token.transfer(
                body['from'], body['to'],
                int(body['amount_bait'] * 100_000_000),
                body.get('memo', ''),
            )
            self._send_json({'success': ok})
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self._send_json({'error': str(e)}, 400)

    def _post_faucet_claim(self):
        if not self.faucet:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            body = json.loads(self._read_body())
            result = self.faucet.claim(
                agent_id=body['agent_id'],
                pubkey_hex=body.get('pubkey_hex', ''),
                challenge_sig=body.get('challenge_sig', ''),
            )
            status = 200 if result.get('success') else 429
            self._send_json(result, status)
        except (json.JSONDecodeError, KeyError) as e:
            self._send_json({'error': str(e)}, 400)

    def _post_stake(self):
        if not self.staking_pool:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            body = json.loads(self._read_body())
            ok = self.staking_pool.stake(
                body['agent_id'],
                int(body['amount_bait'] * 100_000_000),
            )
            self._send_json({'success': ok})
        except (json.JSONDecodeError, KeyError) as e:
            self._send_json({'error': str(e)}, 400)

    def _post_zkml_proof(self):
        if not self.zkml_verifier:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            body = json.loads(self._read_body())
            agent = getattr(self, 'moltbook_agent', None)
            self._send_json({
                'acknowledged': True,
                'proof_id': body.get('proof_id', ''),
                'verified_by': agent.name if agent else 'anonymous',
            })
        except json.JSONDecodeError:
            self._send_json({'error': 'invalid_json'}, 400)

    # --- Moltbook + Platform Faucet endpoints ---
    def _get_moltbook_stats(self):
        r"""Stats do middleware de autenticacao Moltbook."""
        self._send_json(moltbook_auth.get_stats())

    def _get_auth_status_handler(self):
        r"""Retorna status de autenticacao Moltbook do request atual."""
        self._send_json(self._get_auth_status())

    def _get_platform_faucet(self, path: str):
        r"""Retorna faucet de uma plataforma IA especifica."""
        if not self.platform_faucets:
            return self._send_json({'error': 'platform_faucets_not_loaded'}, 503)
        platform = path.replace('/api/v1/platform-faucets/', '').strip('/')
        faucet_data = self.platform_faucets.get(platform.lower())
        if not faucet_data:
            available = list(self.platform_faucets.keys())
            return self._send_json({
                'error': 'platform_not_found',
                'platform': platform,
                'available_platforms': available,
            }, 404)
        self._send_json({
            'platform': platform,
            'faucet': {k: v for k, v in faucet_data.items() if k != 'private_key_hex'},
        })

    def _post_platform_faucets(self):
        r"""Lista todas as faucets de plataformas IA com filtros."""
        if not self.platform_faucets:
            return self._send_json({'error': 'platform_faucets_not_loaded'}, 503)
        try:
            body = json.loads(self._read_body()) if self.headers.get('Content-Length') else {}
        except json.JSONDecodeError:
            body = {}
        category = body.get('category', '')
        min_balance = body.get('min_balance_bait', 0)
        faucets = []
        for name, data in self.platform_faucets.items():
            if category and data.get('category', '') != category:
                continue
            if data.get('balance_bait', 0) < min_balance:
                continue
            faucets.append({
                'platform': name,
                'category': data.get('category', ''),
                'address': data.get('bait_address', ''),
                'public_key': data.get('public_key_hex', ''),
                'balance_bait': data.get('balance_bait', 0),
                'tx_hash': data.get('tx_hash', ''),
                'block_index': data.get('block_index', 0),
            })
        self._send_json({
            'total_faucets': len(faucets),
            'total_balance_bait': sum(f['balance_bait'] for f in faucets),
            'faucets': faucets,
        })

    # --- Whitelabel endpoints ---
    def _get_whitelabel_info(self):
        r"""Retorna info de whitelabel da deploy atual."""
        try:
            wl = get_whitelabel()
            self._send_json(wl.to_public_dict())
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _get_whitelabel_css(self):
        r"""Retorna CSS variables do whitelabel como text/css."""
        try:
            wl = get_whitelabel()
            self.send_response(200)
            self.send_header('Content-Type', 'text/css')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(wl.css_block().encode())
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # --- Obscura browser endpoints ---
    def _get_obscura_status(self):
        r"""Status do Obscura browser bridge."""
        if not self.obscura_bridge:
            return self._send_json({'error': 'obscura_not_initialized'}, 503)
        self._send_json(self.obscura_bridge.get_stats())

    def _post_obscura_fetch(self):
        r"""Fetch pagina via Obscura (Moltbook protected)."""
        if not self.obscura_bridge:
            return self._send_json({'error': 'obscura_not_initialized'}, 503)
        try:
            body = json.loads(self._read_body())
            agent = getattr(self, 'moltbook_agent', None)
            agent_id = agent.name if agent else body.get('agent_id', '')
            result = self.obscura_bridge.fetch_page(
                url=body['url'],
                dump=body.get('dump', 'html'),
                eval_js=body.get('eval', ''),
                wait_until=body.get('wait_until', 'load'),
                timeout=body.get('timeout', 0),
                agent_id=agent_id,
            )
            self._send_json(result.to_dict())
        except (json.JSONDecodeError, KeyError) as e:
            self._send_json({'error': str(e)}, 400)

    def _post_obscura_scrape(self):
        r"""Scrape paginas em paralelo via Obscura (Moltbook protected)."""
        if not self.obscura_bridge:
            return self._send_json({'error': 'obscura_not_initialized'}, 503)
        try:
            body = json.loads(self._read_body())
            agent = getattr(self, 'moltbook_agent', None)
            agent_id = agent.name if agent else body.get('agent_id', '')
            results = self.obscura_bridge.scrape_pages(
                urls=body['urls'],
                concurrency=body.get('concurrency', 10),
                eval_js=body.get('eval', ''),
                agent_id=agent_id,
            )
            self._send_json({
                'total': len(results),
                'results': [r.to_dict() for r in results],
            })
        except (json.JSONDecodeError, KeyError) as e:
            self._send_json({'error': str(e)}, 400)

    def _get_obscura_tasks(self):
        r"""Lista tarefas de scraping do agente autenticado."""
        self._send_json({'message': 'Use WebScrapingCapability for task management',
                         'obscura_stats': self.obscura_bridge.get_stats() if self.obscura_bridge else None})

    def _get_whitelabel_presets(self):
        r"""Lista todos os presets de whitelabel disponiveis (70 plataformas IA)."""
        from baitcoin_whitelabel.presets import PresetLibrary
        self._send_json(PresetLibrary.list_presets())

    # ==================================================================
    # Blockch'AI'in Explorer Handlers
    # ==================================================================

    def _get_explorer_blocks(self):
        r"""GET /api/v1/explorer/blocks?limit=N&offset=M"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        _, query = self._parse_path()
        limit = int(query.get('limit', ['20'])[0])
        offset = int(query.get('offset', ['0'])[0])
        blocks = self.explorer_index.get_latest_blocks(limit=limit, offset=offset)
        self._send_json({
            'total': self.explorer_index.stats['indexed_blocks'],
            'blocks': [b.to_dict() for b in blocks],
        })

    def _get_explorer_block_by_hash(self, block_hash):
        r"""GET /api/v1/explorer/blocks/hash/{hash}"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        block = self.explorer_index.get_block_by_hash(block_hash)
        if not block:
            return self._send_json({'error': 'block_not_found', 'hash': block_hash}, 404)
        self._send_json(block.to_dict())

    def _get_explorer_block_by_height(self, height_str):
        r"""GET /api/v1/explorer/blocks/height/{height}"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        try:
            h = int(height_str)
        except ValueError:
            return self._send_json({'error': 'invalid_height', 'height': height_str}, 400)
        block = self.explorer_index.get_block_by_height(h)
        if not block:
            return self._send_json({'error': 'block_not_found', 'height': h}, 404)
        self._send_json(block.to_dict())

    def _get_explorer_tx(self, tx_hash):
        r"""GET /api/v1/explorer/tx/{hash}"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        tx = self.explorer_index.get_tx(tx_hash)
        if not tx:
            return self._send_json({'error': 'tx_not_found', 'tx_hash': tx_hash}, 404)
        self._send_json(tx.to_dict())

    def _get_explorer_address(self, address):
        r"""GET /api/v1/explorer/address/{address}"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        addr = self.explorer_index.get_address(address)
        if not addr:
            return self._send_json({'error': 'address_not_found', 'address': address}, 404)
        self._send_json(addr.to_dict(include_txs=False))

    def _get_explorer_address_txs(self, address, query):
        r"""GET /api/v1/explorer/address/{address}/txs?limit=N&offset=M"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        limit = int(query.get('limit', ['20'])[0])
        offset = int(query.get('offset', ['0'])[0])
        txs = self.explorer_index.get_address_txs(address, limit=limit, offset=offset)
        addr = self.explorer_index.get_address(address)
        self._send_json({
            'address': address,
            'total_txs': addr.tx_count if addr else 0,
            'transactions': [t.to_dict() for t in txs],
        })

    def _get_explorer_latest_txs(self):
        r"""GET /api/v1/explorer/txs/latest?limit=N&offset=M"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        _, query = self._parse_path()
        limit = int(query.get('limit', ['20'])[0])
        offset = int(query.get('offset', ['0'])[0])
        txs = self.explorer_index.get_latest_txs(limit=limit, offset=offset)
        self._send_json({
            'total': self.explorer_index.stats['indexed_transactions'],
            'transactions': [t.to_dict() for t in txs],
        })

    def _get_explorer_search(self):
        r"""GET /api/v1/explorer/search?q=...&types=...&limit=N&offset=M"""
        if not self.explorer_search:
            return self._send_json({'error': 'search_not_initialized'}, 503)
        _, query = self._parse_path()
        q = query.get('q', [''])[0]
        if not q:
            return self._send_json({'error': 'query_required', 'hint': '?q=<search_term>'}, 400)
        types = query.get('types', [])
        limit = int(query.get('limit', ['20'])[0])
        offset = int(query.get('offset', ['0'])[0])
        results = self.explorer_search.query(q, types=types or None, limit=limit, offset=offset)
        self._send_json(results)

    def _get_explorer_mempool(self):
        r"""GET /api/v1/explorer/mempool"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        self._send_json(self.explorer_index.get_mempool_info(self.blockchain))

    def _get_explorer_agents(self):
        r"""GET /api/v1/explorer/agents?limit=N&offset=M&capability=..."""
        if not self.agent_registry:
            return self._send_json({'error': 'not_initialized'}, 503)
        _, query = self._parse_path()
        cap_str = query.get('capability', [''])[0]
        cap = None
        if cap_str:
            from baitcoin_ai.agent_protocol.registry import AgentCapability
            try:
                cap = AgentCapability(cap_str)
            except ValueError:
                return self._send_json({'error': 'invalid_capability', 'capability': cap_str}, 400)
        agents = self.agent_registry.list_agents(capability=cap)
        limit = int(query.get('limit', ['20'])[0])
        offset = int(query.get('offset', ['0'])[0])
        self._send_json({
            'total': len(agents),
            'agents': agents[offset:offset + limit],
        })

    def _get_explorer_agent_profile(self, agent_id):
        r"""GET /api/v1/explorer/agents/{agent_id}"""
        if not self.agent_registry:
            return self._send_json({'error': 'not_initialized'}, 503)
        profile = self.agent_registry.get_agent(agent_id)
        if not profile:
            return self._send_json({'error': 'agent_not_found', 'agent_id': agent_id}, 404)
        # Enriquecer com transacoes do explorer
        tx_count = 0
        if self.explorer_index:
            txs = self.explorer_index.get_agent_txs(agent_id, limit=1)
            tx_count = len(self.explorer_index._txs_by_agent.get(agent_id, []))
        self._send_json({
            'agent_id': profile.agent_id,
            'pubkey_hex': profile.pubkey_hex,
            'reputation': profile.reputation_score,
            'trust_level': profile.trust_level,
            'capabilities': [c.value for c in profile.capabilities],
            'stake_bait': profile.stake_sats / 100_000_000,
            'is_validator': profile.is_validator,
            'is_active': profile.is_active,
            'registered_at': profile.registered_at,
            'last_active': profile.last_active,
            'total_transactions': tx_count,
            'metadata': profile.metadata,
        })

    def _get_explorer_stats(self):
        r"""GET /api/v1/explorer/stats"""
        if not self.explorer_index:
            return self._send_json({'error': 'explorer_not_initialized'}, 503)
        self._send_json(self.explorer_index.stats)

    # ==================================================================
    # Paper Wallet Handlers (public, no auth)
    # ==================================================================

    def _get_wallet_paper_json(self):
        r"""GET /api/v1/wallet/paper - Generate a fresh paper wallet, return JSON."""
        try:
            from baitcoin_wallet.paper_wallet import generate_paper_wallet
            wallet = generate_paper_wallet()
            self._send_json({
                'success': True,
                'wallet': {
                    'address': wallet['address'],
                    'public_key': wallet['public_key'],
                    'public_key_uncompressed': wallet['public_key_uncompressed'],
                    'private_key': wallet['private_key'],
                    'timestamp': wallet['timestamp'],
                    'warning': wallet['warning'],
                },
            })
        except Exception as e:
            logger.exception("paper_wallet_json_error")
            self._send_json({'error': str(e)}, 500)

    def _get_wallet_paper_html(self):
        r"""GET /api/v1/wallet/paper/html - Generate a fresh paper wallet, return HTML for printing."""
        try:
            from baitcoin_wallet.paper_wallet import generate_paper_wallet, generate_paper_wallet_html
            wallet = generate_paper_wallet()
            html = generate_paper_wallet_html(wallet)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            try:
                wl = get_whitelabel()
                for k, v in wl.api_headers().items():
                    self.send_header(k, v)
            except Exception:
                pass
            self.end_headers()
            self.wfile.write(html.encode())
        except Exception as e:
            logger.exception("paper_wallet_html_error")
            self._send_json({'error': str(e)}, 500)

    # ==================================================================
    # Developer Tools Handlers
    # ==================================================================

    def _get_dev_spec(self):
        r"""GET /api/v1/dev/spec?format=json"""
        if not self.explorer_docs:
            return self._send_json({'error': 'docs_not_initialized'}, 503)
        spec = self.explorer_docs.get_spec()
        self._send_json(spec)

    def _get_dev_docs_html(self):
        r"""GET /api/v1/dev/docs - Interactive HTML playground."""
        if not self.explorer_docs:
            return self._send_json({'error': 'docs_not_initialized'}, 503)
        html = self.explorer_docs.get_playground_html()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        try:
            wl = get_whitelabel()
            for k, v in wl.api_headers().items():
                self.send_header(k, v)
        except Exception:
            pass
        self.end_headers()
        self.wfile.write(html.encode())

    def _get_dev_endpoints(self):
        r"""GET /api/v1/dev/endpoints"""
        if not self.explorer_docs:
            return self._send_json({'error': 'docs_not_initialized'}, 503)
        self._send_json(self.explorer_docs.list_all_endpoints())

    def _post_dev_api_key_create(self):
        r"""POST /api/v1/dev/api-keys - Create API key (Moltbook protected)."""
        if not self.rate_limiter:
            return self._send_json({'error': 'rate_limiter_not_initialized'}, 503)
        try:
            body = json.loads(self._read_body())
        except (json.JSONDecodeError, TypeError):
            body = {}
        agent = getattr(self, 'moltbook_agent', None)
        agent_id = agent.name if agent else body.get('agent_id', 'anonymous')
        tier = body.get('tier', 'free')
        ttl = body.get('ttl_days', 365)
        result = self.rate_limiter.create_key(agent_id=agent_id, tier=tier, ttl_days=ttl)
        self._send_json(result)

    def _get_dev_api_keys(self):
        r"""GET /api/v1/dev/api-keys"""
        if not self.rate_limiter:
            return self._send_json({'error': 'rate_limiter_not_initialized'}, 503)
        agent = getattr(self, 'moltbook_agent', None)
        agent_id = agent.name if agent else None
        keys = self.rate_limiter.list_keys(agent_id=agent_id)
        self._send_json({'api_keys': keys, 'total': len(keys)})

    def _get_dev_rate_limit(self):
        r"""GET /api/v1/dev/rate-limit"""
        if not self.rate_limiter:
            return self._send_json({'error': 'rate_limiter_not_initialized'}, 503)
        # Try to get API key from Authorization header
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bait '):
            api_key = auth[5:]
            info = self.rate_limiter.verify_key(api_key)
            if info:
                return self._send_json({
                    'authenticated': True,
                    'agent_id': info.agent_id,
                    'tier': info.tier,
                    'total_requests': info.total_requests,
                    'last_used': info.last_used,
                })
        self._send_json({'authenticated': False, 'hint': 'Use Authorization: Bait <api_key>'})

    def _get_dev_usage(self):
        r"""GET /api/v1/dev/usage"""
        if not self.rate_limiter:
            return self._send_json({'error': 'rate_limiter_not_initialized'}, 503)
        self._send_json(self.rate_limiter.get_usage_stats())

    # ==================================================================
    # Analytics Handlers
    # ==================================================================

    def _get_analytics_supply(self):
        r"""GET /api/v1/analytics/supply"""
        if not self.explorer_analytics or not self.blockchain:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.explorer_analytics.supply_analysis(self.blockchain, self.token))

    def _get_analytics_network(self):
        r"""GET /api/v1/analytics/network"""
        if not self.explorer_analytics or not self.blockchain:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.explorer_analytics.network_health(self.blockchain, self.p2p_node))

    def _get_analytics_agents(self):
        r"""GET /api/v1/analytics/agents"""
        if not self.explorer_analytics:
            return self._send_json({'error': 'not_initialized'}, 503)
        if not self.agent_registry:
            return self._send_json({'total': 0, 'agents': []})
        self._send_json(self.explorer_analytics.agent_analysis(self.agent_registry))

    def _get_analytics_staking(self):
        r"""GET /api/v1/analytics/staking"""
        if not self.explorer_analytics:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.explorer_analytics.staking_analysis(self.staking_pool))

    def _get_analytics_consensus(self):
        r"""GET /api/v1/analytics/consensus"""
        if not self.explorer_analytics or not self.blockchain:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.explorer_analytics.consensus_health(self.blockchain))

    def _get_analytics_dashboard(self):
        r"""GET /api/v1/analytics/dashboard"""
        if not self.explorer_analytics or not self.blockchain:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.explorer_analytics.full_dashboard(
            self.blockchain, self.token, self.agent_registry,
            self.staking_pool, self.p2p_node
        ))


    # ═══════════════════════════════════════════════════════════
    # AI MARKETPLACE POST ENDPOINTS
    # ═══════════════════════════════════════════════════════════

    def _post_marketplace_list(self):
        r"""POST /api/v1/marketplace/list — Listar novo servico no AI Store.

        Body: {provider, category, name, description, price_sats}
        """
        if not self.marketplace:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            body = json.loads(self._read_body().decode())
        except Exception:
            return self._send_json({'error': 'invalid_json'}, 400)
        from baitcoin_ai.marketplace.services import ServiceCategory
        cat_map = {c.value: c for c in ServiceCategory}
        category = cat_map.get(body.get('category'))
        if not category:
            return self._send_json({'error': 'invalid_category', 'valid': list(cat_map.keys())}, 400)
        lid = self.marketplace.list_service(
            provider=body.get('provider', 'anonymous'),
            category=category,
            name=body.get('name', ''),
            description=body.get('description', ''),
            price_sats=int(body.get('price_sats', 0)),
        )
        self._send_json({'success': True, 'listing_id': lid})

    def _post_marketplace_purchase(self):
        r"""POST /api/v1/marketplace/purchase — Comprar servico no AI Store.

        Body: {listing_id, buyer_agent}
        """
        if not self.marketplace:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            body = json.loads(self._read_body().decode())
        except Exception:
            return self._send_json({'error': 'invalid_json'}, 400)
        pid = self.marketplace.purchase_service(
            listing_id=body.get('listing_id', ''),
            buyer=body.get('buyer_agent', 'anonymous'),
        )
        if pid:
            self._send_json({'success': True, 'purchase_id': pid})
        else:
            self._send_json({'error': 'listing_not_found_or_inactive'}, 404)

    def _post_marketplace_rate(self):
        r"""POST /api/v1/marketplace/rate — Avaliar servico comprado.

        Body: {purchase_id, score (1.0-5.0)}
        """
        if not self.marketplace:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            body = json.loads(self._read_body().decode())
        except Exception:
            return self._send_json({'error': 'invalid_json'}, 400)
        ok = self.marketplace.rate_service(
            purchase_id=body.get('purchase_id', ''),
            score=float(body.get('score', 3.0)),
        )
        if ok:
            self._send_json({'success': True})
        else:
            self._send_json({'error': 'purchase_not_found'}, 404)

    def _post_marketplace_search(self):
        r"""POST /api/v1/marketplace/search — Buscar servicos com filtros.

        Body: {category?, max_price?, min_rating?}
        """
        if not self.marketplace:
            return self._send_json({'error': 'not_initialized'}, 503)
        try:
            body = json.loads(self._read_body().decode())
        except Exception:
            return self._send_json({'error': 'invalid_json'}, 400)
        from baitcoin_ai.marketplace.services import ServiceCategory
        cat = ServiceCategory(body['category']) if body.get('category') else None
        results = self.marketplace.search(
            category=cat,
            max_price=body.get('max_price'),
            min_rating=float(body.get('min_rating', 0.0)),
        )
        self._send_json({'results': results, 'count': len(results)})


def create_app(host: str = '0.0.0.0', port: int = 18445) -> HTTPServer:
    r"""Cria e retorna o servidor HTTP com whitelabel + Blockch'AI'in inicializado."""
    init_whitelabel()
    # Inicializar Blockch'AI'in Explorer (sera populado pelo daemon)
    from baitcoin_explorer.indices import BlockchAInIndex
    from baitcoin_explorer.search import UniversalSearch
    from baitcoin_explorer.analytics import OnChainAnalytics
    from baitcoin_explorer.docs import DeveloperDocs
    from baitcoin_explorer.rate_limiter import RateLimiter

    BaitcoinAPIHandler.explorer_index = BlockchAInIndex()
    BaitcoinAPIHandler.explorer_search = UniversalSearch(BaitcoinAPIHandler.explorer_index)
    BaitcoinAPIHandler.explorer_analytics = OnChainAnalytics()
    BaitcoinAPIHandler.explorer_docs = DeveloperDocs()
    BaitcoinAPIHandler.rate_limiter = RateLimiter()

    return HTTPServer((host, port), BaitcoinAPIHandler)


def run_server(host: str = '0.0.0.0', port: int = 18445):
    r"""Roda o servidor HTTP (blocking)."""
    server = create_app(host, port)
    print(f"b'AI'tcoin API + Blockch'AI'in Explorer listening on {host}:{port}")
    server.serve_forever()

    # Phase A: Signed transaction broadcast endpoint
    def _handle_tx_broadcast(self):
        r"""POST /api/v1/transactions/broadcast — Broadcast a signed transaction.

        Request body (JSON):
            inputs: [{prev_tx_id, prev_output_index, script_sig}]
            outputs: [{amount_sats, script_pubkey_hex}]
            nonce: int
            agent_id: str
            signature: hex string (64 bytes)
            gas_limit: int (optional)
            gas_price: int (optional)
            payload: hex string (optional)
        """
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_len).decode()) if content_len > 0 else {}
        except Exception:
            self._json_response({"error": "invalid_json"}, 400)
            return

        # Build Transaction object
        from baitcoin_core.blockchain.block import Transaction, TransactionInput, TransactionOutput

        inputs = []
        for inp in body.get('inputs', []):
            inputs.append(TransactionInput(
                prev_tx_id=bytes.fromhex(inp['prev_tx_id']),
                prev_output_index=inp['prev_output_index'],
                script_sig=bytes.fromhex(inp.get('script_sig', '')),
            ))

        outputs = []
        for out in body.get('outputs', []):
            outputs.append(TransactionOutput(
                amount_sats=out['amount_sats'],
                script_pubkey=bytes.fromhex(out['script_pubkey_hex']),
            ))

        signature = bytes.fromhex(body.get('signature', '')) if body.get('signature') else b''
        payload = bytes.fromhex(body.get('payload', '')) if body.get('payload') else b''

        tx = Transaction(
            tx_type=body.get('tx_type', 'transfer'),
            inputs=inputs,
            outputs=outputs,
            nonce=body.get('nonce', 0),
            agent_id=body.get('agent_id', ''),
            gas_limit=body.get('gas_limit', 0),
            gas_price=body.get('gas_price', 0),
            payload=payload,
            signature=signature,
        )

        # Add to mempool via blockchain's fee market
        fee_rate = body.get('fee_rate', 10)
        success = self.server.blockchain.add_transaction(tx, fee_rate)

        if success:
            self._json_response({
                "success": True,
                "tx_id": tx.tx_id.hex(),
                "mempool_size": self.server.blockchain.fee_market.size,
            })
        else:
            self._json_response({"error": "transaction_rejected", "reason": "fee_too_low"}, 400)

    # Register broadcast endpoint in POST routes
    POST_ROUTES['/api/v1/transactions/broadcast'] = _handle_tx_broadcast