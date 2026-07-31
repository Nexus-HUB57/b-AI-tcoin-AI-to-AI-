r"""
API REST b'AI'tcoin - Interface HTTP para o ecossistema.

Endpoints:
  GET  /api/v1/status          - Status da rede
  GET  /api/v1/blockchain      - Info da blockchain
  GET  /api/v1/block/:height   - Bloco por altura
  GET  /api/v1/token           - Info do token
  GET  /api/v1/balance/:agent  - Saldo de agente
  POST /api/v1/transfer        - Transferir BAIT
  POST /api/v1/faucet/claim    - Reclamar BAIT do faucet
  GET  /api/v1/faucet/balance  - Saldo via faucet
  GET  /api/v1/staking         - Info do staking
  POST /api/v1/staking/stake   - Fazer stake
  GET  /api/v1/agents          - Lista de agentes
  GET  /api/v1/marketplace     - Serviços do marketplace
  GET  /api/v1/oracle/:symbol  - Preço de ativo
  POST /api/v1/zkml/proof      - Verificar prova zkML
  GET  /api/v1/p2p/peers       - Lista de peers

Sem dependência de framework - usa apenas asyncio + http.server.
"""
import json
import asyncio
import hashlib
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs


class BaitcoinAPIHandler(BaseHTTPRequestHandler):
    r"""Handler HTTP para a API REST."""

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

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
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
        }
        handler = routes.get(path)
        if handler:
            handler()
        else:
            self._send_json({'error': 'not_found'}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # --- GET handlers ---
    def _get_status(self):
        self._send_json({
            'network': 'baitcoin-mainnet',
            'version': '0.2.0',
            'timestamp': time.time(),
            'blockchain_height': self.blockchain.height if self.blockchain else 0,
            'agents': len(self.agent_registry.agents) if self.agent_registry else 0,
            'peers': len(self.p2p_node._connections) if self.p2p_node else 0,
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
            self._send_json({'acknowledged': True, 'proof_id': body.get('proof_id', '')})
        except json.JSONDecodeError:
            self._send_json({'error': 'invalid_json'}, 400)


def create_app(host: str = '0.0.0.0', port: int = 18445) -> HTTPServer:
    r"""Cria e retorna o servidor HTTP."""
    return HTTPServer((host, port), BaitcoinAPIHandler)


def run_server(host: str = '0.0.0.0', port: int = 18445):
    r"""Roda o servidor HTTP (blocking)."""
    server = create_app(host, port)
    print(f"b'AI'tcoin API listening on {host}:{port}")
    server.serve_forever()
