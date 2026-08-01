r"""Mainnet Launcher - Inicializa todos os componentes da rede.

Orquestra o startup de:
- Blockchain com configuração mainnet
- P2P Node
- API REST
- Faucet
- ZkML Verifier"""
import asyncio
import logging
from baitcoin_mainnet.config import MainnetConfig
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
from baitcoin_core.network.p2p_real.node import P2PNode
from baitcoin_faucet.faucet import BAITFaucet
from baitcoin_token.erc20_like.bait_token import BAITToken

logger = logging.getLogger("baitcoin.mainnet")


class MainnetLauncher:
    r"""Lança a rede mainnet completa."""

    def __init__(self, config: MainnetConfig = None):
        self.config = config or MainnetConfig()
        self.blockchain: Blockchain = None
        self.token: BAITToken = None
        self.consensus: ZkMLConsensus = None
        self.zkml_verifier: ZkMLVerifier = None
        self.p2p_node: P2PNode = None
        self.faucet: BAITFaucet = None

    async def launch(self) -> None:
        r"""Inicializa todos os componentes."""
        logger.info(f"Launching {self.config.network_name}...")

        # 1. Blockchain
        self.blockchain = Blockchain()
        logger.info(f"Blockchain initialized at height {self.blockchain.height}")

        # 2. Token
        self.token = BAITToken()
        logger.info("Token BAIT initialized")

        # 3. Consensus
        self.consensus = ZkMLConsensus()
        logger.info("zkML-PoUW consensus engine ready")

        # 4. ZkML Verifier
        self.zkml_verifier = ZkMLVerifier()
        logger.info("ZkML verifier ready")

        # 5. Faucet
        self.faucet = BAITFaucet(
            token=self.token,
            amount_sats=int(self.config.faucet_amount_bait * 100_000_000),
            cooldown=self.config.faucet_cooldown_seconds,
            max_total=int(self.config.faucet_max_per_agent * 100_000_000),
        )
        logger.info(f"Faucet ready ({self.config.faucet_amount_bait} BAIT per claim)")

        # 6. P2P Node
        self.p2p_node = P2PNode(
            port=self.config.p2p_port,
            seeds=list(self.config.seed_nodes),
        )
        self.p2p_node.set_blockchain_hooks(
            get_block=lambda h: None,
            get_headers=lambda loc, stop: [],
            get_height=lambda: self.blockchain.height,
        )
        await self.p2p_node.start()
        logger.info(f"P2P node on port {self.config.p2p_port}")

        logger.info("=== MAINNET LAUNCHED ===")

    async def shutdown(self) -> None:
        r"""Desliga a rede."""
        if self.p2p_node:
            await self.p2p_node.stop()
        logger.info("Mainnet shutdown complete")

    def get_status(self) -> dict:
        return {
            "network": self.config.network_name,
            "blockchain_height": self.blockchain.height if self.blockchain else 0,
            "token": self.token.to_dict() if self.token else {},
            "zkml": self.zkml_verifier.get_stats() if self.zkml_verifier else {},
            "p2p": self.p2p_node.get_status() if self.p2p_node else {},
            "faucet": self.faucet.get_stats() if self.faucet else {},
        }
