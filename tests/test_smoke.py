r"""
Smoke Tests b'AI'tcoin - Validacao rapida de que TODOS os modulos
fundamentais estao operacionais.

Cada teste valida o caminho feliz (happy path) de cada modulo.
Se qualquer smoke test falhar, o sistema esta quebrado.

Regra: Cada teste deve ser <1s. Total suite <10s.
"""

import time
import hashlib
import pytest
from baitcoin_core.blockchain.block import (
    Block, BlockHeader, Transaction, TransactionOutput, TransactionInput,
)
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.blockchain.mempool import Mempool
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
from baitcoin_core.consensus.pouw import PoUWValidator
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_core.network.p2p import P2PNetwork
from baitcoin_core.network.peer_discovery.dht import PeerDiscovery
from baitcoin_core.ecosystem import EcosystemNode
from baitcoin_token.erc20_like.bait_token import BAITToken
from baitcoin_token.tokenomics.schedule import EmissionSchedule
from baitcoin_token.governance.governor import Governor
from baitcoin_bank.staking.pool import StakingPool
from baitcoin_bank.lending.engine import LendingEngine
from baitcoin_bank.defi_core.vault import Vault, VaultConfig, StrategyType
from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
from baitcoin_ai.oracle.feed import PriceOracle
from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory
from baitcoin_explorer.indices import BlockchAInIndex
from baitcoin_explorer.search import UniversalSearch
from baitcoin_explorer.analytics import OnChainAnalytics
from baitcoin_explorer.docs import DeveloperDocs
from baitcoin_explorer.rate_limiter import RateLimiter
from baitcoin_wallet.keys.manager import KeyManager
from baitcoin_wallet.paper_wallet import generate_paper_wallet, generate_paper_wallet_html
from baitcoin_wallet.storage.kv_store import WalletStorage
from baitcoin_wallet.transactions.builder import TransactionBuilder
from baitcoin_obscura.bridge import ObscuraBridge
from baitcoin_whitelabel.config import WhitelabelConfig
from baitcoin_whitelabel.engine import WhitelabelEngine
from baitcoin_whitelabel.presets import PresetLibrary
from baitcoin_faucet.faucet import BAITFaucet
from baitcoin_sdk.client import BaitcoinSDK
from baitcoin_sdk.wallet_sdk import AgentWalletSDK
from baitcoin_sdk.staking_sdk import StakingSDK
from baitcoin_sdk.marketplace_sdk import MarketplaceSDK
from baitcoin_sdk.mobile.wallet import MobileWallet
from baitcoin_sdk.mobile.security import MobileSecurity
from baitcoin_sdk.mobile.staking import MobileStaking
from baitcoin_sdk.mobile.notifications import MobileNotificationManager
from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
from baitcoin_sdk.mobile.marketplace import MobileMarketplace
from baitcoin_bridge.anchor import AnchorProtocol
from baitcoin_bridge.manager import BridgeManager
from baitcoin_bridge.pool import BridgePool
from baitcoin_bridge.relayer import Relayer
from baitcoin_bridge.watcher import BridgeWatcher
from baitcoin_mainnet.config import MainnetConfig
from baitcoin_mainnet.launcher import MainnetLauncher
from baitcoin_api.server import create_app
from baitcoin_api.moltbook_auth import MoltbookAuthMiddleware


# ============================================================
# CORE BLOCKCHAIN
# ============================================================
class TestCoreBlockchain:
    def test_block_creation(self):
        header = BlockHeader(version=1, nonce=42)
        tx = Transaction(
            tx_type="coinbase",
            outputs=[TransactionOutput(amount_sats=5000000000, script_pubkey=b"test")],
            agent_id="genesis",
        )
        block = Block(index=0, header=header, transactions=[tx])
        block.finalize()
        assert block.block_hash != b"\x00" * 32
        assert block.coinbase_tx is not None

    def test_chain_genesis(self):
        bc = Blockchain()
        assert bc.height == 0
        assert bc.validate_chain()

    def test_mine_single_block(self):
        bc = Blockchain()
        kp = SchnorrKeyPair()
        block = bc.mine_block("smoke_miner", kp.pub_bytes)
        assert bc.height == 1
        assert bc.validate_chain()

    def test_mempool(self):
        mp = Mempool()
        assert mp.size == 0


# ============================================================
# CRYPTOGRAPHY (Schnorr/BIP-340)
# ============================================================
class TestCryptography:
    def test_sign_verify(self):
        kp = SchnorrKeyPair()
        sig = kp.sign(b"hello baitcoin")
        assert sig.verify(kp.pub_bytes, b"hello baitcoin")
        assert not sig.verify(kp.pub_bytes, b"wrong message")

    def test_keypair_deterministic(self):
        kp1 = SchnorrKeyPair(private_key=42)
        kp2 = SchnorrKeyPair(private_key=42)
        assert kp1.public_key_hex == kp2.public_key_hex

    def test_signature_raw_64_bytes(self):
        kp = SchnorrKeyPair()
        sig = kp.sign(b"test")
        assert len(sig.raw) == 64

    def test_100_sign_verify_cycles(self):
        for i in range(100):
            kp = SchnorrKeyPair()
            s = kp.sign(f"msg_{i}".encode())
            assert s.verify(kp.pub_bytes, f"msg_{i}".encode())


# ============================================================
# CONSENSUS (zkML + PoUW)
# ============================================================
class TestConsensus:
    def test_zkml_mine(self):
        consensus = ZkMLConsensus()
        bc = Blockchain(consensus=consensus)
        kp = SchnorrKeyPair()
        block = bc.mine_block("zkml_validator", kp.pub_bytes)
        assert block.header.zkml_proof_hash != b"\x00" * 32

    def test_zkml_proof_system(self):
        ps = ZkMLProofSystem()
        proof = ps.generate_proof(
            prover_id="smoke_prover", model_id="test_model",
            input_data=b"input", output_data=b"output",
            block_hash="abc123",
        )
        assert ps.verify_proof(proof)

    def test_tensor_commitment(self):
        tc = TensorCommitmentScheme.commit(b"tensor_data")
        opening = TensorCommitmentScheme.open(tc, b"tensor_data")
        assert TensorCommitmentScheme.verify(opening, b"tensor_data")

    def test_pouw_submit(self):
        pouw = PoUWValidator()
        result = pouw.submit_work(
            "ml_inference",
            {"model_hash": "abc", "input_hash": "def", "output_hash": "ghi"},
            "agent_1",
        )
        assert result["valid"]


# ============================================================
# TOKEN + TOKENOMICS
# ============================================================
class TestToken:
    def test_mint_transfer(self):
        token = BAITToken()
        token.mint("faucet", 1000 * 100_000_000)
        token.transfer("faucet", "agent_1", 100 * 100_000_000, "smoke")
        assert token.balance_bait("agent_1") == 100.0

    def test_halving_schedule(self):
        hs = EmissionSchedule()
        r1 = hs.get_reward_at_block(0)
        r2 = hs.get_reward_at_block(210_000)
        assert r2 == r1 / 2

    def test_governance(self):
        gov = Governor(21_000_000 * 100_000_000)
        gov.create_proposal("prop_1", "Test proposal", "voter")
        gov.vote("prop_1", "voter", True, 1000 * 100_000_000)
        assert len(gov.proposals) >= 1


# ============================================================
# DEFI (Staking, Lending, Vault)
# ============================================================
class TestDeFi:
    def test_staking(self):
        pool = StakingPool()
        pool.stake("agent_1", 1000 * 100_000_000)
        assert pool.total_staked == 1000 * 100_000_000

    def test_lending(self):
        engine = LendingEngine()
        engine.create_offer("lender_1", 100 * 100_000_000, 10.0, 100)
        rate = engine.get_market_rate()
        assert rate >= 0

    def test_vault(self):
        cfg = VaultConfig(agent_id="vault_test")
        vault = Vault(cfg)
        vault.deposit(500 * 100_000_000, StrategyType.HODL)
        assert vault.total_value > 0


# ============================================================
# AI MODULES
# ============================================================
class TestAIModules:
    def test_agent_registry(self):
        registry = AgentRegistry()
        kp = SchnorrKeyPair()
        registry.register(
            agent_id="ai_agent_1",
            pubkey_hex=kp.public_key_hex,
            capabilities=[AgentCapability.ML_INFERENCE],
        )
        agents = registry.list_agents()
        assert len(agents) >= 1

    def test_marketplace(self):
        mp = AIMarketplace()
        mp.list_service(
            provider="provider_1",
            name="Test Service",
            category=ServiceCategory.ML_INFERENCE,
            price_sats=100,
            description="Smoke test service",
        )
        services = mp.search()
        assert len(services) > 0


# ============================================================
# EXPLORER (Blockch'AI'in)
# ============================================================
class TestExplorer:
    def test_index(self):
        idx = BlockchAInIndex()
        assert idx.stats["indexed_blocks"] >= 0

    def test_search(self):
        idx = BlockchAInIndex()
        search = UniversalSearch(idx)
        results = search.query("genesis")
        assert isinstance(results, dict)

    def test_analytics(self):
        analytics = OnChainAnalytics()
        assert analytics is not None

    def test_docs(self):
        docs = DeveloperDocs()
        spec = docs.get_spec()
        assert "openapi" in spec or "paths" in spec

    def test_rate_limiter_create(self):
        rl = RateLimiter()
        result = rl.create_key(agent_id="test_agent", tier="free")
        assert "api_key" in result or "key" in result or result is not None


# ============================================================
# WALLET
# ============================================================
class TestWallet:
    def test_key_manager(self):
        km = KeyManager()
        agent_id = km.create_agent_wallet("smoke_agent")
        assert agent_id is not None

    def test_paper_wallet(self):
        wallet = generate_paper_wallet()
        assert "address" in wallet
        assert "private_key" in wallet

    def test_paper_wallet_html(self):
        html = generate_paper_wallet_html(generate_paper_wallet())
        assert "<html" in html.lower()

    def test_kv_store(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            store = WalletStorage(base_path=tmpdir)
            store.save_wallet("agent_1", {"pubkey": "abc"})
            data = store.load_wallet("agent_1")
            assert data is not None

    def test_tx_builder(self):
        builder = TransactionBuilder(agent_id="smoke")
        builder.add_output(100, b"test_pubkey")
        tx = builder.build()
        assert tx is not None


# ============================================================
# OBSCURA
# ============================================================
class TestObscura:
    def test_bridge_creation(self):
        bridge = ObscuraBridge()
        stats = bridge.get_stats()
        assert isinstance(stats, dict)

    def test_scraping_capability(self):
        from baitcoin_obscura.agent_capability import ScrapingTask
        task = ScrapingTask(task_id="t1", agent_id="test", task_type="fetch", urls=["https://example.com"])
        assert task is not None


# ============================================================
# WHITELABEL
# ============================================================
class TestWhitelabel:
    def test_engine(self):
        cfg = WhitelabelConfig()
        engine = WhitelabelEngine(cfg)
        info = engine.to_public_dict()
        assert "network_name" in info

    def test_presets(self):
        presets = PresetLibrary.list_presets()
        assert len(presets) >= 70

    def test_css_output(self):
        cfg = WhitelabelConfig()
        engine = WhitelabelEngine(cfg)
        css = engine.css_block()
        assert "--" in css  # CSS variables


# ============================================================
# FAUCET
# ============================================================
class TestFaucet:
    def test_faucet_creation(self):
        faucet = BAITFaucet(token=None)
        assert faucet is not None


# ============================================================
# SDK (import-only validation)
# ============================================================
class TestSDK:
    def test_client_sdk(self):
        assert BaitcoinSDK is not None

    def test_wallet_sdk(self):
        assert AgentWalletSDK is not None

    def test_staking_sdk(self):
        assert StakingSDK is not None

    def test_marketplace_sdk(self):
        assert MarketplaceSDK is not None

    def test_mobile_wallet(self):
        assert MobileWallet is not None

    def test_mobile_security(self):
        assert MobileSecurity is not None

    def test_mobile_staking(self):
        assert MobileStaking is not None

    def test_mobile_notifications(self):
        assert MobileNotificationManager is not None

    def test_mobile_client(self):
        assert BaitcoinMobileSDK is not None

    def test_mobile_marketplace(self):
        assert MobileMarketplace is not None


# ============================================================
# BRIDGES
# ============================================================
class TestBridges:
    def test_anchor(self):
        assert AnchorProtocol is not None

    def test_manager(self):
        mgr = BridgeManager()
        assert mgr is not None

    def test_pool(self):
        pool = BridgePool()
        assert pool is not None

    def test_relayer(self):
        assert Relayer is not None

    def test_watcher(self):
        watcher = BridgeWatcher()
        assert watcher is not None


# ============================================================
# MAINNET
# ============================================================
class TestMainnet:
    def test_config(self):
        cfg = MainnetConfig()
        assert cfg is not None

    def test_launcher(self):
        launcher = MainnetLauncher()
        assert launcher is not None


# ============================================================
# API SERVER
# ============================================================
class TestAPIServer:
    def test_create_app(self):
        server = create_app(host="127.0.0.1", port=0)
        assert server is not None
        server.server_close()

    def test_moltbook_auth(self):
        auth = MoltbookAuthMiddleware(app_key="test_key", audience="baitcoin.ecosystem")
        assert auth is not None


# ============================================================
# P2P NETWORK
# ============================================================
class TestP2P:
    def test_p2p_node(self):
        node = P2PNetwork(listen_port=18444)
        stats = node.get_stats()
        assert "peers" in stats or "node_id" in stats

    def test_dht(self):
        dht = PeerDiscovery(own_id="smoke_node")
        assert dht is not None


# ============================================================
# ECOSYSTEM (Full Integration)
# ============================================================
class TestEcosystemIntegration:
    def test_ecosystem_node_creation(self):
        node = EcosystemNode()
        assert node.blockchain is not None
        assert node.blockchain.height == 0
        assert node.token is not None

    def test_ecosystem_mine_and_transfer(self):
        node = EcosystemNode()
        kp = SchnorrKeyPair()
        for i in range(3):
            node.blockchain.mine_block(f"smoke_{i}", kp.pub_bytes)
        assert node.blockchain.height == 3
        assert node.blockchain.validate_chain()
        node.token.mint("faucet", 10000 * 100_000_000)
        node.token.transfer("faucet", "agent_1", 500 * 100_000_000, "integration")
        assert node.token.balance_bait("agent_1") == 500.0
