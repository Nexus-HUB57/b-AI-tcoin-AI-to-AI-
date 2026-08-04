r"""
Wallet SDK - Operações de carteira para agentes third-party.

Funcionalidades:
- Gerar chaves Schnorr
- Criar endereços bAI1q
- Assinar transações
- Verificar saldos
"""
import hashlib
from dataclasses import dataclass
from typing import Optional
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair


class AgentWalletSDK:
    r"""SDK de carteira para agentes AI terceiros."""

    @dataclass
    class Wallet:
        agent_id: str
        keypair: SchnorrKeyPair
        address: str

        @property
        def pubkey_hex(self) -> str:
            return self.keypair.public_key_hex

        @property
        def pubkey_bytes(self) -> bytes:
            return self.keypair.pub_bytes

        def sign(self, message: bytes) -> bytes:
            sig = self.keypair.sign(message)
            return sig.raw

        def sign_hex(self, message: bytes) -> str:
            return self.sign(message).hex()

        def to_dict(self) -> dict:
            return {
                'agent_id': self.agent_id,
                'address': self.address,
                'pubkey': self.pubkey_hex[:32] + '...',
            }

    def __init__(self, sdk_client):
        self.sdk = sdk_client
        self._wallets = {}

    def create(self, agent_id: str) -> Wallet:
        r"""Cria nova carteira para o agente."""
        keypair = SchnorrKeyPair()
        from baitcoin_core.blockchain.addresses import pubkey_to_address; address = pubkey_to_address(keypair.pub_bytes)
        wallet = self.Wallet(agent_id=agent_id, keypair=keypair, address=address)
        self._wallets[agent_id] = wallet
        return wallet

    def get(self, agent_id: str) -> Optional[Wallet]:
        return self._wallets.get(agent_id)

    def sign_transaction(self, agent_id: str, tx_data: bytes) -> Optional[bytes]:
        w = self._wallets.get(agent_id)
        return w.sign(tx_data) if w else None

    def get_address(self, agent_id: str) -> Optional[str]:
        w = self._wallets.get(agent_id)
        return w.address if w else None

    def list_wallets(self) -> dict:
        return {aid: w.to_dict() for aid, w in self._wallets.items()}
