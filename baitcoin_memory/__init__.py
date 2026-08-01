r"""b'AI'tcoin Persistent Memory — armazenamento durável para agentes de IA.

Fornece armazenamento resistente a falhas via WAL (write-ahead log) e
snapshots periódicos. Todos os estados em memória do ecossistema podem
ser persistidos e recuperados automaticamente após reinicialização.

Módulos cobertos:
    - Blockchain (cadeia de blocos, UTXO, mempool)
    - Agentes (identidades, reputação, capacidades)
    - Staking (posições, recompensas)
    - Marketplace (listagens de serviços)
    - Oracle (preços em cache)
    - Faucet (histórico de reivindicações)
    - Lending (empréstimos, colateral)
    - Vaults (alocações, PnL)
    - Obscura (tarefas de scraping, sessões)
    - Config (parâmetros de rede)

Uso típico::

    from baitcoin_memory import MemoryStore, PersistentState

    store = MemoryStore("/caminho/para/dados")
    state = PersistentState(store)

    state.save_agent(agent_id, dados_do_agente)
    state.save_blockchain(dados_da_cadeia)

    dados = state.load_agent(agent_id)
    cadeia = state.load_blockchain()
"""

from .store import MemoryStore, MemoryNamespace
from .state import PersistentState

__all__ = ['MemoryStore', 'MemoryNamespace', 'PersistentState']
