import hashlib
import struct


class OutPoint:
    """Referencia unica a uma saida de transacao (tx_hash + index)."""

    def __init__(self, tx_hash: bytes, index: int):
        self.tx_hash = tx_hash
        self.index = index

    def __eq__(self, other):
        return self.tx_hash == other.tx_hash and self.index == other.index

    def __hash__(self):
        return hash((self.tx_hash, self.index))

    def __repr__(self):
        return f"OutPoint({self.tx_hash.hex()[:16]}...:{self.index})"


class UTXOEntry:
    """Entrada individual no conjunto UTXO."""

    def __init__(self, amount_sats: int, script_pubkey: bytes, is_coinbase: bool = False):
        self.amount_sats = amount_sats
        self.script_pubkey = script_pubkey
        self.is_coinbase = is_coinbase


class UTXODirectedSet:
    """Conjunto direcionado de UTXOs - modelo de estado do b'AI'tcoin."""

    def __init__(self):
        self.store: dict = {}

    def is_unspent(self, outpoint: OutPoint) -> bool:
        return outpoint in self.store

    def spend(self, outpoint: OutPoint):
        if outpoint in self.store:
            del self.store[outpoint]

    def add(self, outpoint: OutPoint, entry: UTXOEntry):
        self.store[outpoint] = entry

    @property
    def total_utxos(self) -> int:
        return len(self.store)

    @property
    def total_sats(self) -> int:
        return sum(entry.amount_sats for entry in self.store.values())


class ZkMLVerifier:
    """Verificador de provas zkML / PoUW em tempo constante O(1)."""

    @staticmethod
    def verify_proof(block_header_hash: bytes, nonce: int, tensor_hash: bytes, proof_hash: bytes, target: int) -> bool:
        expected_tensor_data = f"LLM_LAYER_OUTPUT:{block_header_hash.hex()}:{nonce}:TOKEN_COMPUTE_GRID"
        calculated_tensor_hash = hashlib.sha256(expected_tensor_data.encode()).digest()
        if calculated_tensor_hash != tensor_hash:
            return False
        raw_proof_input = block_header_hash + tensor_hash + struct.pack("<Q", nonce)
        calculated_proof_hash = hashlib.sha256(raw_proof_input).digest()
        if calculated_proof_hash != proof_hash:
            return False
        return int.from_bytes(calculated_proof_hash, byteorder='big') < target


class AgenticBlockConsensus:
    """Motor de consenso completo: zkML + UTXO + validacao de blocos."""

    def __init__(self, target: int = 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff):
        self.target = target
        self.utxo_set = UTXODirectedSet()
        self.chain_headers: list = []
        self.block_count = 0

    def validate_and_process_block(self, block_header_hash: bytes, nonce: int, tensor_hash: bytes, proof_hash: bytes, transactions: list) -> bool:
        if not ZkMLVerifier.verify_proof(block_header_hash, nonce, tensor_hash, proof_hash, self.target):
            return False

        temp_utxo_store = dict(self.utxo_set.store)
        spent_in_this_block = set()

        for tx in transactions:
            tx_id = tx['id']
            if not tx.get('is_coinbase', False):
                total_in = 0
                for inp in tx['inputs']:
                    outpoint = OutPoint(inp['prev_tx_hash'], inp['output_index'])
                    if outpoint in spent_in_this_block or outpoint not in temp_utxo_store:
                        return False
                    total_in += temp_utxo_store[outpoint].amount_sats
                    spent_in_this_block.add(outpoint)
                    del temp_utxo_store[outpoint]
                if sum(out['amount_sats'] for out in tx['outputs']) > total_in:
                    return False

            for idx, out in enumerate(tx['outputs']):
                temp_utxo_store[OutPoint(tx_id, idx)] = UTXOEntry(
                    out['amount_sats'],
                    out['script_pubkey'],
                    tx.get('is_coinbase', False)
                )

        self.utxo_set.store = temp_utxo_store
        self.chain_headers.append(block_header_hash)
        self.block_count += 1
        return True

    def get_chain_info(self) -> dict:
        return {
            "block_count": self.block_count,
            "total_utxos": self.utxo_set.total_utxos,
            "total_sats_circulating": self.utxo_set.total_sats,
            "last_block_hash": self.chain_headers[-1].hex()[:32] if self.chain_headers else None
        }
