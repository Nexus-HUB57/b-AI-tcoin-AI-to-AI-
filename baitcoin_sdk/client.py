r"""SDK Client - Ponto de entrada principal para integracao."""

import json
import time
from typing import Dict, List, Optional, Any
from urllib.request import Request, urlopen
from urllib.error import URLError
from baitcoin_sdk.wallet_sdk import AgentWalletSDK
from baitcoin_sdk.staking_sdk import StakingSDK
from baitcoin_sdk.marketplace_sdk import MarketplaceSDK


class BaitcoinSDK:
    DEFAULT_ENDPOINT = 'http://localhost:18445'

    def __init__(self, endpoint: Optional[str] = None, api_key: str = ''):
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.api_key = api_key
        self.wallet_sdk = AgentWalletSDK(self)
        self.staking_sdk = StakingSDK(self)
        self.marketplace_sdk = MarketplaceSDK(self)
        self._local_mode = True
        self._blockchain = None
        self._token = None
        self._faucet = None
        self._staking = None
        self._registry = None
        self._marketplace = None
        self._oracle = None

    def _request(self, method: str, path: str, body: dict = None) -> dict:
        url = f'{self.endpoint}{path}'
        data = json.dumps(body).encode() if body else None
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except URLError:
            return {'error': 'connection_failed'}

    def configure_local(self, blockchain, token, faucet, staking,
                        registry, marketplace, oracle) -> None:
        self._local_mode = True
        self._blockchain = blockchain
        self._token = token
        self._faucet = faucet
        self._staking = staking
        self._registry = registry
        self._marketplace = marketplace
        self._oracle = oracle

    def get_status(self) -> dict:
        return self._request('GET', '/api/v1/status')

    def get_balance(self, agent_id: str) -> float:
        if self._token and self._local_mode:
            return self._token.balance_bait(agent_id)
        resp = self._request('GET', f'/api/v1/balance/{agent_id}')
        return resp.get('balance_bait', 0.0)

    def transfer(self, from_agent: str, to_agent: str, amount_bait: float,
                memo: str = '') -> bool:
        if self._token and self._local_mode:
            return self._token.transfer(
                from_agent, to_agent,
                int(amount_bait * 100_000_000), memo,
            )
        resp = self._request('POST', '/api/v1/transfer', {
            'from': from_agent, 'to': to_agent,
            'amount_bait': amount_bait, 'memo': memo,
        })
        return resp.get('success', False)

    def faucet_claim(self, agent_id: str, pubkey_hex: str,
                      challenge_sig: str = '') -> dict:
        if self._faucet and self._local_mode:
            return self._faucet.claim(agent_id, pubkey_hex, challenge_sig)
        return self._request('POST', '/api/v1/faucet/claim', {
            'agent_id': agent_id, 'pubkey_hex': pubkey_hex,
            'challenge_sig': challenge_sig,
        })

    def stake(self, agent_id: str, amount_bait: float) -> bool:
        if self._staking and self._local_mode:
            return self._staking.stake(agent_id, int(amount_bait * 100_000_000))
        resp = self._request('POST', '/api/v1/staking/stake', {
            'agent_id': agent_id, 'amount_bait': amount_bait,
        })
        return resp.get('success', False)

    def get_price(self, symbol: str) -> Optional[float]:
        if self._oracle and self._local_mode:
            return self._oracle.get_price(symbol.upper())
        resp = self._request('GET', f'/api/v1/oracle/{symbol}')
        return resp.get('price')

    def register_agent(self, agent_id: str, pubkey_hex: str,
                       capabilities: List[str] = None) -> bool:
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        caps = [AgentCapability(c) for c in (capabilities or [])]
        if self._registry and self._local_mode:
            return self._registry.register(agent_id, pubkey_hex, caps)
        return False

    def get_blockchain_info(self) -> dict:
        if self._blockchain and self._local_mode:
            return self._blockchain.to_dict()
        return self._request('GET', '/api/v1/blockchain')

    def get_token_info(self) -> dict:
        if self._token and self._local_mode:
            return self._token.to_dict()
        return self._request('GET', '/api/v1/token')

    def get_staking_info(self) -> dict:
        if self._staking and self._local_mode:
            return self._staking.to_dict()
        return self._request('GET', '/api/v1/staking')

    def get_agents(self) -> List[dict]:
        if self._registry and self._local_mode:
            return self._registry.list_agents()
        resp = self._request('GET', '/api/v1/agents')
        return resp.get('agents', [])

    def create_wallet(self, agent_id: str):
        return self.wallet_sdk.create(agent_id)

    def search_services(self, category: str = None,
                         max_price: int = None) -> List[dict]:
        return self.marketplace_sdk.search(category, max_price)

    def get_network_status(self) -> dict:
        return {
            'blockchain': self.get_blockchain_info(),
            'token': self.get_token_info(),
            'staking': self.get_staking_info(),
            'agents': len(self.get_agents()),
        }
