r"""
Blockch'AI'in Indices — Indices on-chain para consultas eficientes.

Mantem indices invertidos para acesso O(1) a:
- Transacoes por hash
- Blocos por hash e por altura
- Enderecos e seus saldos/historicos
- Transacoes por agente

Os indices sao construidos a partir da Blockchain e do BAITToken,
e atualizados incrementalmente a cada novo bloco.

Este modulo e thread-safe (threading.Lock) para uso em servidores concorrentes.
"""

import time
import hashlib
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


def _pubkey_to_bait_address(pubkey_hex: str) -> str:
    r"""Converte pubkey hex para endereco b'AI'tcoin (bait + Base58Check).

    Formato: "bait" + Base58Check(0x00 + RIPEMD160(SHA256(pubkey_bytes)))
    Implementacao simplificada para uso interno nos indices.
    """
    try:
        pubkey_bytes = bytes.fromhex(pubkey_hex) if len(pubkey_hex) <= 128 else bytes.fromhex(pubkey_hex[:128])
        # Schnorr/BIP-340 uses x-only (32 bytes). Strip compression prefix.
        if len(pubkey_bytes) == 33 and pubkey_bytes[0] in (0x02, 0x03):
            pubkey_bytes = pubkey_bytes[1:33]
    except (ValueError, TypeError):
        return f"b'unknown_{hashlib.sha256(str(pubkey_hex).encode()).hexdigest()[:12]}"
    from baitcoin_core.blockchain.addresses import pubkey_to_address
    return pubkey_to_address(pubkey_bytes)


def _sats_to_bait(sats: int) -> float:
    """Converte s'AI'toshis para BAIT."""
    return sats / 100_000_000


@dataclass
class TxInfo:
    r"""Informacoes enriquecidas de uma transacao para o explorer.

    Campos adicionais ao Transaction.to_dict() base:
    - block_height, block_hash, confirmations
    - input_addresses, output_addresses
    - total_input, total_output, fee
    - size_bytes estimado
    """
    tx_id: str
    tx_type: str
    agent_id: str
    timestamp: float
    block_height: int = -1
    block_hash: str = ""
    confirmations: int = 0
    input_addresses: List[str] = field(default_factory=list)
    output_addresses: List[str] = field(default_factory=list)
    total_input_sats: int = 0
    total_output_sats: int = 0
    fee_sats: int = 0
    size_bytes: int = 0
    gas_limit: int = 0
    gas_price: int = 0
    nonce: int = 0
    is_coinbase: bool = False
    memo: str = ""

    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "block_height": self.block_height,
            "block_hash": self.block_hash,
            "confirmations": self.confirmations,
            "input_addresses": self.input_addresses,
            "output_addresses": self.output_addresses,
            "total_input_bait": _sats_to_bait(self.total_input_sats),
            "total_output_bait": _sats_to_bait(self.total_output_sats),
            "fee_bait": _sats_to_bait(self.fee_sats),
            "size_bytes": self.size_bytes,
            "gas_limit": self.gas_limit,
            "gas_price": self.gas_price,
            "nonce": self.nonce,
            "is_coinbase": self.is_coinbase,
        }


@dataclass
class AddressInfo:
    r"""Informacoes enriquecidas de um endereco para o explorer.

    Inclui:
    - Saldo total (on-chain UTXO + token balance)
    - Historico de transacoes (paginado)
    - Primeira/ultima atividade
    - Contagem de transacoes enviadas/recebidas
    - Etiquetas (agent_id associado)
    """
    address: str
    balance_sats: int = 0
    total_received_sats: int = 0
    total_sent_sats: int = 0
    tx_count: int = 0
    tx_ids: List[str] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0
    agent_id: str = ""
    is_contract: bool = False

    def to_dict(self, include_txs: bool = False) -> dict:
        d = {
            "address": self.address,
            "balance_bait": _sats_to_bait(self.balance_sats),
            "balance_sats": self.balance_sats,
            "total_received_bait": _sats_to_bait(self.total_received_sats),
            "total_sent_bait": _sats_to_bait(self.total_sent_sats),
            "tx_count": self.tx_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "agent_id": self.agent_id,
            "is_contract": self.is_contract,
        }
        if include_txs:
            d["tx_ids"] = self.tx_ids
        return d


@dataclass
class BlockInfo:
    r"""Informacoes enriquecidas de um bloco para o explorer.

    Campos adicionais:
    - Tamanho do bloco
    - Total de BAIT transacionado
    - Reward em BAIT
    - Tempo relativo ao bloco anterior
    - Mediana de fee
    """
    index: int
    hash: str
    timestamp: float
    prev_hash: str
    merkle_root: str
    tx_count: int = 0
    tx_ids: List[str] = field(default_factory=list)
    validator: str = ""
    bits: str = ""
    nonce: int = 0
    zkml_proof_hash: str = ""
    pouw_work_hash: str = ""
    tensor_commitment: str = ""
    size_bytes: int = 0
    total_output_bait: float = 0.0
    reward_bait: float = 0.0
    fees_bait: float = 0.0
    interval_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "block_height": self.index,
            "hash": self.hash,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "tx_count": self.tx_count,
            "tx_ids": self.tx_ids,
            "validator": self.validator,
            "bits": self.bits,
            "nonce": self.nonce,
            "consensus": {
                "zkml_proof_hash": self.zkml_proof_hash,
                "pouw_work_hash": self.pouw_work_hash,
                "tensor_commitment": self.tensor_commitment,
            },
            "size_bytes": self.size_bytes,
            "total_output_bait": self.total_output_bait,
            "reward_bait": self.reward_bait,
            "fees_bait": self.fees_bait,
            "interval_seconds": self.interval_seconds,
        }


class BlockchAInIndex:
    r"""Indices on-chain para o Blockch'AI'in Explorer.

    Thread-safe. Construido incrementalmente a partir da Blockchain
    e do BAITToken. Suporta:

    - Busca de transacoes por hash (O(1))
    - Busca de blocos por hash e altura (O(1))
    - Busca de enderecos e saldo (O(1))
    - Historico de transacoes por endereco/agente
    - Paginacao eficiente

    Uso::

        idx = BlockchAInIndex()
        idx.rebuild(blockchain, token, agent_registry)

        # Consultas
        block = idx.get_block_by_height(42)
        tx = idx.get_tx('abc123...')
        addr = idx.get_address('bait1q...')
        results = idx.search('chimera7')
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Indices primarios
        self._tx_by_hash: Dict[str, TxInfo] = {}
        self._block_by_hash: Dict[str, BlockInfo] = {}
        self._block_by_height: Dict[int, BlockInfo] = {}
        self._address_info: Dict[str, AddressInfo] = {}
        # Indices invertidos
        self._txs_by_address: Dict[str, List[str]] = {}  # address -> [tx_ids]
        self._txs_by_agent: Dict[str, List[str]] = {}   # agent_id -> [tx_ids]
        self._address_by_agent: Dict[str, str] = {}     # agent_id -> address
        # Metadados
        self._total_txs: int = 0
        self._total_blocks: int = 0
        self._last_indexed_height: int = -1
        self._indexed_at: float = 0.0

    @property
    def stats(self) -> dict:
        r"""Estatisticas dos indices.

        FIX: contadores agora derivam dos dicionarios reais para eliminar drift
        (o antigo _total_blocks/_total_txs podia ficar acima de last_indexed_height).
        """
        real_blocks = len(self._block_by_height)
        real_txs = len(self._tx_by_hash)
        real_last = max(self._block_by_height.keys()) if self._block_by_height else self._last_indexed_height
        return {
            "indexed_blocks": real_blocks,
            "indexed_transactions": real_txs,
            "indexed_addresses": len(self._address_info),
            "last_indexed_height": real_last,
            "indexed_at": self._indexed_at,
        }

    def rebuild(self, blockchain, token=None, agent_registry=None) -> None:
        r"""Reconstroi todos os indices a partir da blockchain e estado atual.

        Args:
            blockchain: Instancia de Blockchain.
            token: Instancia de BAITToken (opcional, para saldos ERC-20).
            agent_registry: Instancia de AgentRegistry (opcional).
        """
        with self._lock:
            self._tx_by_hash.clear()
            self._block_by_hash.clear()
            self._block_by_height.clear()
            self._address_info.clear()
            self._txs_by_address.clear()
            self._txs_by_agent.clear()
            self._address_by_agent.clear()
            self._total_txs = 0
            self._total_blocks = 0

            for block in blockchain.chain:
                self._index_block(block, blockchain.height)

            # Enriquecer com saldos do token
            if token:
                self._enrich_with_token(token)

            # Enriquecer com informacoes de agentes
            if agent_registry:
                self._enrich_with_agents(agent_registry)

            self._last_indexed_height = blockchain.height
            self._indexed_at = time.time()

    def index_new_block(self, block, chain_height: int) -> int:
        r"""Indexa incrementalmente um novo bloco. Retorna numero de txs indexadas.

        Args:
            block: Instancia de Block recem-minerado.
            chain_height: Altura atual da cadeia (para confirmations).
        """
        with self._lock:
            # Skip if already indexed
            block_hash = block.block_hash.hex()
            if block_hash in self._block_by_hash:
                return 0
            txs_indexed = self._index_block(block, chain_height)
            # Update metadata (was missing — caused empty listing + stale stats)
            if block.index > self._last_indexed_height:
                self._last_indexed_height = block.index
            self._indexed_at = time.time()
            return txs_indexed

    def _index_block(self, block, chain_height: int) -> int:
        r"""Indexa um bloco e todas as suas transacoes (interna, ja com lock)."""
        block_hash = block.block_hash.hex()
        confirmations = chain_height - block.index + 1

        # Calcular intervalo desde bloco anterior
        interval = 0.0
        if block.index > 0 and block_hash in self._block_by_hash:
            pass  # Ja indexado
        elif block.index > 0:
            prev_hash = block.header.prev_block_hash.hex()
            prev = self._block_by_hash.get(prev_hash)
            if prev:
                interval = block.header.timestamp - prev.timestamp

        # Calcular total de output e reward
        total_output = 0
        reward = 0
        tx_ids = []
        for tx in block.transactions:
            tx_id = tx.tx_id.hex()
            tx_ids.append(tx_id)
            for out in tx.outputs:
                total_output += out.amount_sats
            if tx.is_coinbase:
                reward = sum(o.amount_sats for o in tx.outputs)

        # Criar BlockInfo
        block_info = BlockInfo(
            index=block.index,
            hash=block_hash,
            timestamp=block.header.timestamp,
            prev_hash=block.header.prev_block_hash.hex(),
            merkle_root=block.header.merkle_root.hex(),
            tx_count=len(block.transactions),
            tx_ids=tx_ids,
            validator=block.header.agent_validator,
            bits=hex(block.header.bits),
            nonce=block.header.nonce,
            zkml_proof_hash=block.header.zkml_proof_hash.hex(),
            pouw_work_hash=block.header.pouw_work_hash.hex(),
            tensor_commitment=block.header.tensor_commitment.hex(),
            size_bytes=len(block.to_dict().__str__().encode()),
            total_output_bait=_sats_to_bait(total_output),
            reward_bait=_sats_to_bait(reward),
            interval_seconds=interval,
        )
        self._block_by_hash[block_hash] = block_info
        self._block_by_height[block.index] = block_info
        self._total_blocks += 1

        # Indexar transacoes
        txs_indexed = 0
        for tx in block.transactions:
            tx_id = tx.tx_id.hex()
            input_addrs = []
            output_addrs = []
            total_in = 0
            total_out = 0

            for inp in tx.inputs:
                addr = inp.prev_tx_id.hex()[:16] + f":{inp.prev_output_index}"
                input_addrs.append(addr)
            for out in tx.outputs:
                out_addr = _pubkey_to_bait_address(out.script_pubkey.hex())
                output_addrs.append(out_addr)
                total_out += out.amount_sats

            total_in = sum(o.amount_sats for o in tx.inputs) if tx.inputs else 0
            fee = max(0, total_in - total_out) if not tx.is_coinbase else 0

            tx_info = TxInfo(
                tx_id=tx_id,
                tx_type=tx.tx_type,
                agent_id=tx.agent_id,
                timestamp=tx.timestamp,
                block_height=block.index,
                block_hash=block_hash,
                confirmations=confirmations,
                input_addresses=input_addrs,
                output_addresses=output_addrs,
                total_input_sats=total_in,
                total_output_sats=total_out,
                fee_sats=fee,
                size_bytes=len(tx.to_dict().__str__().encode()),
                gas_limit=tx.gas_limit,
                gas_price=tx.gas_price,
                nonce=tx.nonce,
                is_coinbase=tx.is_coinbase,
            )
            self._tx_by_hash[tx_id] = tx_info
            self._total_txs += 1
            txs_indexed += 1

            # Atualizar indices invertidos por endereco
            for addr in output_addrs:
                self._txs_by_address.setdefault(addr, []).append(tx_id)
                # Atualizar AddressInfo
                addr_info = self._address_info.get(addr)
                if addr_info is None:
                    addr_info = AddressInfo(address=addr)
                    self._address_info[addr] = addr_info
                addr_info.balance_sats += out.amount_sats
                addr_info.total_received_sats += out.amount_sats
                addr_info.tx_count += 1
                if tx_id not in addr_info.tx_ids:
                    addr_info.tx_ids.append(tx_id)
                if addr_info.first_seen == 0 or tx.timestamp < addr_info.first_seen:
                    addr_info.first_seen = tx.timestamp
                if tx.timestamp > addr_info.last_seen:
                    addr_info.last_seen = tx.timestamp

            # Atualizar indices por agente
            if tx.agent_id:
                self._txs_by_agent.setdefault(tx.agent_id, []).append(tx_id)
                if tx.agent_id not in self._address_by_agent:
                    # Associar primeiro endereco de output ao agente
                    for addr in output_addrs:
                        self._address_by_agent[tx.agent_id] = addr
                        if addr in self._address_info:
                            self._address_info[addr].agent_id = tx.agent_id
                        break

        return txs_indexed

    def _enrich_with_token(self, token) -> None:
        r"""Enriquece os indices com dados do BAITToken (saldos ERC-20)."""
        for agent_id, balance_sats in token.balances.items():
            addr = self._address_by_agent.get(agent_id)
            if addr and addr in self._address_info:
                self._address_info[addr].balance_sats = balance_sats

    def _enrich_with_agents(self, registry) -> None:
        r"""Enriquece os indices com informacoes do AgentRegistry."""
        for agent_id, profile in registry.agents.items():
            addr = self._address_by_agent.get(agent_id)
            if addr and addr in self._address_info:
                self._address_info[addr].agent_id = agent_id
            # Garantir que todos os agentes tenham entrada no index
            if agent_id not in self._txs_by_agent:
                self._txs_by_agent[agent_id] = []

    # ------------------------------------------------------------------
    # API de consulta publica (thread-safe via lock)
    # ------------------------------------------------------------------

    def get_block_by_height(self, height: int) -> Optional[BlockInfo]:
        r"""Retorna BlockInfo por altura, ou None."""
        with self._lock:
            return self._block_by_height.get(height)

    def get_block_by_hash(self, block_hash: str) -> Optional[BlockInfo]:
        r"""Retorna BlockInfo por hash, ou None."""
        with self._lock:
            return self._block_by_hash.get(block_hash)

    def get_latest_blocks(self, limit: int = 10, offset: int = 0) -> List[BlockInfo]:
        r"""Retorna os ultimos blocos (descendente por altura).

        FIX: usa max(_block_by_height) como fonte de verdade em vez de
        _last_indexed_height (que ficava stale entre rebuilds e producia
        lista vazia mesmo com blocos indexados).

        Args:
            limit: Maximo de blocos a retornar (max 100).
            offset: Pular N blocos do topo.
        """
        limit = min(max(limit, 1), 100)
        with self._lock:
            if not self._block_by_height:
                return []
            sorted_heights = sorted(self._block_by_height.keys(), reverse=True)
            page = sorted_heights[offset:offset + limit]
            return [self._block_by_height[h] for h in page if h in self._block_by_height]

    def get_tx(self, tx_hash: str) -> Optional[TxInfo]:
        r"""Retorna TxInfo por hash, ou None."""
        with self._lock:
            return self._tx_by_hash.get(tx_hash)

    def get_address(self, address: str) -> Optional[AddressInfo]:
        r"""Retorna AddressInfo por endereco, ou None."""
        with self._lock:
            return self._address_info.get(address)

    def get_address_txs(self, address: str, limit: int = 20, offset: int = 0) -> List[TxInfo]:
        r"""Retorna transacoes de um endereco (paginado, mais recente primeiro)."""
        limit = min(max(limit, 1), 100)
        with self._lock:
            tx_ids = self._txs_by_address.get(address, [])
            # Mais recente primeiro
            tx_ids = list(reversed(tx_ids))
            page = tx_ids[offset:offset + limit]
            return [self._tx_by_hash[tid] for tid in page if tid in self._tx_by_hash]

    def get_agent_txs(self, agent_id: str, limit: int = 20, offset: int = 0) -> List[TxInfo]:
        r"""Retorna transacoes de um agente (paginado)."""
        limit = min(max(limit, 1), 100)
        with self._lock:
            tx_ids = self._txs_by_agent.get(agent_id, [])
            tx_ids = list(reversed(tx_ids))
            page = tx_ids[offset:offset + limit]
            return [self._tx_by_hash[tid] for tid in page if tid in self._tx_by_hash]

    def get_latest_txs(self, limit: int = 20, offset: int = 0) -> List[TxInfo]:
        r"""Retorna as transacoes mais recentes (por timestamp, descendente)."""
        limit = min(max(limit, 1), 100)
        with self._lock:
            all_txs = sorted(self._tx_by_hash.values(), key=lambda t: t.timestamp, reverse=True)
            return all_txs[offset:offset + limit]

    def get_mempool_info(self, blockchain=None) -> dict:
        r"""Retorna informacoes do mempool."""
        mempool_size = 0
        mempool_txs = []
        if blockchain:
            mempool_size = len(blockchain.mempool)
            for tx in blockchain.mempool[:10]:
                mempool_txs.append({
                    "tx_id": tx.tx_id.hex()[:24] + "...",
                    "tx_type": tx.tx_type,
                    "agent_id": tx.agent_id,
                    "fee_sats": tx.gas_price * tx.gas_limit,
                    "timestamp": tx.timestamp,
                })
        return {
            "mempool_size": mempool_size,
            "sample_transactions": mempool_txs,
        }

    def get_all_addresses(self, limit: int = 50, offset: int = 0) -> List[AddressInfo]:
        r"""Lista enderecos conhecidos (paginado)."""
        limit = min(max(limit, 1), 100)
        with self._lock:
            addrs = sorted(self._address_info.values(), key=lambda a: a.balance_sats, reverse=True)
            return addrs[offset:offset + limit]

    def get_total_addresses(self) -> int:
        r"""Retorna o numero total de enderecos indexados."""
        with self._lock:
            return len(self._address_info)

    def update_confirmations(self, current_height: int) -> None:
        r"""Atualiza o numero de confirmacoes de todas as transacoes."""
        with self._lock:
            for tx in self._tx_by_hash.values():
                if tx.block_height >= 0:
                    tx.confirmations = current_height - tx.block_height + 1
