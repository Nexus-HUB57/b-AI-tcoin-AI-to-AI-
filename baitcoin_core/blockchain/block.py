"""
Bloco b'AI'tcoin - Estrutura de dados fundamental da cadeia.

Cada bloco contém:
- Header com metadados de consenso (zkML proof, PoUW hash)
- Lista de transações (incluindo coinbase agêntica)
- Merkle root das transações
- Assinatura do validador
"""

import hashlib
import json
import struct
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TransactionOutput:
    """UTXO-like output para b'AI'tcoin."""
    amount_sats: int
    script_pubkey: bytes
    output_index: int = 0

    def to_dict(self) -> dict:
        return {
            "amount_sats": self.amount_sats,
            "script_pubkey": self.script_pubkey.hex(),
            "output_index": self.output_index,
        }


@dataclass
class TransactionInput:
    """Referência a um output anterior (UTXO spending)."""
    prev_tx_id: bytes
    prev_output_index: int
    script_sig: bytes = b""
    sequence: int = 0xFFFFFFFF

    def to_dict(self) -> dict:
        return {
            "prev_tx_id": self.prev_tx_id.hex(),
            "prev_output_index": self.prev_output_index,
            "script_sig": self.script_sig.hex(),
            "sequence": self.sequence,
        }


@dataclass
class Transaction:
    """Transação b'AI'tcoin - suporta pagamentos AI-to-AI.

    Tipos de transação:
    - coinbase: recompensa de mineração (agêntica)
    - transfer: transferência entre entidades AI
    - stake: transação de staking
    - contract_deploy: deploy de contrato inteligente AI
    """
    tx_type: str = "transfer"
    inputs: List[TransactionInput] = field(default_factory=list)
    outputs: List[TransactionOutput] = field(default_factory=list)
    nonce: int = 0
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""
    gas_limit: int = 0
    gas_price: int = 0
    payload: bytes = b""
    signature: bytes = b""

    @property
    def tx_id(self) -> bytes:
        """Calcula o hash da transação (sem assinatura)."""
        tx_data = self._serialize_unsigned()
        return hashlib.sha256(hashlib.sha256(tx_data).digest()).digest()

    @property
    def is_coinbase(self) -> bool:
        return self.tx_type == "coinbase"

    def _serialize_unsigned(self) -> bytes:
        """Serializa a transação para hashing (sem assinatura)."""
        data = {
            "tx_type": self.tx_type,
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "gas_limit": self.gas_limit,
            "gas_price": self.gas_price,
            "payload": self.payload.hex(),
        }
        return json.dumps(data, sort_keys=True).encode()

    def serialize(self) -> bytes:
        """Serialização completa incluindo assinatura."""
        return self._serialize_unsigned() + self.signature

    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id.hex(),
            "tx_type": self.tx_type,
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "gas_limit": self.gas_limit,
            "gas_price": self.gas_price,
            "payload": self.payload.hex(),
            "signature": self.signature.hex(),
        }

    def __repr__(self) -> str:
        return f"Transaction(id={self.tx_id.hex()[:16]}..., type={self.tx_type}, agent={self.agent_id})"


@dataclass
class BlockHeader:
    """Header do bloco b'AI'tcoin.

    Contém metadados de consenso zkML e PoUW.
    """
    version: int = 1
    prev_block_hash: bytes = b"\x00" * 32
    merkle_root: bytes = b"\x00" * 32
    timestamp: float = field(default_factory=time.time)
    bits: int = 0x1d00ffff  # dificuldade inicial
    nonce: int = 0

    # Campos específicos do consenso b'AI'tcoin
    zkml_proof_hash: bytes = b"\x00" * 32
    pouw_work_hash: bytes = b"\x00" * 32
    agent_validator: str = ""
    tensor_commitment: bytes = b"\x00" * 32

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "prev_block_hash": self.prev_block_hash.hex(),
            "merkle_root": self.merkle_root.hex(),
            "timestamp": self.timestamp,
            "bits": hex(self.bits),
            "nonce": self.nonce,
            "zkml_proof_hash": self.zkml_proof_hash.hex(),
            "pouw_work_hash": self.pouw_work_hash.hex(),
            "agent_validator": self.agent_validator,
            "tensor_commitment": self.tensor_commitment.hex(),
        }


class Block:
    """Bloco completo da b'AI'tcoin blockchain.

    Composição:
    - Header com provas de consenso
    - Transações validadas
    - Metadados de mineração agêntica
    """

    def __init__(
        self,
        index: int = 0,
        header: Optional[BlockHeader] = None,
        transactions: Optional[List[Transaction]] = None,
    ):
        self.index = index
        self.header = header or BlockHeader()
        self.transactions = transactions or []

    @property
    def block_hash(self) -> bytes:
        """Hash SHA-256 duplo do header do bloco."""
        header_data = json.dumps(self.header.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(hashlib.sha256(header_data).digest()).digest()

    @property
    def coinbase_tx(self) -> Optional[Transaction]:
        """Retorna a transação coinbase se existir."""
        for tx in self.transactions:
            if tx.is_coinbase:
                return tx
        return None

    def compute_merkle_root(self) -> bytes:
        """Calcula a Merkle root das transações do bloco."""
        if not self.transactions:
            return b"\x00" * 32

        hashes = [tx.tx_id for tx in self.transactions]

        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_level.append(hashlib.sha256(combined).digest())
            hashes = new_level

        return hashes[0]

    def finalize(self) -> None:
        """Finaliza o bloco: calcula merkle root e atualiza header."""
        self.header.merkle_root = self.compute_merkle_root()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "hash": self.block_hash.hex(),
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
            "tx_count": len(self.transactions),
        }

    def __repr__(self) -> str:
        return (
            f"Block(#{self.index}, hash={self.block_hash.hex()[:16]}..., "
            f"txs={len(self.transactions)}, validator={self.header.agent_validator})"
        )

    def validate(self, prev_block_hash: bytes) -> bool:
        """Validação básica do bloco."""
        if self.header.prev_block_hash != prev_block_hash:
            return False
        if self.header.merkle_root != self.compute_merkle_root():
            return False
        if self.index > 0 and not self.coinbase_tx:
            return False
        return True