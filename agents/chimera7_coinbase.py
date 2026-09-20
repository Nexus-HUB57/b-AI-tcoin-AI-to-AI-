import hashlib
import struct


class ChimeraCoinbaseAgent:
    """Agente Coinbase Chimera7 - emissao e fracionamento atomico em s'AI'toshis."""

    INITIAL_SUBSIDY = 50 * 100_000_000  # 50 BAIT em sats
    HALVING_INTERVAL = 210_000

    def __init__(self, agent_id: str = "Chimera7-Coinbase-Sentinel"):
        self.agent_id = agent_id

    def build_coinbase_transaction(self, block_height: int, mempool_fees: int, miner_pubkey: bytes) -> dict:
        total_reward = (self.INITIAL_SUBSIDY >> (block_height // self.HALVING_INTERVAL)) + mempool_fees
        coinbase_script = f"Chimera7/LiveBook-rRNA:Block#{block_height}:{self.agent_id}".encode()
        raw_cb = struct.pack("<I", block_height) + coinbase_script + miner_pubkey
        tx_id = hashlib.sha256(hashlib.sha256(raw_cb).digest()).digest()
        return {
            'id': tx_id,
            'is_coinbase': True,
            'inputs': [{
                'prev_tx_hash': b'\x00' * 32,
                'output_index': 0xFFFFFFFF,
                'coinbase_script': coinbase_script
            }],
            'outputs': [{
                'amount_sats': total_reward,
                'script_pubkey': miner_pubkey
            }]
        }

    def get_reward_at_height(self, block_height: int, mempool_fees: int = 0) -> int:
        halvings = block_height // self.HALVING_INTERVAL
        if halvings >= 64:
            return mempool_fees
        return (self.INITIAL_SUBSIDY >> halvings) + mempool_fees
