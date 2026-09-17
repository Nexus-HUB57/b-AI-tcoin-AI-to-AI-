r"""
Gerenciador de Chaves - Cria e gerencia pares de chaves para agentes AI.

Cada agente AI possui sua própria carteira com:
- Chave Schnorr (BIP-340) para assinatura
- ID do agente derivado da chave pública
- Histórico de transações
"""

import hashlib
from typing import Dict, List, Optional
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair


class KeyManager:
    r"""Gerenciador de chaves para múltiplos agentes AI.

    Funcionalidades:
    - Gerar novos pares de chaves por agente
    - Derivar agent_id a partir da pubkey
    - Assinar transações em nome do agente
    - Gerenciar múltiplas identidades
    """

    def __init__(self):
        self._keys: Dict[str, SchnorrKeyPair] = {}

    def create_agent_wallet(self, agent_id: Optional[str] = None) -> str:
        r"""Cria uma nova carteira para um agente AI."""
        keypair = SchnorrKeyPair()
        if agent_id is None:
            agent_id = self._derive_agent_id(keypair.pub_bytes)
        self._keys[agent_id] = keypair
        return agent_id

    def _derive_agent_id(self, pubkey: bytes) -> str:
        r"""Deriva ID do agente a partir da chave pública."""
        return f"agent_{hashlib.sha256(pubkey).hexdigest()[:12]}"

    def get_keypair(self, agent_id: str) -> Optional[SchnorrKeyPair]:
        r"""Retorna o par de chaves de um agente."""
        return self._keys.get(agent_id)

    def sign_transaction(self, agent_id: str, tx_data: bytes) -> Optional[bytes]:
        r"""Assina dados de transação em nome do agente."""
        keypair = self.get_keypair(agent_id)
        if keypair is None:
            return None
        sig = keypair.sign(tx_data)
        return sig.raw

    def get_pubkey(self, agent_id: str) -> Optional[bytes]:
        r"""Retorna a chave pública de um agente."""
        keypair = self.get_keypair(agent_id)
        return keypair.pub_bytes if keypair else None

    def list_agents(self) -> List[str]:
        r"""Lista todos os agentes registrados."""
        return list(self._keys.keys())

    def to_dict(self) -> dict:
        return {
            "agents": len(self._keys),
            "agent_ids": list(self._keys.keys()),
        }
