r"""
Configuração Mainnet b'AI'tcoin.

Diferença entre mainnet e testnet:
- Dificuldade inicial mais alta
- Reward real de 50 BAIT
- Sementes de bootstrap oficiais
- Parâmetros de rede mais restritivos
"""
from dataclasses import dataclass


@dataclass
class MainnetConfig:
    r"""Configuração da rede principal."""
    # Network
    network_name: str = "baitcoin-mainnet"
    p2p_port: int = 18444
    api_port: int = 18445
    rpc_port: int = 18446

    # Consensus
    initial_target: str = "0x0000ffff00000000000000000000000000000000000000000000000000000000"
    block_time_target: int = 30
    difficulty_adjustment_interval: int = 2016

    # Token
    max_supply_bait: int = 21_000_000
    initial_reward_bait: float = 50.0
    halving_interval: int = 210_000

    # Faucet
    faucet_amount_bait: float = 10.0
    faucet_cooldown_seconds: int = 86400
    faucet_max_per_agent: float = 100.0

    # P2P
    max_peers: int = 50
    max_inbound: int = 30
    max_outbound: int = 10

    # Bootstrap seeds
    seed_nodes: tuple = (
        ("seed1.baitcoin.network", 18444),
        ("seed2.baitcoin.network", 18444),
        ("seed3.baitcoin.network", 18444),
    )

    # Limits
    max_txs_per_block: int = 1000
    max_block_size_bytes: int = 1_000_000
    min_fee_sats: int = 100
    mempool_max_size: int = 50_000

    def is_mainnet(self) -> bool:
        return "mainnet" in self.network_name

    def to_dict(self) -> dict:
        return {
            "network_name": self.network_name,
            "p2p_port": self.p2p_port,
            "api_port": self.api_port,
            "rpc_port": self.rpc_port,
            "max_supply_bait": self.max_supply_bait,
            "initial_reward_bait": self.initial_reward_bait,
            "halving_interval": self.halving_interval,
            "faucet_amount_bait": self.faucet_amount_bait,
            "seed_nodes": self.seed_nodes,
            "max_peers": self.max_peers,
        }
