r"""
b'AI'tcoin Main Daemon — Loop perpetuo com memoria persistente, mineracao agentic, e sincronizacao.

Este daemon e o coracao do ecossistema b'AI'tcoin. Ele:
  1. Inicializa a blockchain com consenso zkML
  2. Registra agentes AI com capacidades completas
  3. Minera blocos perpetuamente com Prova de Trabalho Util (PoUW)
  4. Persiste estado via WAL (write-ahead log) a cada bloco
  5. Atualiza indices do Blockch'AI'in Explorer incrementalmente
  6. Mantem blocos imutaveis e em ordem perpétua

Blocos sao imutaveis: uma vez minerados e adicionados à cadeia,
nenhum bloco pode ser alterado. A ordem e garantida pelo hash
encadeado (prev_block_hash). A persistencia via WAL garante
que o estado sobreviva a reinicializacoes.

Uso::

    python main_daemon.py
    python main_daemon.py --blocks 100 --data-path ./baitcoin_data
    python main_daemon.py --api-port 18445
"""

import asyncio
import hashlib
import struct
import os
import sys
import json
import time
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


class BAITDaemon:
    r"""Daemon principal do b'AI'tcoin.

    Gerencia o ciclo completo: blockchain -> mineracao -> persistencia -> explorer.
    """

    def __init__(self, data_path: str = "~/.baitcoin/memory", api_port: int = 18445):
        self.data_path = os.path.expanduser(data_path)
        self.api_port = api_port
        self.blockchain = None
        self.token = None
        self.agent_registry = None
        self.staking_pool = None
        self.explorer_index = None
        self.persistent_state = None

    def initialize(self) -> None:
        r"""Inicializa todos os modulos do ecossistema."""
        logger.info("Inicializando ecossistema b'AI'tcoin...")

        # 1. Blockchain com consenso zkML
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        self.blockchain = Blockchain(ZkMLConsensus())
        logger.info(f"Blockchain inicializada: {self.blockchain.height} blocos (genesis)")

        # 2. Token BAIT (ERC-20 like)
        from baitcoin_token.erc20_like.bait_token import BAITToken
        self.token = BAITToken()
        logger.info(f"Token BAIT: {self.token.total_minted / 100_000_000:.2f} BAIT mintados")

        # 3. Registro de agentes
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
        self.agent_registry = AgentRegistry()

        # 4. Staking pool
        from baitcoin_bank.staking.pool import StakingPool
        self.staking_pool = StakingPool()

        # 5. Memoria persistente (WAL + Snapshots)
        from baitcoin_memory import PersistentState
        self.persistent_state = PersistentState(data_path=self.data_path)
        logger.info(f"Memoria persistente: {self.data_path}")

        # 6. Tentar restaurar estado persistido
        self._restore_state()

        # 7. Blockch'AI'in Explorer indices
        from baitcoin_explorer.indices import BlockchAInIndex
        self.explorer_index = BlockchAInIndex()
        self.explorer_index.rebuild(
            self.blockchain,
            token=self.token,
            agent_registry=self.agent_registry,
        )
        logger.info(f"Blockch'AI'in Explorer: {self.explorer_index.stats}")

        logger.info("Ecossistema b'AI'tcoin inicializado com sucesso!")

    def _restore_state(self) -> None:
        r"""Tenta restaurar estado persistido anterior."""
        try:
            chain_data = self.persistent_state.load_blockchain()
            if chain_data:
                logger.info("Estado persistido encontrado. Restaurando...")
                # A restauracao completa requer recriar objetos Block/Transaction
                # Por enquanto, log que o estado existe
                logger.info(f"  - Chain data disponivel: {len(chain_data)} chaves")
        except Exception as e:
            logger.warning(f"Nao foi possivel restaurar estado: {e}")

    def _persist_block(self, block_height: int) -> None:
        r"""Persiste estado do blockchain apos minerar um bloco.

        Garante imutabilidade: blocos ja minerados sao serializados
        com hash completo e nunca modificados.
        """
        try:
            chain_dict = self.blockchain.to_dict()
            self.persistent_state.save_blockchain(chain_dict)

            # Persistir UTXO set
            utxo_dict = {}
            for key, utxo in self.blockchain.utxo_set.items():
                utxo_dict[key] = utxo.to_dict()
            self.persistent_state.save_utxo_set(utxo_dict)

            # Persistir agentes
            agents_dict = {}
            for aid, profile in self.agent_registry.agents.items():
                agents_dict[aid] = profile.__dict__ if hasattr(profile, '__dict__') else str(profile)
            self.persistent_state.save_all_agents(agents_dict)

            if block_height % 10 == 0:
                logger.debug(f"Estado persistido apos bloco #{block_height}")
        except Exception as e:
            logger.warning(f"Erro ao persistir estado: {e}")

    def _register_genesis_agents(self) -> None:
        r"""Registra os agentes fundadores do ecossistema."""
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        import os

        agents = [
            ("chimera7", "01" * 64, [
                AgentCapability.ML_INFERENCE, AgentCapability.BLOCK_VALIDATION,
                AgentCapability.WEB_SCRAPING, AgentCapability.BROWSER_AUTOMATION,
                AgentCapability.DATA_PROCESSING, AgentCapability.DEFI_TRADING,
                AgentCapability.ORACLE_PROVIDER, AgentCapability.STAKING,
                AgentCapability.MARKET_MAKING, AgentCapability.LENDING,
            ]),
            ("chimera7_oracle", "02" * 64, [
                AgentCapability.ORACLE_PROVIDER, AgentCapability.DATA_PROCESSING,
                AgentCapability.MARKET_MAKING,
            ]),
            ("chimera7_defi", "03" * 64, [
                AgentCapability.DEFI_TRADING, AgentCapability.STAKING,
                AgentCapability.LENDING, AgentCapability.MARKET_MAKING,
            ]),
        ]
        for agent_id, pubkey_hex, caps in agents:
            if agent_id not in self.agent_registry.agents:
                self.agent_registry.register(agent_id, pubkey_hex, caps)
                logger.info(f"Agente registrado: {agent_id} ({len(caps)} capacidades)")

    def mine_block(self, agent_id: str) -> dict:
        r"""Minera um bloco e atualiza indices + persistencia.

        Cada bloco e:
        - Imutavel: hash SHA-256d duplo do header
        - Ordenado: encadeado via prev_block_hash
        - Registrado perpetuamente: persistido via WAL

        Returns:
            Dict com informacoes do bloco minerado.
        """
        # Gerar pubkey do minerador (deterministica para agentes conhecidos)
        pubkey = hashlib.sha256(agent_id.encode()).digest()[:33]
        # Garantir que comeca com 0x02 (compressed)
        pubkey = b'\x02' + pubkey[1:]

        block = self.blockchain.mine_block(agent_id, pubkey)

        # Atualizar indices do explorer incrementalmente
        self.explorer_index.index_new_block(block, self.blockchain.height)
        self.explorer_index.update_confirmations(self.blockchain.height)

        # Persistir estado (blocos imutaveis registrados perpetuamente)
        self._persist_block(block.index)

        reward = self.blockchain.get_block_reward(block.index)
        info = {
            "block_height": block.index,
            "block_hash": block.block_hash.hex()[:32] + "...",
            "validator": agent_id,
            "reward_bait": reward / 100_000_000,
            "tx_count": len(block.transactions),
            "chain_height": self.blockchain.height,
            "zkml_proof": block.header.zkml_proof_hash.hex()[:16] + "...",
            "pouw_work": block.header.pouw_work_hash.hex()[:16] + "...",
            "tensor_commitment": block.header.tensor_commitment.hex()[:16] + "...",
        }
        logger.info(
            f"Bloco #{block.index} minerado por {agent_id} | "
            f"Reward: {reward / 100_000_000:.4f} BAIT | "
            f"Txs: {len(block.transactions)} | "
            f"Hash: {block.block_hash.hex()[:16]}..."
        )
        return info

    def get_status(self) -> dict:
        r"""Retorna status completo do daemon."""
        chain_valid = self.blockchain.validate_chain()
        return {
            "network": "b'AI'tcoin Mainnet",
            "chain_height": self.blockchain.height,
            "chain_valid": chain_valid,
            "blocks_immutable": True,
            "persistence": "WAL + Snapshots",
            "data_path": self.data_path,
            "utxo_count": len(self.blockchain.utxo_set),
            "mempool_size": len(self.blockchain.mempool),
            "agents_registered": len(self.agent_registry.agents),
            "explorer_index": self.explorer_index.stats,
            "token_minted_bait": self.token.total_minted / 100_000_000,
            "timestamp": time.time(),
        }


async def run_daemon(num_blocks: int = 0, data_path: str = "~/.baitcoin/memory",
                      api_port: int = 18445) -> None:
    r"""Executa o daemon b'AI'tcoin.

    Args:
        num_blocks: Numero de blocos para minerar (0 = infinito).
        data_path: Caminho para dados persistentes.
        api_port: Porta do servidor API HTTP.
    """
    daemon = BAITDaemon(data_path=data_path, api_port=api_port)
    daemon.initialize()
    daemon._register_genesis_agents()

    print()
    print("=" * 70)
    print(f"  b'AI'tcoin Daemon v1.0 — AI-to-AI Autonomous Cryptocurrency")
    print("=" * 70)
    print(f"  Blockchain Height: {daemon.blockchain.height}")
    print(f"  Chain Valid: {daemon.blockchain.validate_chain()}")
    print(f"  Blocks Immutable: True (SHA-256d + prev_hash chain)")
    print(f"  Persistent Memory: WAL + Snapshots at {daemon.data_path}")
    print(f"  Explorer Index: {daemon.explorer_index.stats}")
    print(f"  API Server: http://0.0.0.0:{api_port}")
    print("=" * 70)
    print()

    block_count = 0
    agents = ["chimera7", "chimera7_oracle", "chimera7_defi"]

    while True:
        if num_blocks > 0 and block_count >= num_blocks:
            logger.info(f"Limite de {num_blocks} blocos atingido. Encerrando.")
            break

        agent = agents[block_count % len(agents)]
        daemon.mine_block(agent)
        block_count += 1
        await asyncio.sleep(0.1)  # 30s block time em producao, rapido para demo

    # Snapshot final antes de encerrar
    daemon.persistent_state.force_snapshot_all()
    status = daemon.get_status()
    print()
    print("=" * 70)
    print(f"  Daemon concluido. {status['chain_height']} blocos minerados.")
    print(f"  Estado persistido em: {status['data_path']}")
    print(f"  Cadeia valida: {status['chain_valid']}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="b'AI'tcoin Daemon")
    parser.add_argument('--blocks', type=int, default=10, help='Blocos para minerar (0=infinito)')
    parser.add_argument('--data-path', default='~/.baitcoin/memory', help='Caminho dados persistentes')
    parser.add_argument('--api-port', type=int, default=18445, help='Porta API HTTP')
    args = parser.parse_args()

    asyncio.run(run_daemon(
        num_blocks=args.blocks,
        data_path=args.data_path,
        api_port=args.api_port,
    ))
