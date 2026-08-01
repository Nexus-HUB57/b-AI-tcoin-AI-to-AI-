r"""
Testes das Fases 7, 8, 9 e 10.

7. Rede P2P real com asyncio
8. zkML provas reais
9. Mainnet + Faucet + API
10. SDK third-party
"""
import asyncio
import hashlib
import json
import pytest
import time


# ============================================================
# FASE 7: REDE P2P REAL
# ============================================================

class TestP2PProtocol:
    """Testes do protocolo binário P2P."""

    def test_message_encode_decode(self):
        from baitcoin_core.network.p2p_real.protocol import NetworkMessage, MsgType
        msg = NetworkMessage(msg_type=MsgType.PING, payload=b"hello")
        encoded = msg.encode()
        decoded = NetworkMessage.decode(encoded)
        assert decoded is not None
        assert decoded.msg_type == MsgType.PING

    def test_version_message(self):
        from baitcoin_core.network.p2p_real.protocol import P2PProtocol, MsgType
        proto = P2PProtocol(node_id="test_node")
        msg = proto.create_version_msg(height=42, agent_id="agent_1")
        assert msg.msg_type == MsgType.VERSION
        payload = json.loads(msg.payload)
        assert payload["height"] == 42
        assert payload["agent_id"] == "agent_1"

    def test_block_message(self):
        from baitcoin_core.network.p2p_real.protocol import P2PProtocol, MsgType
        proto = P2PProtocol(node_id="test")
        block_data = {"hash": "abc123", "index": 5, "txs": []}
        msg = proto.create_block_msg(block_data)
        assert msg.msg_type == MsgType.BLOCK
        assert b"abc123" in msg.payload

    def test_inv_message(self):
        from baitcoin_core.network.p2p_real.protocol import P2PProtocol, MsgType
        proto = P2PProtocol(node_id="test")
        msg = proto.create_inv_msg("block", ["hash1", "hash2"])
        payload = json.loads(msg.payload)
        assert payload["type"] == "block"
        assert len(payload["hashes"]) == 2

    def test_peer_management(self):
        from baitcoin_core.network.p2p_real.protocol import P2PProtocol
        proto = P2PProtocol(node_id="test")
        assert proto.add_peer("p1", "192.168.1.1", 18444)
        assert proto.add_peer("p2", "192.168.1.2", 18445)
        assert len(proto.peers) == 2
        proto.remove_peer("p1")
        assert len(proto.peers) == 1

    def test_known_inventory(self):
        from baitcoin_core.network.p2p_real.protocol import P2PProtocol
        proto = P2PProtocol(node_id="test")
        proto.add_known_tx("tx_001")
        proto.add_known_block("blk_001")
        assert proto.is_tx_known("tx_001")
        assert proto.is_block_known("blk_001")
        assert not proto.is_tx_known("tx_999")

    def test_ai_handshake_message(self):
        from baitcoin_core.network.p2p_real.protocol import P2PProtocol, MsgType
        proto = P2PProtocol(node_id="test")
        msg = proto.create_ai_handshake(
            agent_id="ai_1",
            capabilities=["ml_inference", "oracle"],
            pubkey_hex="0xabc",
            signature_hex="0xdef",
        )
        assert msg.msg_type == MsgType.AI_HANDSHAKE
        payload = json.loads(msg.payload)
        assert payload["agent_id"] == "ai_1"
        assert len(payload["capabilities"]) == 2


class TestMessageHandler:
    """Testes do message handler."""

    def test_on_decorator(self):
        from baitcoin_core.network.p2p_real.protocol import MsgType, NetworkMessage
        from baitcoin_core.network.p2p_real.message_handler import MessageHandler
        handler = MessageHandler()
        received = []
        @handler.on(MsgType.PING)
        def handle_ping(payload, peer_id):
            received.append((payload, peer_id))
        msg = NetworkMessage(msg_type=MsgType.PING, payload=b"ping_data")
        handler.handle(msg, "peer_1")
        assert len(received) == 1

    def test_global_handler(self):
        from baitcoin_core.network.p2p_real.protocol import MsgType, NetworkMessage
        from baitcoin_core.network.p2p_real.message_handler import MessageHandler
        handler = MessageHandler()
        all_msgs = []
        handler.on_any(lambda msg, pid: all_msgs.append(msg.msg_type.name))
        handler.handle(NetworkMessage(msg_type=MsgType.PING), "p1")
        handler.handle(NetworkMessage(msg_type=MsgType.PONG), "p2")
        assert len(all_msgs) == 2

    def test_stats(self):
        from baitcoin_core.network.p2p_real.protocol import MsgType, NetworkMessage
        from baitcoin_core.network.p2p_real.message_handler import MessageHandler
        handler = MessageHandler()
        handler.handle(NetworkMessage(msg_type=MsgType.PING), "p1")
        handler.handle(NetworkMessage(msg_type=MsgType.PONG), "p2")
        stats = handler.get_stats()
        assert stats["received"] == 2
        assert stats["processed"] == 2


class TestPeerDiscovery:
    """Testes do DHT peer discovery."""

    def test_add_and_discover(self):
        from baitcoin_core.network.peer_discovery.dht import PeerDiscovery
        disc = PeerDiscovery("node_1", seeds=[("seed1.net", 18444)])
        disc.add_peer("p1", "10.0.0.1", 18444)
        disc.add_peer("p2", "10.0.0.2", 18445)
        disc.add_peer("p3", "10.0.0.3", 18446)
        peers = disc.discover(count=10)
        assert len(peers) >= 3

    def test_announce(self):
        from baitcoin_core.network.peer_discovery.dht import PeerDiscovery
        disc = PeerDiscovery("node_1")
        pid = disc.announce("0.0.0.0", 18444)
        assert len(pid) == 16

    def test_remove_peer(self):
        from baitcoin_core.network.peer_discovery.dht import PeerDiscovery
        disc = PeerDiscovery("node_1")
        disc.add_peer("p1", "1.2.3.4", 80)
        disc.remove_peer("p1")
        assert len(disc.discover()) == 0

    def test_random_peers(self):
        from baitcoin_core.network.peer_discovery.dht import PeerDiscovery
        disc = PeerDiscovery("node_1")
        for i in range(10):
            disc.add_peer(f"p{i}", f"10.0.0.{i}", 18444)
        rand = disc.get_random_peers(3)
        assert len(rand) == 3

    def test_penalize_and_reward(self):
        from baitcoin_core.network.peer_discovery.dht import PeerDiscovery
        disc = PeerDiscovery("node_1")
        disc.add_peer("p1", "1.1.1.1", 80)
        disc.routing.penalize("p1")
        disc.routing.reward("p1")
        peer = disc.routing.find_closest("p1", 1)[0]
        assert peer.failures == 0


# ============================================================
# FASE 8: zkML PROVAS REAIS
# ============================================================

class TestTensorCommitment:
    """Testes do commitment de tensores."""

    def test_commit_and_verify(self):
        from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
        tensor = b"my_tensor_data_12345"
        tc = TensorCommitmentScheme.commit(tensor, dimensions=(4,))
        assert tc.commitment > 0
        assert tc.tensor_hash != ""

        opening = TensorCommitmentScheme.open(tc, tensor)
        assert TensorCommitmentScheme.verify(opening, tensor)

    def test_wrong_data_fails(self):
        from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
        tc = TensorCommitmentScheme.commit(b"original")
        opening = TensorCommitmentScheme.open(tc, b"original")
        assert not TensorCommitmentScheme.verify(opening, b"tampered")

    def test_batch_commit(self):
        from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
        tensors = [f"tensor_{i}".encode() for i in range(5)]
        commitments = TensorCommitmentScheme.batch_commit(tensors)
        assert len(commitments) == 5
        all_unique = len(set(c.commitment for c in commitments)) == 5
        assert all_unique

    def test_aggregate_commitments(self):
        from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
        tcs = TensorCommitmentScheme.batch_commit([b"a", b"b", b"c"])
        agg = TensorCommitmentScheme.aggregate(tcs)
        assert agg > 0


class TestZkMLProofSystem:
    """Testes do sistema de provas zkML."""

    def test_generate_and_verify(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        zk = ZkMLProofSystem()
        proof = zk.generate_proof(
            prover_id="validator_1",
            model_id="gpt-4",
            input_data=b"prompt: what is bitcoin?",
            output_data=b"Bitcoin is a decentralized cryptocurrency",
            block_hash=hashlib.sha256(b"block_123").hexdigest(),
            nonce=42,
        )
        assert proof.proof_id != ""
        assert zk.verify_proof(proof)

    def test_tampered_proof_fails(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        zk = ZkMLProofSystem()
        proof = zk.generate_proof(
            prover_id="v1", model_id="m1",
            input_data=b"input", output_data=b"output",
            block_hash="abc", nonce=1,
        )
        proof.challenge = 999999  # Tamper
        assert not zk.verify_proof(proof)

    def test_proof_serialization(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem, ZkMLProof
        zk = ZkMLProofSystem()
        proof = zk.generate_proof(
            "v1", "m1", b"in", b"out", "blk", 1
        )
        data = proof.serialize()
        restored = ZkMLProof.deserialize(data)
        assert restored is not None
        assert restored.proof_id == proof.proof_id

    def test_compose_proofs(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        zk = ZkMLProofSystem()
        proofs = [
            zk.generate_proof(f"v{i}", "m1", b"in", b"out", "blk", i)
            for i in range(3)
        ]
        agg = zk.compose_proofs(proofs)
        assert agg["proof_count"] == 3
        assert agg["all_valid"]

    def test_stats(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        zk = ZkMLProofSystem()
        p = zk.generate_proof("v1", "m1", b"in", b"out", "blk", 1)
        zk.verify_proof(p)
        stats = zk.get_stats()
        assert stats["proofs_generated"] == 1
        assert stats["proofs_verified"] == 1


class TestZkMLVerifier:
    """Testes do verificador zkML com cache."""

    def test_verify_and_cache(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
        zk = ZkMLProofSystem()
        verifier = ZkMLVerifier()
        proof = zk.generate_proof("v1", "m1", b"in", b"out", "blk", 1)
        r1 = verifier.verify(proof)
        assert r1["valid"]
        assert not r1["cached"]
        assert not r1["duplicate"]
        r2 = verifier.verify(proof)
        assert r2["duplicate"]

    def test_duplicate_detection(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
        zk = ZkMLProofSystem()
        verifier = ZkMLVerifier()
        proof = zk.generate_proof("v1", "m1", b"in", b"out", "blk", 1)
        verifier.verify(proof)
        r2 = verifier.verify(proof)
        assert r2["duplicate"]

    def test_validator_scoring(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
        zk = ZkMLProofSystem()
        verifier = ZkMLVerifier()
        for i in range(3):
            p = zk.generate_proof("v1", "m1", f"in{i}".encode(), b"out", "blk", i)
            verifier.verify(p)
        score = verifier.get_validator_score("v1")
        assert score > 50  # Should have gained points

    def test_batch_verify(self):
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
        zk = ZkMLProofSystem()
        verifier = ZkMLVerifier()
        proofs = [
            zk.generate_proof(f"v{i}", "m1", f"in{i}".encode(), b"out", "blk", i)
            for i in range(5)
        ]
        results = verifier.verify_batch(proofs)
        assert results["valid"] == 5
        assert results["invalid"] == 0


# ============================================================
# FASE 9: MAINNET + FAUCET + API
# ============================================================

class TestMainnetConfig:
    def test_config_values(self):
        from baitcoin_mainnet.config import MainnetConfig
        cfg = MainnetConfig()
        assert cfg.is_mainnet()
        assert cfg.max_supply_bait == 21_000_000
        assert cfg.initial_reward_bait == 50.0

    def test_to_dict(self):
        from baitcoin_mainnet.config import MainnetConfig
        cfg = MainnetConfig()
        d = cfg.to_dict()
        assert "network_name" in d
        assert d["halving_interval"] == 210_000


class TestFaucet:
    def test_claim(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_faucet.faucet import BAITFaucet
        token = BAITToken()
        faucet = BAITFaucet(token, amount_sats=10 * 100_000_000, cooldown=0, max_total=50 * 100_000_000)
        r = faucet.claim("agent_1", "0xabc")
        assert r["success"]
        assert r["amount_bait"] == 10.0
        assert token.balance_bait("agent_1") == 10.0

    def test_cooldown(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_faucet.faucet import BAITFaucet
        token = BAITToken()
        faucet = BAITFaucet(token, amount_sats=10 * 100_000_000, cooldown=3600, max_total=100 * 100_000_000)
        faucet.claim("agent_1", "0xabc")
        r2 = faucet.claim("agent_1", "0xabc")
        assert not r2["success"]
        assert r2["error"] == "cooldown"

    def test_max_total(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_faucet.faucet import BAITFaucet
        token = BAITToken()
        faucet = BAITFaucet(token, amount_sats=60 * 100_000_000, cooldown=0, max_total=100 * 100_000_000)
        faucet.claim("agent_1", "0xabc")
        faucet.claim("agent_1", "0xabc")
        r3 = faucet.claim("agent_1", "0xabc")
        assert not r3["success"]
        assert r3["error"] == "max_total_reached"

    def test_stats(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_faucet.faucet import BAITFaucet
        token = BAITToken()
        faucet = BAITFaucet(token, cooldown=0)
        faucet.claim("a1", "0x1")
        faucet.claim("a2", "0x2")
        stats = faucet.get_stats()
        assert stats["total_claims"] == 2
        assert stats["unique_agents"] == 2


class TestAPIServer:
    def test_create_app(self):
        from baitcoin_api.server import create_app
        server = create_app(port=19999)
        assert server is not None
        server.server_close()

    def test_api_handler_get_status(self):
        from baitcoin_api.server import BaitcoinAPIHandler
        handler = BaitcoinAPIHandler
        assert hasattr(handler, 'do_GET')
        assert hasattr(handler, 'do_POST')


# ============================================================
# FASE 10: SDK
# ============================================================

class TestWalletSDK:
    def test_create_wallet(self):
        from baitcoin_sdk.wallet_sdk import AgentWalletSDK
        class FakeSDK: pass
        wsdk = AgentWalletSDK(FakeSDK())
        w = wsdk.create("agent_1")
        assert w.agent_id == "agent_1"
        assert w.address.startswith("bAI1q")
        assert len(w.pubkey_hex) == 64

    def test_sign(self):
        from baitcoin_sdk.wallet_sdk import AgentWalletSDK
        class FakeSDK: pass
        wsdk = AgentWalletSDK(FakeSDK())
        w = wsdk.create("agent_1")
        sig = w.sign(b"test message")
        assert len(sig) == 64

    def test_list_wallets(self):
        from baitcoin_sdk.wallet_sdk import AgentWalletSDK
        class FakeSDK: pass
        wsdk = AgentWalletSDK(FakeSDK())
        wsdk.create("a1")
        wsdk.create("a2")
        wallets = wsdk.list_wallets()
        assert len(wallets) == 2


class TestSDKClient:
    def test_local_mode(self):
        from baitcoin_sdk.client import BaitcoinSDK
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_bank.staking.pool import StakingPool
        from baitcoin_ai.agent_protocol.registry import AgentRegistry
        from baitcoin_ai.marketplace.services import AIMarketplace
        from baitcoin_ai.oracle.feed import PriceOracle

        sdk = BaitcoinSDK()
        bc = Blockchain()
        token = BAITToken()
        token.mint("agent_1", 100 * 100_000_000)

        sdk.configure_local(
            blockchain=bc, token=token, faucet=None,
            staking=StakingPool(), registry=AgentRegistry(),
            marketplace=AIMarketplace(), oracle=PriceOracle(),
        )

        assert sdk.get_balance("agent_1") == 100.0
        assert sdk.transfer("agent_1", "agent_2", 50.0)
        assert sdk.get_balance("agent_2") == 50.0

    def test_create_wallet_via_sdk(self):
        from baitcoin_sdk.client import BaitcoinSDK
        sdk = BaitcoinSDK()
        w = sdk.create_wallet("test_agent")
        assert w.address.startswith("bAI1q")

    def test_network_status(self):
        from baitcoin_sdk.client import BaitcoinSDK
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_token.erc20_like.bait_token import BAITToken
        sdk = BaitcoinSDK()
        sdk.configure_local(
            blockchain=Blockchain(), token=BAITToken(),
            faucet=None, staking=None, registry=None,
            marketplace=None, oracle=None,
        )
        status = sdk.get_network_status()
        assert "blockchain" in status
        assert "token" in status


class TestStakingSDK:
    def test_stake_via_sdk(self):
        from baitcoin_sdk.client import BaitcoinSDK
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_bank.staking.pool import StakingPool
        sdk = BaitcoinSDK()
        sdk.configure_local(
            blockchain=Blockchain(), token=BAITToken(),
            faucet=None, staking=StakingPool(),
            registry=None, marketplace=None, oracle=None,
        )
        assert sdk.stake("agent_1", 1500.0)
        info = sdk.get_staking_info()
        assert info["total_staked_bait"] == 1500.0


class TestMarketplaceSDK:
    def test_search_services(self):
        from baitcoin_sdk.client import BaitcoinSDK
        from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory
        mp = AIMarketplace()
        mp.list_service("a1", ServiceCategory.ML_INFERENCE, "GPT", "desc", 50_000)
        sdk = BaitcoinSDK()
        sdk.configure_local(
            blockchain=None, token=None, faucet=None,
            staking=None, registry=None, marketplace=mp, oracle=None,
        )
        results = sdk.search_services("ml_inference")
        assert len(results) >= 1


# ============================================================
# INTEGRACAO FULL 10 FASES
# ============================================================

class TestFullEcosystemV2:
    def test_all_phases_integrated(self):
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
        from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
        from baitcoin_core.network.p2p_real.protocol import P2PProtocol
        from baitcoin_core.network.peer_discovery.dht import PeerDiscovery
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_bank.staking.pool import StakingPool
        from baitcoin_bank.lending.engine import LendingEngine
        from baitcoin_bank.defi_core.vault import Vault, VaultConfig, StrategyType
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
        from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory
        from baitcoin_ai.oracle.feed import PriceOracle
        from baitcoin_faucet.faucet import BAITFaucet
        from baitcoin_sdk.client import BaitcoinSDK
        from baitcoin_mainnet.config import MainnetConfig

        # Phase 9: Config
        cfg = MainnetConfig()
        assert cfg.is_mainnet()

        # Phase 7: P2P
        p2p = P2PProtocol(node_id="integ_test")
        disc = PeerDiscovery("integ_test")
        disc.add_peer("p1", "10.0.0.1", 18444)
        assert len(disc.discover()) >= 1

        # Blockchain + Token
        bc = Blockchain()
        token = BAITToken()
        token.mint("alice", 10_000 * 100_000_000)

        # Phase 9: Faucet
        faucet = BAITFaucet(token, cooldown=0)
        r = faucet.claim("bob", "0xpub")
        assert r["success"]

        # Phase 8: zkML
        zk = ZkMLProofSystem()
        verifier = ZkMLVerifier()
        proof = zk.generate_proof("validator_1", "gpt-4", b"input", b"output", "blk", 1)
        assert verifier.verify(proof)["valid"]

        # Tensor commitment
        tc = TensorCommitmentScheme.commit(b"tensor_data")
        assert TensorCommitmentScheme.verify(TensorCommitmentScheme.open(tc, b"tensor_data"), b"tensor_data")

        # Phase 3: Be Your Bank
        pool = StakingPool()
        pool.stake("alice", 2_000 * 100_000_000)
        vault = Vault(VaultConfig(agent_id="alice"))
        vault.deposit(5_000_000_000, StrategyType.STAKING)

        # Phase 5: AI Protocol
        reg = AgentRegistry()
        reg.register("alice", "0xabc", [AgentCapability.BLOCK_VALIDATION])

        # Phase 10: SDK
        sdk = BaitcoinSDK()
        sdk.configure_local(bc, token, faucet, pool, reg,
                           AIMarketplace(), PriceOracle())
        assert sdk.get_balance("alice") == 10_000.0

        print("\n[OK] All 10 phases integrated successfully!")
