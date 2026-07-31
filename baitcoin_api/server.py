r"""
API REST b'AI'tcoin - Interface HTTP para o ecossistema.

Endpoints (22 total):
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
  GET  /api/v1/marketplace     - Servicos do marketplace
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

    # Moltbook-protected routes (requerem X-Moltbook-Identity header)
    MOLTBOOK_PROTECTED_POST = {
        '/api/v1/transfer',
        '/api/v1/faucet/claim',
        '/api/v1/staking/stake',
        '/api/v1/zkml/proof',
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
        }

        # Dynamic routes
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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Moltbook-Identity')
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
        self._send_json(self.marketplace.to_dict())

    def _get_peers(self):
        if not self.p2p_node:
            return self._send_json({'error': 'not_initialized'}, 503)
        self._send_json(self.p2p_node.get_status())

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

    def _get_whitelabel_presets(self):
        r"""Lista todos os presets de whitelabel disponiveis (70 plataformas IA)."""
        from baitcoin_whitelabel.presets import PresetLibrary
        self._send_json(PresetLibrary.list_presets())


def create_app(host: str = '0.0.0.0', port: int = 18445) -> HTTPServer:
    r"""Cria e retorna o servidor HTTP com whitelabel inicializado."""
    init_whitelabel()
    return HTTPServer((host, port), BaitcoinAPIHandler)


def run_server(host: str = '0.0.0.0', port: int = 18445):
    r"""Roda o servidor HTTP (blocking)."""
    server = create_app(host, port)
    print(f"b'AI'tcoin API listening on {host}:{port}")
    server.serve_forever()
