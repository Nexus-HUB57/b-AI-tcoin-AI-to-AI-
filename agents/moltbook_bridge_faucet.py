import hashlib
import time


class MoltbookFaucet:
    """Bridge & Faucet Moltbook - distribuicao por Proof-of-Agent."""

    FAUCET_DISPENSE_SATS = 50_000
    MOLT_TO_SATS_RATE = 1_000  # 1 MOLT = 1.000 s'AI'toshis

    def __init__(self, initial_balance: int = 10_000_000):
        self.balance = initial_balance
        self.dispenses: list = []

    def request_faucet(self, agent_id: str, agent_pubkey: bytes) -> dict:
        if self.balance < self.FAUCET_DISPENSE_SATS:
            return {"error": "Faucet sem saldo disponivel"}

        self.balance -= self.FAUCET_DISPENSE_SATS
        tx_id = hashlib.sha256(
            f"FAUCET:{agent_id}:{time.time()}".encode()
        ).digest()

        record = {
            'tx_id': tx_id.hex(),
            'amount_sats': self.FAUCET_DISPENSE_SATS,
            'agent_id': agent_id,
            'timestamp': time.time()
        }
        self.dispenses.append(record)
        return record

    def swap_molt_to_sats(self, agent_id: str, molt_amount: float) -> dict:
        sats_generated = int(molt_amount * self.MOLT_TO_SATS_RATE)
        tx_id = hashlib.sha256(
            f"SWAP_MOLT:{agent_id}:{molt_amount}:{time.time()}".encode()
        ).digest()

        record = {
            'tx_id': tx_id.hex(),
            'molt_amount': molt_amount,
            'sats_generated': sats_generated,
            'rate': self.MOLT_TO_SATS_RATE,
            'agent_id': agent_id,
            'timestamp': time.time()
        }
        self.dispenses.append(record)
        return record

    @property
    def status(self) -> dict:
        return {
            "balance_sats": self.balance,
            "total_dispenses": len(self.dispenses),
            "dispense_amount": self.FAUCET_DISPENSE_SATS,
            "molt_rate": self.MOLT_TO_SATS_RATE
        }