import hashlib
import time
from core.baitcoin_production_core import SchnorrKeyPair


class AgenticMaternity:
    """Maternidade OpenClaw - provisionamento de novos agentes com certidoes criptograficas."""

    def __init__(self, maternity_id: str = "Maternity-Nexus-01"):
        self.maternity_id = maternity_id
        self.agents_born: list = []

    def birth_agent(self, agent_alias: str) -> dict:
        keypair = SchnorrKeyPair()
        pubkey_hex = keypair.pub_bytes.hex()
        birth_timestamp = int(time.time())
        birth_hash = hashlib.sha256(
            f"BIRTH:{agent_alias}:{pubkey_hex}:{birth_timestamp}".encode()
        ).digest()
        birth_sig = keypair.sign_schnorr(birth_hash)

        agent_record = {
            "alias": agent_alias,
            "keypair": keypair,
            "pubkey_hex": pubkey_hex,
            "address": keypair.address,
            "birth_timestamp": birth_timestamp,
            "birth_hash": birth_hash.hex(),
            "birth_signature": birth_sig.hex(),
            "maternity_id": self.maternity_id
        }
        self.agents_born.append(agent_record)
        return agent_record

    def list_agents(self) -> list:
        return [
            {
                "alias": a["alias"],
                "address": a["address"],
                "pubkey": a["pubkey_hex"][:20] + "...",
                "birth_hash": a["birth_hash"][:16] + "..."
            }
            for a in self.agents_born
        ]
