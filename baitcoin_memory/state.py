r"""Persistent State — interface de alto nível para persistir o estado do ecossistema.

Envolve o :class:`MemoryStore` com métodos tipados para cada módulo
do ecossistema b'AI'tcoin:

    - **Blockchain**: blocos, UTXO, mempool
    - **Agentes**: perfis, eventos de reputação
    - **Staking**: posições, recompensas, metadados
    - **Marketplace**: serviços, contratações
    - **Oracle**: preços em cache
    - **Faucet**: histórico de reivindicações
    - **Lending**: empréstimos, colateral
    - **Vaults**: alocações, lucro/perda
    - **Obscura**: tarefas de scraping, sessões
    - **Config**: parâmetros de rede

Uso típico::

    from baitcoin_memory import PersistentState, MemoryStore

    store = MemoryStore("/dados/baitcoin")
    state = PersistentState(store)

    # Persistir estado do blockchain
    state.save_blockchain(chain_data)
    state.save_utxo_set(utxo_data)

    # Recuperar após reinicialização
    chain = state.load_blockchain()
    utxos = state.load_utxo_set()
"""

import time
from typing import Any, Dict, List, Optional

from .store import MemoryStore, MemoryNamespace


class PersistentState:
    r"""Gerenciador de estado persistente de alto nível.

    Fornece métodos tipados de salvamento/carregamento para cada
    componente do ecossistema. Todas as escritas são duráveis
    via WAL (write-ahead log).

    Args:
        store: Instância de :class:`MemoryStore`. Se None, uma nova
               instância é criada com o ``data_path`` fornecido.
        data_path: Caminho base para os dados (usado apenas se
                   ``store`` for None).
    """

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        data_path: str = "~/.baitcoin/memory",
    ) -> None:
        self.store: MemoryStore = store or MemoryStore(data_path)

    # ------------------------------------------------------------------
    # Blockchain
    # ------------------------------------------------------------------

    def save_blockchain(self, chain_data: Dict[str, Any]) -> None:
        r"""Persiste a cadeia de blocos completa.

        Args:
            chain_data: Dicionário representando o estado da cadeia.
        """
        self.store.put(MemoryNamespace.BLOCKCHAIN.value, "chain", chain_data)

    def load_blockchain(self) -> Optional[Dict[str, Any]]:
        r"""Carrega a cadeia de blocos persistida.

        Returns:
            Dicionário da cadeia ou None se não existir.
        """
        return self.store.get(MemoryNamespace.BLOCKCHAIN.value, "chain")

    def save_utxo_set(self, utxo_data: Dict[str, Any]) -> None:
        r"""Persiste o conjunto de UTXOs (saídas de transação não gastas).

        Args:
            utxo_data: Dicionário mapeando outpoint -> dados da saída.
        """
        self.store.put(MemoryNamespace.BLOCKCHAIN.value, "utxo_set", utxo_data)

    def load_utxo_set(self) -> Optional[Dict[str, Any]]:
        r"""Carrega o conjunto de UTXOs persistido.

        Returns:
            Dicionário de UTXOs ou None se não existir.
        """
        return self.store.get(MemoryNamespace.BLOCKCHAIN.value, "utxo_set")

    def save_mempool(self, mempool_data: List[Dict[str, Any]]) -> None:
        r"""Persiste o estado atual do mempool.

        Args:
            mempool_data: Lista de transações pendentes.
        """
        self.store.put(MemoryNamespace.BLOCKCHAIN.value, "mempool", mempool_data)

    def load_mempool(self) -> Optional[List[Dict[str, Any]]]:
        r"""Carrega o mempool persistido.

        Returns:
            Lista de transações pendentes ou None.
        """
        return self.store.get(MemoryNamespace.BLOCKCHAIN.value, "mempool")

    # ------------------------------------------------------------------
    # Agentes
    # ------------------------------------------------------------------

    def save_agent(self, agent_id: str, agent_data: Dict[str, Any]) -> None:
        r"""Persiste os dados de um agente individual.

        Args:
            agent_id: Identificador único do agente.
            agent_data: Perfil e dados do agente.
        """
        self.store.put(MemoryNamespace.AGENTS.value, agent_id, agent_data)

    def load_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        r"""Carrega os dados de um agente.

        Args:
            agent_id: Identificador único do agente.

        Returns:
            Dados do agente ou None se não encontrado.
        """
        return self.store.get(MemoryNamespace.AGENTS.value, agent_id)

    def load_all_agents(self) -> Dict[str, Dict[str, Any]]:
        r"""Carrega todos os agentes registrados.

        Returns:
            Dicionário mapeando agent_id -> dados do agente.
        """
        result = self.store.get_all(MemoryNamespace.AGENTS.value)
        # Garantir que valores sejam dicionários
        return {k: v for k, v in result.items() if isinstance(v, dict)}

    def save_all_agents(self, agents: Dict[str, Dict[str, Any]]) -> None:
        r"""Persiste todos os agentes em uma operação de lote.

        Args:
            agents: Dicionário mapeando agent_id -> dados do agente.
        """
        self.store.put_all(MemoryNamespace.AGENTS.value, agents)

    def delete_agent(self, agent_id: str) -> bool:
        r"""Remove um agente do armazenamento persistente.

        Args:
            agent_id: Identificador único do agente.

        Returns:
            True se o agente existia e foi removido.
        """
        return self.store.delete(MemoryNamespace.AGENTS.value, agent_id)

    # ------------------------------------------------------------------
    # Reputação
    # ------------------------------------------------------------------

    def save_reputation_event(self, event: Dict[str, Any]) -> None:
        r"""Adiciona um evento de reputação ao histórico.

        Os eventos são armazenados como uma lista crescente.

        Args:
            event: Dicionário com os dados do evento (timestamp,
                   tipo, agente, valor, etc.).
        """
        events: List[Dict[str, Any]] = self.store.get(
            MemoryNamespace.REPUTATION.value, "events", []
        )
        if not isinstance(events, list):
            events = []
        events.append(event)
        self.store.put(MemoryNamespace.REPUTATION.value, "events", events)

    def load_reputation_events(self) -> List[Dict[str, Any]]:
        r"""Carrega todo o histórico de eventos de reputação.

        Returns:
            Lista de eventos de reputação (vazia se não existir).
        """
        events = self.store.get(MemoryNamespace.REPUTATION.value, "events", [])
        if not isinstance(events, list):
            return []
        return events

    def save_reputation_events(self, events: List[Dict[str, Any]]) -> None:
        r"""Substitui todo o histórico de reputação de uma vez.

        Útil para restaurar um estado completo.

        Args:
            events: Lista completa de eventos de reputação.
        """
        self.store.put(MemoryNamespace.REPUTATION.value, "events", events)

    # ------------------------------------------------------------------
    # Staking
    # ------------------------------------------------------------------

    def save_staking_positions(self, positions: Dict[str, Any]) -> None:
        r"""Persiste todas as posições de staking.

        Args:
            positions: Dicionário mapeando identificador -> posição.
        """
        self.store.put(MemoryNamespace.STAKING.value, "positions", positions)

    def load_staking_positions(self) -> Optional[Dict[str, Any]]:
        r"""Carrega as posições de staking persistidas.

        Returns:
            Dicionário de posições ou None.
        """
        return self.store.get(MemoryNamespace.STAKING.value, "positions")

    def save_staking_meta(self, meta: Dict[str, Any]) -> None:
        r"""Persiste metadados do pool de staking (recompensas totais, contadores).

        Args:
            meta: Dicionário com metadados operacionais.
        """
        self.store.put(MemoryNamespace.STAKING.value, "meta", meta)

    def load_staking_meta(self) -> Optional[Dict[str, Any]]:
        r"""Carrega os metadados do pool de staking.

        Returns:
            Dicionário de metadados ou None.
        """
        return self.store.get(MemoryNamespace.STAKING.value, "meta")

    # ------------------------------------------------------------------
    # Marketplace
    # ------------------------------------------------------------------

    def save_marketplace(self, data: Dict[str, Any]) -> None:
        r"""Persiste o estado completo do marketplace.

        Args:
            data: Dicionário com listagens, contratações, etc.
        """
        self.store.put(MemoryNamespace.MARKETPLACE.value, "marketplace", data)

    def load_marketplace(self) -> Optional[Dict[str, Any]]:
        r"""Carrega o estado do marketplace.

        Returns:
            Dicionário do marketplace ou None.
        """
        return self.store.get(MemoryNamespace.MARKETPLACE.value, "marketplace")

    # ------------------------------------------------------------------
    # Oracle (preços)
    # ------------------------------------------------------------------

    def save_oracle_prices(self, prices: Dict[str, Any]) -> None:
        r"""Persiste o cache de preços do oráculo.

        Args:
            prices: Dicionário mapeando par -> preço.
        """
        self.store.put(MemoryNamespace.ORACLE.value, "prices", prices)

    def load_oracle_prices(self) -> Optional[Dict[str, Any]]:
        r"""Carrega o cache de preços persistido.

        Returns:
            Dicionário de preços ou None.
        """
        return self.store.get(MemoryNamespace.ORACLE.value, "prices")

    # ------------------------------------------------------------------
    # Faucet
    # ------------------------------------------------------------------

    def save_faucet_state(self, state_data: Dict[str, Any]) -> None:
        r"""Persiste o estado completo do faucet (reivindicações, limites).

        Args:
            state_data: Dicionário com o estado do faucet.
        """
        self.store.put(MemoryNamespace.FAUCET.value, "state", state_data)

    def load_faucet_state(self) -> Optional[Dict[str, Any]]:
        r"""Carrega o estado do faucet.

        Returns:
            Dicionário do faucet ou None.
        """
        return self.store.get(MemoryNamespace.FAUCET.value, "state")

    # ------------------------------------------------------------------
    # Lending
    # ------------------------------------------------------------------

    def save_lending_state(self, state_data: Dict[str, Any]) -> None:
        r"""Persiste o estado do módulo de empréstimos.

        Args:
            state_data: Dicionário com empréstimos ativos, colateral, etc.
        """
        self.store.put(MemoryNamespace.LENDING.value, "loans", state_data)

    def load_lending_state(self) -> Optional[Dict[str, Any]]:
        r"""Carrega o estado do módulo de empréstimos.

        Returns:
            Dicionário do lending ou None.
        """
        return self.store.get(MemoryNamespace.LENDING.value, "loans")

    # ------------------------------------------------------------------
    # Vaults
    # ------------------------------------------------------------------

    def save_vault(self, agent_id: str, vault_data: Dict[str, Any]) -> None:
        r"""Persiste os dados de um vault individual.

        Args:
            agent_id: Identificador do agente proprietário do vault.
            vault_data: Dados do vault (alocações, PnL, etc.).
        """
        self.store.put(MemoryNamespace.VAULTS.value, agent_id, vault_data)

    def load_vault(self, agent_id: str) -> Optional[Dict[str, Any]]:
        r"""Carrega os dados de um vault.

        Args:
            agent_id: Identificador do agente.

        Returns:
            Dados do vault ou None se não encontrado.
        """
        return self.store.get(MemoryNamespace.VAULTS.value, agent_id)

    def load_all_vaults(self) -> Dict[str, Dict[str, Any]]:
        r"""Carrega todos os vaults registrados.

        Returns:
            Dicionário mapeando agent_id -> dados do vault.
        """
        result = self.store.get_all(MemoryNamespace.VAULTS.value)
        return {k: v for k, v in result.items() if isinstance(v, dict)}

    def save_all_vaults(self, vaults: Dict[str, Dict[str, Any]]) -> None:
        r"""Persiste todos os vaults em uma operação de lote.

        Args:
            vaults: Dicionário mapeando agent_id -> dados do vault.
        """
        self.store.put_all(MemoryNamespace.VAULTS.value, vaults)

    # ------------------------------------------------------------------
    # Obscura
    # ------------------------------------------------------------------

    def save_obscura_tasks(self, tasks: Dict[str, Any]) -> None:
        r"""Persiste as tarefas do módulo Obscura.

        Args:
            tasks: Dicionário com tarefas de scraping, sessões, etc.
        """
        self.store.put(MemoryNamespace.OBSCURA.value, "tasks", tasks)

    def load_obscura_tasks(self) -> Optional[Dict[str, Any]]:
        r"""Carrega as tarefas do Obscura.

        Returns:
            Dicionário de tarefas ou None.
        """
        return self.store.get(MemoryNamespace.OBSCURA.value, "tasks")

    def save_obscura_sessions(self, sessions: Dict[str, Any]) -> None:
        r"""Persiste as sessões ativas do Obscura.

        Args:
            sessions: Dicionário mapeando session_id -> dados da sessão.
        """
        self.store.put(MemoryNamespace.OBSCURA.value, "sessions", sessions)

    def load_obscura_sessions(self) -> Optional[Dict[str, Any]]:
        r"""Carrega as sessões do Obscura.

        Returns:
            Dicionário de sessões ou None.
        """
        return self.store.get(MemoryNamespace.OBSCURA.value, "sessions")

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def save_config(self, config: Dict[str, Any]) -> None:
        r"""Persiste os parâmetros de configuração da rede.

        Args:
            config: Dicionário com parâmetros de rede.
        """
        self.store.put(MemoryNamespace.CONFIG.value, "network", config)

    def load_config(self) -> Optional[Dict[str, Any]]:
        r"""Carrega a configuração de rede.

        Returns:
            Dicionário de configuração ou None.
        """
        return self.store.get(MemoryNamespace.CONFIG.value, "network")

    # ------------------------------------------------------------------
    # Operações em lote
    # ------------------------------------------------------------------

    def save_ecosystem_snapshot(self, data: Dict[str, Any]) -> None:
        r"""Salva o estado completo do ecossistema em uma operação.

        Cada chave do dicionário ``data`` deve corresponder a um
        namespace válido. Valores de tipo dict são persistidos
        via ``put_all``; outros tipos via ``put`` com chave ``snapshot``.

        Exemplo::

            state.save_ecosystem_snapshot({
                "blockchain": {"chain": [...], "utxo_set": {...}},
                "agents": {"agent_1": {...}, "agent_2": {...}},
                "staking": {"positions": {...}},
            })

        Args:
            data: Dicionário mapeando namespace -> dados.
        """
        for namespace, value in data.items():
            if isinstance(value, dict):
                self.store.put_all(namespace, value)
            else:
                self.store.put(namespace, "snapshot", value)

    def load_ecosystem_snapshot(
        self, namespaces: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        r"""Carrega o estado completo do ecossistema.

        Args:
            namespaces: Lista de namespaces a carregar.
                        Se None, carrega todos os namespaces conhecidos.

        Returns:
            Dicionário mapeando namespace -> dados carregados.
        """
        result: Dict[str, Any] = {}
        target = namespaces or [ns.value for ns in MemoryNamespace]
        for ns in target:
            result[ns] = self.store.get_all(ns)
        return result

    def force_snapshot_all(self) -> None:
        r"""Força a criação de snapshots imediatos para todos os namespaces.

        Útil antes de encerrar o processo para garantir que todo
        o estado em memória seja persistido.
        """
        self.store.force_snapshot()

    def get_stats(self) -> Dict[str, Any]:
        r"""Retorna estatísticas operacionais do armazenamento.

        Returns:
            Dicionário com caminho, namespaces, cache, etc.
        """
        return self.store.get_stats()

    def compact_all(self) -> Dict[str, int]:
        r"""Compacta todos os namespaces (snapshot + limpeza de WAL).

        Returns:
            Dicionário mapeando namespace -> número de segmentos removidos.
        """
        result: Dict[str, int] = {}
        for ns in self.store.list_namespaces():
            result[ns] = self.store.compact(ns)
        return result
