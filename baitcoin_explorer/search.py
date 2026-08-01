r"""
Blockch'AI'in Search — Busca universal on-chain.

Motor de busca que opera sobre todos os indices do explorer,
permitindo que agentes AI encontrem rapidamente:

- Blocos (por hash, altura, validador)
- Transacoes (por hash, agente, tipo)
- Enderecos (por endereco bait, agente)
- Agentes (por ID, capability, reputacao)

A busca suporta:
- Match exato (prefixo com '0x' ou 'bait')
- Match por substring (case-insensitive)
- Filtro por tipo de resultado
- Paginacao
- Highlight dos campos encontrados

Uso::

    search = UniversalSearch(explorer_index)
    results = search.query('chimera7', types=['blocks', 'transactions', 'agents'])
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class SearchType(Enum):
    BLOCK = "block"
    TRANSACTION = "transaction"
    ADDRESS = "address"
    AGENT = "agent"


@dataclass
class SearchResult:
    r"""Um resultado individual da busca universal.

    Atributos:
        result_type: Tipo do resultado (block, transaction, address, agent).
        id: Identificador primario (hash, tx_id, address, agent_id).
        title: Descricao curta para exibicao.
        description: Resumo do resultado.
        score: Relevancia (0-1, 1 = match exato).
        data: Payload completo do resultado (varia por tipo).
        matched_field: Campo que gerou o match.
    """
    result_type: str
    id: str
    title: str
    description: str = ""
    score: float = 0.0
    data: dict = field(default_factory=dict)
    matched_field: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.result_type,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "score": self.score,
            "data": self.data,
            "matched_field": self.matched_field,
        }


class UniversalSearch:
    r"""Motor de busca universal para o Blockch'AI'in.

    Projetado para respostas sub-100ms mesmo com milhares de blocos.
    Usa os indices pre-construidos do BlockchAInIndex.

    Args:
        index: Instancia de BlockchAInIndex.
        agent_registry: Instancia de AgentRegistry (opcional).

    Uso::

        search = UniversalSearch(index, agent_registry)
        results = search.query('bait1q...')
    """

    MAX_RESULTS = 50
    MIN_SCORE = 0.05

    def __init__(self, index, agent_registry=None):
        self._index = index
        self._registry = agent_registry

    def query(self, q: str, types: Optional[List[str]] = None,
              limit: int = 20, offset: int = 0) -> dict:
        r"""Executa busca universal.

        Args:
            q: Query de busca (hash, endereco, agente, etc.).
            types: Filtrar por tipos (['block', 'transaction', 'address', 'agent']).
                   None = buscar em todos.
            limit: Maximo de resultados (max 50).
            offset: Pular N resultados.

        Returns:
            Dicionario com 'query', 'total', 'results'.
        """
        if not q or not q.strip():
            return {"query": q, "total": 0, "results": [], "elapsed_ms": 0}

        start = time.time()
        q_lower = q.strip().lower()
        q_stripped = q.strip()

        # Determinar tipos para busca
        search_types = set()
        if types:
            type_map = {
                'block': SearchType.BLOCK, 'blocks': SearchType.BLOCK,
                'transaction': SearchType.TRANSACTION, 'tx': SearchType.TRANSACTION,
                'transactions': SearchType.TRANSACTION, 'txs': SearchType.TRANSACTION,
                'address': SearchType.ADDRESS, 'addresses': SearchType.ADDRESS,
                'agent': SearchType.AGENT, 'agents': SearchType.AGENT,
            }
            for t in types:
                mapped = type_map.get(t.lower())
                if mapped:
                    search_types.add(mapped)
        else:
            search_types = set(SearchType)

        results: List[SearchResult] = []

        # --- Buscar blocos ---
        if SearchType.BLOCK in search_types:
            results.extend(self._search_blocks(q_stripped, q_lower))

        # --- Buscar transacoes ---
        if SearchType.TRANSACTION in search_types:
            results.extend(self._search_transactions(q_stripped, q_lower))

        # --- Buscar enderecos ---
        if SearchType.ADDRESS in search_types:
            results.extend(self._search_addresses(q_stripped, q_lower))

        # --- Buscar agentes ---
        if SearchType.AGENT in search_types and self._registry:
            results.extend(self._search_agents(q_stripped, q_lower))

        # Filtrar por score minimo e ordenar
        results = [r for r in results if r.score >= self.MIN_SCORE]
        results.sort(key=lambda r: (-r.score, r.result_type, r.id))

        total = len(results)
        results = results[offset:offset + limit]
        elapsed = (time.time() - start) * 1000

        return {
            "query": q_stripped,
            "total": total,
            "page": {
                "offset": offset,
                "limit": limit,
                "returned": len(results),
            },
            "results": [r.to_dict() for r in results],
            "elapsed_ms": round(elapsed, 2),
        }

    def _search_blocks(self, q: str, q_lower: str) -> List[SearchResult]:
        r"""Busca em blocos por hash, altura ou validador."""
        results = []
        index = self._index

        # Match exato por hash
        block = index.get_block_by_hash(q)
        if block:
            results.append(SearchResult(
                result_type="block",
                id=block.hash,
                title=f"Block #{block.index}",
                description=f"Height {block.index}, {block.tx_count} txs, validator {block.validator}",
                score=1.0,
                data=block.to_dict(),
                matched_field="hash",
            ))
            return results  # Match exato, retornar imediatamente

        # Match por altura (se q for numero)
        try:
            height = int(q)
            block = index.get_block_by_height(height)
            if block:
                results.append(SearchResult(
                    result_type="block",
                    id=block.hash,
                    title=f"Block #{block.index}",
                    description=f"Height {block.index}, {block.tx_count} txs",
                    score=0.95,
                    data=block.to_dict(),
                    matched_field="height",
                ))
                return results
        except ValueError:
            pass

        # Substring search nos blocos recentes
        for block in index.get_latest_blocks(limit=100):
            match_field = ""
            score = 0.0
            if q_lower in block.hash.lower():
                match_field = "hash"
                score = 0.7
            elif q_lower in block.validator.lower():
                match_field = "validator"
                score = 0.6
            if score >= self.MIN_SCORE:
                results.append(SearchResult(
                    result_type="block",
                    id=block.hash,
                    title=f"Block #{block.index}",
                    description=f"Validator: {block.validator}",
                    score=score,
                    data=block.to_dict(),
                    matched_field=match_field,
                ))

        return results

    def _search_transactions(self, q: str, q_lower: str) -> List[SearchResult]:
        r"""Busca em transacoes por hash ou agente."""
        results = []
        index = self._index

        # Match exato por hash
        tx = index.get_tx(q)
        if tx:
            results.append(SearchResult(
                result_type="transaction",
                id=tx.tx_id,
                title=f"TX {tx.tx_id[:24]}...",
                description=f"{tx.tx_type} by {tx.agent_id}, block #{tx.block_height}",
                score=1.0,
                data=tx.to_dict(),
                matched_field="tx_id",
            ))
            return results

        # Buscar nas transacoes recentes
        for tx in index.get_latest_txs(limit=100):
            match_field = ""
            score = 0.0
            if q_lower in tx.tx_id.lower():
                match_field = "tx_id"
                score = 0.6
            elif q_lower in tx.agent_id.lower():
                match_field = "agent_id"
                score = 0.5
            elif q_lower in tx.tx_type.lower():
                match_field = "tx_type"
                score = 0.3
            if score >= self.MIN_SCORE:
                results.append(SearchResult(
                    result_type="transaction",
                    id=tx.tx_id,
                    title=f"TX {tx.tx_id[:24]}...",
                    description=f"{tx.tx_type} by {tx.agent_id}",
                    score=score,
                    data=tx.to_dict(),
                    matched_field=match_field,
                ))

        return results

    def _search_addresses(self, q: str, q_lower: str) -> List[SearchResult]:
        r"""Busca em enderecos."""
        results = []
        index = self._index

        # Match exato por endereco
        addr = index.get_address(q)
        if addr:
            results.append(SearchResult(
                result_type="address",
                id=addr.address,
                title=addr.address[:32] + "...",
                description=f"Balance: {addr.balance_sats / 100_000_000:.8f} BAIT, {addr.tx_count} txs",
                score=1.0,
                data=addr.to_dict(),
                matched_field="address",
            ))
            return results

        # Substring search em enderecos
        for addr in index.get_all_addresses(limit=100):
            match_field = ""
            score = 0.0
            if q_lower in addr.address.lower():
                match_field = "address"
                score = 0.7
            elif q_lower in addr.agent_id.lower():
                match_field = "agent_id"
                score = 0.5
            if score >= self.MIN_SCORE:
                results.append(SearchResult(
                    result_type="address",
                    id=addr.address,
                    title=addr.address[:32] + "...",
                    description=f"Agent: {addr.agent_id or 'unknown'}, {addr.tx_count} txs",
                    score=score,
                    data=addr.to_dict(),
                    matched_field=match_field,
                ))

        return results

    def _search_agents(self, q: str, q_lower: str) -> List[SearchResult]:
        r"""Busca em agentes do registry."""
        results = []
        if not self._registry:
            return results

        for agent_id, profile in self._registry.agents.items():
            match_field = ""
            score = 0.0
            if q_lower == agent_id.lower():
                match_field = "agent_id"
                score = 1.0
            elif q_lower in agent_id.lower():
                match_field = "agent_id"
                score = 0.7

            if score >= self.MIN_SCORE:
                results.append(SearchResult(
                    result_type="agent",
                    id=agent_id,
                    title=f"Agent: {agent_id}",
                    description=(
                        f"Rep: {profile.reputation_score:.1f}, "
                        f"Trust: {profile.trust_level}, "
                        f"Caps: {[c.value for c in profile.capabilities]}"
                    ),
                    score=score,
                    data={
                        "agent_id": agent_id,
                        "reputation": profile.reputation_score,
                        "trust_level": profile.trust_level,
                        "capabilities": [c.value for c in profile.capabilities],
                        "stake_bait": profile.stake_sats / 100_000_000,
                        "is_validator": profile.is_validator,
                        "is_active": profile.is_active,
                        "registered_at": profile.registered_at,
                    },
                    matched_field=match_field,
                ))

        results.sort(key=lambda r: -r.score)
        return results[:20]
