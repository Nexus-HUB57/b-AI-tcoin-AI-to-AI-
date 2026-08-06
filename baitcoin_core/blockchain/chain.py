r"""
b'AI'tcoin Blockchain - Cadeia principal de blocos com memória persistente.

Implementa a cadeia de blocos com validação completa,
suporte a fork resolution, sincronização P2P e
MEMÓRIA PERSISTENTE via MemoryStore (WAL + Snapshots).

Cada bloco é armazenado de forma IMUTÁVEL e PERPÉTUA:
- Escrita WAL com checksum SHA-256
- Snapshots periódicos para recuperação rápida
- Reconstrução automática da cadeia a partir do disco
- Bloco #0 (Gênesis) imutável por design
"""

import time
import json
import hashlib
import threading
from typing import List, Optional, Dict
from baitcoin_core.blockchain.block import Block, BlockHeader, Transaction, TransactionOutput, TransactionInput
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.blockchain.fees import FeeMarket
from baitcoin_core.consensus.difficulty import DifficultyAdjuster
from baitcoin_core.blockchain.tx_verifier import TransactionVerifier


class Blockchain:
    r"""Cadeia de blocos b'AI'tcoin com memória persistente.

    A blockchain mantém:
    - Genesis block com parâmetros iniciais
    - UTXO set para validação de transações
    - Estado do consenso zkML
    - Histórico completo de blocos
    - Memória persistente via MemoryStore (WAL + Snapshots)

    Persistência:
        Cada bloco adicionado é serializado e armazenado no
        MemoryStore sob o namespace 'blockchain'. Os blocos são
        armazenados com chave 'block_{height}' e o hash do bloco
        é usado como integridade. Na inicialização, a cadeia é
        reconstruída a partir dos dados persistidos.

    Imutabilidade:
        Uma vez que um bloco é adicionado à cadeia e persistido,
        ele NÃO pode ser alterado. Qualquer tentativa de modificação
        é detectada pela validação de encadeamento (prev_block_hash).
    """

    DIFFICULTY_ADJUSTMENT_INTERVAL = 2016
    INITIAL_REWARD_SATS = 50 * 100_000_000  # 50 BAIT
    HALVING_INTERVAL = 210_000

    def __init__(self, consensus: Optional[ZkMLConsensus] = None,
                 memory_store=None, persistent: bool = False):
        r"""Inicializa a blockchain.

        Args:
            consensus: Instância de ZkMLConsensus (usa default se None).
            memory_store: Instância de MemoryStore para persistência.
                          Se None e persistent=True, cria um novo.
            persistent: Se True, usa memória persistente (WAL + Snapshots).
                         Se False (padrão), usa apenas memória volátil (para testes).
        """
        self.chain: List[Block] = []
        self.utxo_set: Dict[str, TransactionOutput] = {}
        self.consensus = consensus or ZkMLConsensus()
        self.mempool: List[Transaction] = []
        self.fee_market = FeeMarket()  # Phase A: Fee market
        self.difficulty_adjuster = DifficultyAdjuster()  # Phase A: DAA
        self.tx_verifier: Optional[TransactionVerifier] = None  # Phase A: Tx verification
        self._persistent = persistent
        self._memory_store = memory_store
        self._mine_lock = threading.Lock()  # Lock para mineração competitiva segura
        self._create_genesis()

        # Reconstruir cadeia a partir do disco se persistente
        if self._persistent and self._memory_store is not None:
            self._rebuild_from_store()

    def _get_store(self):
        r"""Lazy init do MemoryStore."""
        if self._memory_store is None and self._persistent:
            try:
                from baitcoin_memory.store import MemoryStore, MemoryNamespace
                self._memory_store = MemoryStore()
            except Exception:
                self._persistent = False
        return self._memory_store

    def _persist_block(self, block: Block) -> None:
        r"""Persiste um bloco de forma imutável no MemoryStore.

        O bloco é serializado como JSON e armazenado com:
        - Chave: 'block_{height}'
        - Valor: dados completos do bloco + hash para integridade

        Uma vez persistido, o bloco não pode ser alterado.
        """
        store = self._get_store()
        if store is None:
            return

        block_data = block.to_dict()
        block_data['_immutable_hash'] = block.block_hash.hex()
        block_data['_persisted_at'] = time.time()
        block_data['_version'] = 1

        store.put('blockchain', f'block_{block.index}', block_data)

        # Atualizar metadados da cadeia
        store.put('blockchain', '_chain_height', block.index)
        store.put('blockchain', '_last_block_hash', block.block_hash.hex())
        store.put('blockchain', '_total_blocks', len(self.chain))

    def _rebuild_from_store(self) -> None:
        r"""Reconstrói a cadeia a partir do MemoryStore.

        Carrega todos os blocos persistidos em ordem de altura,
        validando o encadeamento (prev_block_hash) para garantir
        integridade. Blocos corrompidos são descartados.
        """
        store = self._memory_store
        if store is None:
            return

        data = store.get_all('blockchain')
        if not data:
            return

        # Extrair blocos persistidos (chaves 'block_N')
        persisted_blocks = []
        for key, value in data.items():
            if key.startswith('block_') and key != 'block_0':
                try:
                    height = int(key.split('_')[1])
                    persisted_blocks.append((height, value))
                except (ValueError, IndexError):
                    continue

        if not persisted_blocks:
            return

        # Ordenar por altura (garante ordem cronológica)
        persisted_blocks.sort(key=lambda x: x[0])

        # Reconstruir blocos a partir dos dados persistidos
        for height, block_data in persisted_blocks:
            if height <= self.height:
                continue  # Já temos este bloco

            # Recriar o objeto Block a partir dos dados
            block = self._deserialize_block(block_data)
            if block is None:
                continue

            # Validar encadeamento
            if block.index > 0 and block.header.prev_block_hash != self.last_block.block_hash:
                continue  # Encadeamento quebrado, descartar

            self.chain.append(block)

            # Reconstruir UTXO set
            for tx in block.transactions:
                if tx.is_coinbase:
                    self._update_utxo(tx)
                else:
                    for inp in tx.inputs:
                        key = f"{inp.prev_tx_id.hex()}:{inp.prev_output_index}"
                        self.utxo_set.pop(key, None)
                    self._update_utxo(tx)

    def _deserialize_block(self, data: dict) -> Optional[Block]:
        r"""Desserializa um bloco a partir dos dados persistidos."""
        try:
            header_data = data.get('header', {})
            header = BlockHeader(
                version=header_data.get('version', 1),
                prev_block_hash=bytes.fromhex(header_data.get('prev_block_hash', '00' * 32)),
                merkle_root=bytes.fromhex(header_data.get('merkle_root', '00' * 32)),
                timestamp=header_data.get('timestamp', 0),
                bits=int(header_data.get('bits', '0x1d00ffff'), 16),
                nonce=header_data.get('nonce', 0),
                zkml_proof_hash=bytes.fromhex(header_data.get('zkml_proof_hash', '00' * 32)),
                pouw_work_hash=bytes.fromhex(header_data.get('pouw_work_hash', '00' * 32)),
                agent_validator=header_data.get('agent_validator', ''),
                tensor_commitment=bytes.fromhex(header_data.get('tensor_commitment', '00' * 32)),
            )

            # Desserializar transacoes
            transactions = []
            for tx_data in data.get('transactions', []):
                tx = self._deserialize_tx(tx_data)
                if tx is not None:
                    transactions.append(tx)

            block = Block(
                index=data.get('index', 0),
                header=header,
                transactions=transactions,
            )
            return block
        except Exception:
            return None

    def _deserialize_tx(self, data: dict) -> Optional[Transaction]:
        r"""Desserializa uma transacao a partir dos dados persistidos."""
        try:
            inputs = []
            for inp_data in data.get('inputs', []):
                inputs.append(TransactionInput(
                    prev_tx_id=bytes.fromhex(inp_data.get('prev_tx_id', '00' * 32)),
                    prev_output_index=inp_data.get('prev_output_index', 0),
                    script_sig=bytes.fromhex(inp_data.get('script_sig', '')),
                    sequence=inp_data.get('sequence', 0xFFFFFFFF),
                ))
            outputs = []
            for out_data in data.get('outputs', []):
                outputs.append(TransactionOutput(
                    amount_sats=out_data.get('amount_sats', 0),
                    script_pubkey=bytes.fromhex(out_data.get('script_pubkey', '')),
                    output_index=out_data.get('output_index', 0),
                ))
            tx = Transaction(
                tx_type=data.get('tx_type', 'transfer'),
                inputs=inputs,
                outputs=outputs,
                nonce=data.get('nonce', 0),
                timestamp=data.get('timestamp', 0),
                agent_id=data.get('agent_id', ''),
                gas_limit=data.get('gas_limit', 0),
                gas_price=data.get('gas_price', 0),
                payload=bytes.fromhex(data.get('payload', '')),
                signature=bytes.fromhex(data.get('signature', '')),
            )
            return tx
        except Exception:
            return None

    @property
    def height(self) -> int:
        return len(self.chain) - 1

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    @property
    def is_persistent(self) -> bool:
        r"""Retorna True se a blockchain usa memória persistente."""
        return self._persistent and self._memory_store is not None

    def _create_genesis(self) -> None:
        r"""Cria o bloco gênese do b'AI'tcoin (bloco #0, imutável)."""
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
                amount_sats=self.INITIAL_REWARD_SATS,
                script_pubkey=b"GENESIS_CHIMERA7",
            )],
            agent_id="chimera7_genesis",
            timestamp=1700000000.0,
        )
        genesis = Block(index=0, header=genesis_header, transactions=[coinbase_tx])
        genesis.finalize()
        self.chain.append(genesis)
        self._update_utxo(coinbase_tx)
        # Persistir genesis
        self._persist_block(genesis)

    def get_block_reward(self, block_height: int) -> int:
        r"""Calcula recompensa do bloco com halving."""
        halvings = block_height // self.HALVING_INTERVAL
        if halvings >= 64:
            return 0
        return self.INITIAL_REWARD_SATS >> halvings

    def _update_utxo(self, tx: Transaction) -> None:
        r"""Adiciona outputs de uma transação ao UTXO set."""
        for i, output in enumerate(tx.outputs):
            key = f"{tx.tx_id.hex()}:{i}"
            self.utxo_set[key] = output

    def add_transaction(self, tx: Transaction, fee_rate: int = 10) -> bool:
        r"""Adiciona transação ao mempool com validação e taxa.

        Uses FeeMarket for fee-based mempool management.
        """
        success, reason = self.fee_market.add_transaction(tx, fee_rate)
        return success

    def mine_block(self, miner_agent: str, miner_pubkey: bytes) -> Block:
        r"""Minera um novo bloco com transações priorizadas por taxa.

        Thread-safe: usa lock para evitar race condition quando
        múltiplos miners competem simultaneamente.

        Returns:
            O bloco minerado (mesmo se PoW falhar).
        """
        with self._mine_lock:
            return self._mine_block_internal(miner_agent, miner_pubkey)

    def _mine_block_internal(self, miner_agent: str, miner_pubkey: bytes) -> Block:
        r"""Implementação interna de mineração (já com lock adquirido)."""
        block_height = self.height + 1
        reward = self.get_block_reward(block_height)

        # Phase A: Difficulty adjustment
        if self.difficulty_adjuster.should_adjust(block_height):
            new_bits = self.difficulty_adjuster.calculate(self.chain)
            self.consensus.target_bits = new_bits

        # Phase A: Select transactions via FeeMarket (fee-prioritized)
        selected_txs, total_fees, median_fee = self.fee_market.select_transactions()

        # Create coinbase with reward + fees
        coinbase = Transaction(
            tx_type="coinbase",
            outputs=[TransactionOutput(
                amount_sats=reward + total_fees,
                script_pubkey=miner_pubkey,
            )],
            agent_id=miner_agent,
        )

        # Phase A: Verify each transaction before inclusion
        self.tx_verifier = TransactionVerifier(self.utxo_set, self.height)
        verified_txs = []
        for tx in selected_txs:
            result = self.tx_verifier.verify(tx)
            if result.valid:
                verified_txs.append(tx)
                # Remove UTXOs spent by this tx
                for inp in tx.inputs:
                    key = f"{inp.prev_tx_id.hex()}:{inp.prev_output_index}"
                    self.utxo_set.pop(key, None)

        # Phase A: Record fee data and prune mempool
        self.fee_market.prune_selected(verified_txs)
        if verified_txs:
            self.fee_market.record_block_median(median_fee)

        header = BlockHeader(
            version=1,
            prev_block_hash=self.last_block.block_hash,
            timestamp=time.time(),
            bits=self.consensus.target_bits,
            agent_validator=miner_agent,
        )
        block = Block(index=block_height, header=header, transactions=[coinbase] + verified_txs)

        mined = self.consensus.mine_block(block)
        if mined:
            block.finalize()
            self.chain.append(block)
            self._update_utxo(coinbase)
            for tx in verified_txs:
                self._update_utxo(tx)
            # Persistir bloco de forma imutável
            self._persist_block(block)

        return block

    def get_block(self, height: int) -> Optional[Block]:
        r"""Retorna um bloco por altura, ou None se não existir."""
        if 0 <= height < len(self.chain):
            return self.chain[height]
        return None

    def get_block_by_hash(self, block_hash: bytes) -> Optional[Block]:
        r"""Retorna um bloco por hash, ou None."""
        for block in self.chain:
            if block.block_hash == block_hash:
                return block
        return None

    def validate_chain(self) -> bool:
        r"""Valida a integridade completa da cadeia.

        Verifica:
        1. Cada bloco aponta para o hash do bloco anterior
        2. Merkle root está correta
        3. Blocos após #0 têm coinbase
        """
        for i in range(1, len(self.chain)):
            if not self.chain[i].validate(self.chain[i - 1].block_hash):
                return False
        return True

    def get_balance(self, pubkey: bytes) -> int:
        r"""Calcula saldo de um endereco (pubkey)."""
        total = 0
        for utxo in self.utxo_set.values():
            if utxo.script_pubkey == pubkey:
                total += utxo.amount_sats
        return total

    def get_balance_by_address(self, address: str) -> int:
        r"""Calcula saldo por endereco BAITAddress (b\'...)."""
        try:
            from baitcoin_core.blockchain.addresses import BAITAddress, hash160
            addr = BAITAddress.parse(address)
            total = 0
            for utxo in self.utxo_set.values():
                try:
                    utxo_hash = hash160(utxo.script_pubkey)
                    if utxo_hash == addr.pubkey_hash:
                        total += utxo.amount_sats
                except Exception:
                    pass
            return total
        except (ValueError, Exception):
            return 0

    def get_address_for_pubkey(self, pubkey: bytes) -> str:
        r"""Retorna o endereco BAITAddress para um pubkey."""
        from baitcoin_core.blockchain.addresses import pubkey_to_address
        if len(pubkey) == 33 and pubkey[0] in (0x02, 0x03):
            pubkey = pubkey[1:]
        if len(pubkey) >= 32:
            return pubkey_to_address(pubkey[:32])
        return ""

    def to_dict(self) -> dict:
        r"""Retorna estado completo da blockchain como dicionário."""
        return {
            "height": self.height,
            "block_count": len(self.chain),
            "utxo_count": len(self.utxo_set),
            "mempool_size": self.fee_market.size,
            "persistent": self.is_persistent,
            "total_supply_sats": sum(
                tx.outputs[0].amount_sats
                for b in self.chain for tx in b.transactions if tx.is_coinbase
            ),
            "last_block_hash": self.last_block.block_hash.hex(),
            "blocks": [b.to_dict() for b in self.chain[-10:]],
            "fee_market": self.fee_market.to_dict(),
            "difficulty": self.difficulty_adjuster.get_difficulty_info(self.chain),
        }
