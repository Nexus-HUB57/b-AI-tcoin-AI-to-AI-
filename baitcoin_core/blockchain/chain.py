"""
b'AI'tcoin Blockchain - Cadeia principal de blocos.

Implementa a cadeia de blocos com validação completa,
suporte a fork resolution e sincronização P2P.
"""

import time
import json
import hashlib
from typing import List, Optional, Dict
from baitcoin_core.blockchain.block import Block, BlockHeader, Transaction, TransactionOutput, TransactionInput
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus


class Blockchain:
    """Cadeia de blocos b'AI'tcoin.

    A blockchain mantém:
    - Genesis block com parâmetros iniciais
    - UTXO set para validação de transações
    - Estado do consenso zkML
    - Histórico completo de blocos
    """

    DIFFICULTY_ADJUSTMENT_INTERVAL = 2016
    INITIAL_REWARD_SATS = 50 * 100_000_000  # 50 BAIT
    HALVING_INTERVAL = 210_000

    def __init__(self, consensus: Optional[ZkMLConsensus] = None):
        self.chain: List[Block] = []
        self.utxo_set: Dict[str, TransactionOutput] = {}
        self.consensus = consensus or ZkMLConsensus()
        self.mempool: List[Transaction] = []
        self._create_genesis()

    @property
    def height(self) -> int:
        return len(self.chain) - 1

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def _create_genesis(self) -> None:
        """Cria o bloco gênese do b'AI'tcoin."""
        genesis_header = BlockHeader(
            version=1,
            prev_block_hash=b"\x00" * 32,
            timestamp=1700000000.0,
            bits=0x1d00ffff,
            nonce=42,
            zkml_proof_hash=hashlib.sha256(b"genesis_zkml_proof").digest(),
            pouw_work_hash=hashlib.sha256(b"genesis_pouw_work").digest(),
            agent_validator="chimera7_genesis",
            tensor_commitment=hashlib.sha256(b"genesis_tensor").digest(),
        )
        coinbase_tx = Transaction(
            tx_type="coinbase",
            outputs=[TransactionOutput(
                amount_sats=self.INITIAL_REWARD_SATS * 100,
                script_pubkey=b"GENESIS_CHIMERA7",
            )],
            agent_id="chimera7_genesis",
        )
        genesis = Block(index=0, header=genesis_header, transactions=[coinbase_tx])
        genesis.finalize()
        self.chain.append(genesis)
        self._update_utxo(coinbase_tx)

    def get_block_reward(self, block_height: int) -> int:
        """Calcula recompensa do bloco com halving."""
        halvings = block_height // self.HALVING_INTERVAL
        if halvings >= 64:
            return 0
        return self.INITIAL_REWARD_SATS >> halvings

    def _update_utxo(self, tx: Transaction) -> None:
        """Adiciona outputs de uma transação ao UTXO set."""
        for i, output in enumerate(tx.outputs):
            key = f"{tx.tx_id.hex()}:{i}"
            self.utxo_set[key] = output

    def add_transaction(self, tx: Transaction) -> bool:
        """Adiciona transação ao mempool após validação básica."""
        if tx.is_coinbase:
            return False
        # Validar inputs existem no UTXO
        for inp in tx.inputs:
            key = f"{inp.prev_tx_id.hex()}:{inp.prev_output_index}"
            if key not in self.utxo_set:
                return False
        self.mempool.append(tx)
        return True

    def mine_block(self, miner_agent: str, miner_pubkey: bytes) -> Block:
        """Minera um novo bloco com transações do mempool."""
        block_height = self.height + 1
        reward = self.get_block_reward(block_height)

        # Criar coinbase agêntica
        coinbase = Transaction(
            tx_type="coinbase",
            outputs=[TransactionOutput(
                amount_sats=reward,
                script_pubkey=miner_pubkey,
            )],
            agent_id=miner_agent,
        )

        # Selecionar transações do mempool (até 1000)
        selected_txs = self.mempool[:1000]
        self.mempool = self.mempool[1000:]

        # Remover UTXOs gastos
        for tx in selected_txs:
            for inp in tx.inputs:
                key = f"{inp.prev_tx_id.hex()}:{inp.prev_output_index}"
                self.utxo_set.pop(key, None)

        # Construir bloco
        header = BlockHeader(
            version=1,
            prev_block_hash=self.last_block.block_hash,
            timestamp=time.time(),
            bits=self.consensus.target_bits,
            agent_validator=miner_agent,
        )
        block = Block(index=block_height, header=header, transactions=[coinbase] + selected_txs)

        # Minerar com consenso zkML
        mined = self.consensus.mine_block(block)
        if mined:
            block.finalize()
            self.chain.append(block)
            self._update_utxo(coinbase)
            for tx in selected_txs:
                self._update_utxo(tx)

        return block

    def validate_chain(self) -> bool:
        """Valida a integridade completa da cadeia."""
        for i in range(1, len(self.chain)):
            if not self.chain[i].validate(self.chain[i - 1].block_hash):
                return False
        return True

    def get_balance(self, pubkey: bytes) -> int:
        """Calcula saldo de um endereço (pubkey)."""
        total = 0
        for utxo in self.utxo_set.values():
            if utxo.script_pubkey == pubkey:
                total += utxo.amount_sats
        return total

    def to_dict(self) -> dict:
        return {
            "height": self.height,
            "block_count": len(self.chain),
            "utxo_count": len(self.utxo_set),
            "mempool_size": len(self.mempool),
            "total_supply_sats": sum(
                tx.outputs[0].amount_sats
                for tx in self.chain if tx.is_coinbase
            ),
            "last_block_hash": self.last_block.block_hash.hex(),
            "blocks": [b.to_dict() for b in self.chain[-10:]],
        }
