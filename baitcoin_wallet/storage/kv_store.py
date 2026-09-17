r"""
Armazenamento Local - KV Store para wallet.

Persiste dados da carteira em disco usando formato JSON.
Suporta múltiplas carteiras por agente.
"""

import json
import os
from typing import Any, Dict, Optional


class WalletStorage:
    r"""Armazenamento chave-valor para carteiras.

    Estrutura em disco:
    /wallet_data/
      ├── agent_xxxx.json
      ├── agent_yyyy.json
      └── metadata.json
    """

    def __init__(self, base_path: str = "./wallet_data"):
        self.base_path = base_path
        self._cache: Dict[str, dict] = {}
        os.makedirs(base_path, exist_ok=True)

    def save_wallet(self, agent_id: str, data: dict) -> None:
        r"""Salva dados da carteira de um agente."""
        filepath = os.path.join(self.base_path, f"{agent_id}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        self._cache[agent_id] = data

    def load_wallet(self, agent_id: str) -> Optional[dict]:
        r"""Carrega dados da carteira de um agente."""
        if agent_id in self._cache:
            return self._cache[agent_id]
        filepath = os.path.join(self.base_path, f"{agent_id}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'r') as f:
            data = json.load(f)
        self._cache[agent_id] = data
        return data

    def delete_wallet(self, agent_id: str) -> bool:
        r"""Remove carteira de um agente."""
        filepath = os.path.join(self.base_path, f"{agent_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        self._cache.pop(agent_id, None)
        return True

    def list_wallets(self) -> list:
        r"""Lista todos os agentes com carteiras salvas."""
        return [f.replace('.json', '') for f in os.listdir(self.base_path)
                if f.endswith('.json')]

    def to_dict(self) -> dict:
        return {
            "base_path": self.base_path,
            "wallets": self.list_wallets(),
            "cached": len(self._cache),
        }
