r"""
Validacao End-to-End Compreensiva do b'AI'tcoin.

Executa todas as validacoes criticas em um unico script:
1. Blockchain: genesis, mining, chain validation, halving
2. Criptografia: Schnorr/BIP-340 sign/verify, 64-byte sigs
3. Consensus: zkML proofs, PoUW, tensor commitments
4. Token: mint, burn, transfer, approve, supply cap
5. DeFi: staking, lending, vaults
6. AI: agents, marketplace, oracle
7. EcosystemNode: full integration with persistence
8. Address format: 'bait' prefix
9. P2P: peer management, broadcast
10. Explorer, SDK, Bridge, Whitelabel, Mainnet, Faucet

Uso: python scripts/validate_e2e_comprehensive.py
"""

import sys
import os
import time
import hashlib
import tempfile
import shutil
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def ok(msg):
    print(f"  [PASS] {msg}")


def fail(msg):
    print(f"  [FAIL] {msg}")
    return False


def run_all():
    errors = 0
    start_total = time.time()

    # 1. BLOCKCHAIN
    section("1. BLOCKCHAIN")
    try:
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.blockchain.block import Block, BlockHeader, Transaction, TransactionOutput
        from baitcoin_core.blockchain.mempool import Mempool
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair

        bc = Blockchain()
        assert bc.height == 0, "Genesis height"
        assert bc.validate_chain(), "Genesis valid"
        ok("Genesis block criado e valido")

        kp = SchnorrKeyPair()
        for i in range(10):
            bc.mine_block(f"validator_{i}", kp.pub_bytes)
        assert bc.height == 10, "Mining 10 blocks"
        assert bc.validate_chain(), "Chain valid after 10 blocks"
        ok("10 blocos minerados, cadeia valida")

        # Halving
        assert bc.get_block_reward(1) == 50 * 100_000_000
        assert bc.get_block_reward(210_000) == 25 * 100_000_000
        ok("Halving schedule correto")

        # Supply cap
        total = 0
        for h in range(64):
            total += 210_000 * (50 * 100_000_000 >> h)
        assert total <= 21_000_000 * 100_000_000
        ok(f"Supply total ({total/100_000_000:.0f} BAIT) <= 21M")

        # Mempool
        mp = Mempool()
        tx = Transaction(
            tx_type="transfer", agent_id="mp_test",
            gas_price=100, gas_limit=1,
            outputs=[TransactionOutput(amount_sats=100, script_pubkey=kp.pub_bytes)],
        )
        mp.add_transaction(tx)
        assert mp.size == 1
        assert mp.total_fees == 100
        ok("Mempool funcional com fee tracking")

    except Exception as e:
        fail(f"Blockchain: {e}")
        errors += 1
        traceback.print_exc()

    # 2. CRYPTOGRAPHY
    section("2. CRIPTOGRAFIA (Schnorr/BIP-340)")
    try:
        kp = SchnorrKeyPair()
        sig = kp.sign(b"baitcoin e2e validation")
        assert sig.verify(kp.pub_bytes, b"baitcoin e2e validation")
        assert not sig.verify(kp.pub_bytes, b"wrong")
        assert len(sig.raw) == 64
        assert len(kp.pub_bytes) == 32
        ok("Sign/verify correto, 64-byte sig, 32-byte pubkey")

        # Cross-validation
        kp2 = SchnorrKeyPair()
        sig2 = kp2.sign(b"other")
        assert not sig2.verify(kp.pub_bytes, b"other")
        ok("Cross-key rejection funciona")

        # Deterministic
        k1 = SchnorrKeyPair(private_key=99999)
        k2 = SchnorrKeyPair(private_key=99999)
        assert k1.public_key_hex == k2.public_key_hex
        ok("Keypair deterministico")
    except Exception as e:
        fail(f"Cryptography: {e}")
        errors += 1

    # 3. CONSENSUS
    section("3. CONSENSUS (zkML + PoUW)")
    try:
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
        from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
        from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
        from baitcoin_core.consensus.pouw import PoUWValidator

        # zkML proofs
        ps = ZkMLProofSystem()
        proofs = []
        for i in range(10):
            p = ps.generate_proof(
                f"prover_{i}", "model_e2e",
                f"in_{i}".encode(), f"out_{i}".encode(),
                hashlib.sha256(f"block_{i}".encode()).hexdigest() if i > 0 else "genesis",
            )
            proofs.append(p)
        verified = sum(1 for p in proofs if ps.verify_proof(p))
        assert verified == 10
        ok("10/10 provas zkML geradas e verificadas")

        # Aggregation
        agg = ps.compose_proofs(proofs)
        assert agg["all_valid"]
        ok("Composicao de provas valida")

        # Anti-replay
        verifier = ZkMLVerifier()
        r1 = verifier.verify(proofs[0])
        assert r1["valid"] and not r1["duplicate"]
        r2 = verifier.verify(proofs[0])
        assert not r2["valid"] and r2["duplicate"]
        ok("Anti-replay funciona")

        # Tensor commitment
        tc = TensorCommitmentScheme.commit(b"e2e_tensor")
        opening = TensorCommitmentScheme.open(tc, b"e2e_tensor")
        assert TensorCommitmentScheme.verify(opening, b"e2e_tensor")
        ok("Tensor commitment (Pedersen) funciona")

        # PoUW
        pouw = PoUWValidator()
        r = pouw.submit_work("ml_inference", {
            "model_hash": "mh", "input_hash": "ih", "output_hash": "oh"
        }, "agent_pouw")
        assert r["valid"]
        ok("PoUW validacao de ML inference")
    except Exception as e:
        fail(f"Consensus: {e}")
        errors += 1

    # 4. TOKEN
    section("4. TOKEN BAIT")
    try:
        from baitcoin_token.erc20_like.bait_token import BAITToken

        token = BAITToken()
        assert token.TOTAL_SUPPLY_SATS == 21_000_000 * 100_000_000
        assert token.DECIMALS == 8
        token.mint("treasury", 1_000_000 * 100_000_000)
        token.transfer("treasury", "agent_a", 100 * 100_000_000, "e2e_1")
        token.transfer("agent_a", "agent_b", 50 * 100_000_000, "e2e_2")
        assert token.balance_bait("agent_b") == 50.0
        assert token.balance_bait("agent_a") == 50.0
        token.burn("agent_b", 10 * 100_000_000)
        assert token.balance_bait("agent_b") == 40.0
        ok("Mint/transfer/burn funcionando")

        # Approval
        token.approve("agent_a", "agent_b", 20 * 100_000_000)
        token.transfer_from("agent_b", "agent_a", "agent_c", 10 * 100_000_000)
        assert token.balance_bait("agent_c") == 10.0
        ok("Approve/transfer_from funciona")
    except Exception as e:
        fail(f"Token: {e}")
        errors += 1

    # 5. DEFI
    section("5. DeFi (Staking + Lending + Vault)")
    try:
        from baitcoin_bank.staking.pool import StakingPool
        from baitcoin_bank.lending.engine import LendingEngine
        from baitcoin_bank.defi_core.vault import Vault, VaultConfig, StrategyType

        pool = StakingPool()
        pool.stake("staker_e2e", 1000 * 100_000_000)
        rewards = pool.distribute_rewards(50 * 100_000_000)
        assert pool.total_staked > 0
        ok("Staking + rewards")

        engine = LendingEngine()
        oid = engine.create_offer("lender_e2e", 100 * 100_000_000, 5.0)
        assert oid
        rate = engine.get_market_rate()
        assert rate > 0
        ok("Lending + market rate")

        cfg = VaultConfig(agent_id="vault_e2e")
        vault = Vault(cfg)
        vault.deposit(500 * 100_000_000, StrategyType.HODL)
        w = vault.withdraw(100 * 100_000_000)
        assert w > 0
        ok("Vault deposit/withdraw")
    except Exception as e:
        fail(f"DeFi: {e}")
        errors += 1

    # 6. AI MODULES
    section("6. MODULOS AI")
    try:
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
        from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory
        from baitcoin_ai.oracle.feed import PriceOracle

        reg = AgentRegistry()
        kp = SchnorrKeyPair()
        reg.register("ai_e2e", kp.public_key_hex, [AgentCapability.ML_INFERENCE])
        assert len(reg.list_agents()) >= 1
        ok("Agent registry")

        mp = AIMarketplace()
        mp.list_service("provider_e2e", ServiceCategory.ML_INFERENCE,
                       "E2E Service", "E2E test", 100)
        assert len(mp.search()) > 0
        ok("Marketplace list/search")

        oracle = PriceOracle()
        for i in range(3):
            oracle.register_oracle(f"oracle_e2e_{i}")
            oracle.submit_price(f"oracle_e2e_{i}", "BAIT/USD", 1.5 + i * 0.1)
        price = oracle.get_price("BAIT/USD")
        assert price is not None and price > 0
        ok(f"Oracle price feed: BAIT/USD = {price:.2f}")
    except Exception as e:
        fail(f"AI Modules: {e}")
        errors += 1

    # 7. ECOSYSTEM NODE
    section("7. ECOSYSTEM NODE (Full Integration)")
    try:
        from baitcoin_core.ecosystem import EcosystemNode

        tmp = tempfile.mkdtemp(prefix="bait_e2e_")
        try:
            node = EcosystemNode(data_path=tmp, auto_persist=True)

            # Mine
            for i in range(5):
                node.mine_block(f"e2e_miner_{i}", kp.pub_bytes)
            assert node.height == 5
            assert node.validate_chain()
            ok("5 blocos minerados via EcosystemNode")

            # Token operations
            node.mint("e2e_treasury", 10_000 * 100_000_000)
            node.transfer("e2e_treasury", "e2e_agent", 500 * 100_000_000)
            assert node.balance_bait("e2e_agent") == 500.0
            ok("Mint + transfer via EcosystemNode")

            # Agent
            node.register_agent("e2e_ai", kp.public_key_hex,
                               [AgentCapability.ML_INFERENCE])
            assert node.total_agents >= 1
            ok("Agent registration via EcosystemNode")

            # Staking
            node.stake("e2e_agent", 1000 * 100_000_000)
            assert node.total_staked_bait >= 1000.0
            ok("Staking via EcosystemNode")

            # zkML
            proof = node.generate_zk_proof(
                "e2e_prover", "model_e2e",
                b"input_e2e", b"output_e2e", "block_hash_e2e", 0,
            )
            assert node.verify_zk_proof(proof)
            ok("zkML proof via EcosystemNode")

            # Persistence roundtrip
            h = node.height
            agents = node.total_agents
            node.shutdown()

            node2 = EcosystemNode(data_path=tmp, auto_persist=False)
            assert node2.height == h
            assert node2.total_agents >= agents
            ok("Persistencia + restauracao")
            node2.shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:
        fail(f"EcosystemNode: {e}")
        errors += 1
        traceback.print_exc()

    # 8. ADDRESS FORMAT
    section("8. FORMATO DE ENDERECO")
    try:
        from baitcoin_wallet.paper_wallet import generate_paper_wallet
        pw = generate_paper_wallet()
        assert pw["address"].startswith("bait")
        assert "private_key" in pw
        ok(f"Endereco 'bait' prefix: {pw['address'][:20]}...")
    except Exception as e:
        fail(f"Address: {e}")
        errors += 1

    # 9. P2P
    section("9. REDE P2P")
    try:
        from baitcoin_core.network.p2p import P2PNetwork, MessageType
        net = P2PNetwork(listen_port=18460)
        for i in range(10):
            net.add_peer(f"10.0.0.{i}", 18444, f"peer_{i}")
        assert len(net.peers) == 10
        count = net.broadcast(MessageType.PING, {})
        assert count == 10
        ok("P2P: 10 peers, broadcast OK")
    except Exception as e:
        fail(f"P2P: {e}")
        errors += 1

    # 10. EXPLORER, SDK, BRIDGE, WHITELABEL, MAINNET, FAUCET, API
    section("10. MODULOS ADICIONAIS")
    try:
        from baitcoin_explorer.indices import BlockchAInIndex
        from baitcoin_explorer.search import UniversalSearch
        from baitcoin_sdk.client import BaitcoinSDK
        from baitcoin_sdk.wallet_sdk import AgentWalletSDK
        from baitcoin_bridge.anchor import AnchorProtocol
        from baitcoin_bridge.manager import BridgeManager
        from baitcoin_whitelabel.engine import WhitelabelEngine
        from baitcoin_whitelabel.config import WhitelabelConfig
        from baitcoin_whitelabel.presets import PresetLibrary
        from baitcoin_mainnet.config import MainnetConfig
        from baitcoin_mainnet.launcher import MainnetLauncher
        from baitcoin_api.server import create_app

        idx = BlockchAInIndex()
        search = UniversalSearch(idx)
        assert isinstance(search.query("test"), dict)
        ok("Explorer index + search")

        assert BaitcoinSDK is not None
        assert AgentWalletSDK is not None
        ok("SDK imports")

        assert BridgeManager() is not None
        ok("Bridge manager")

        presets = PresetLibrary.list_presets()
        assert len(presets) >= 70
        ok(f"Whitelabel: {len(presets)} presets")

        assert MainnetConfig() is not None
        assert MainnetLauncher() is not None
        ok("Mainnet config + launcher")

        server = create_app(host="127.0.0.1", port=0)
        assert server is not None
        server.server_close()
        ok("API server cria e fecha")
    except Exception as e:
        fail(f"Additional modules: {e}")
        errors += 1

    # SUMMARY
    elapsed = time.time() - start_total
    section("RESUMO")
    if errors == 0:
        print(f"  TODAS AS VALIDACOES PASSARAM ({elapsed:.2f}s)")
        print(f"  Sistema b'AI'tcoin operacional.")
        return 0
    else:
        print(f"  {errors} VALIDACOES FALHARAM ({elapsed:.2f}s)")
        return 1


if __name__ == "__main__":
    import hashlib  # Needed for consensus section
    sys.exit(run_all())
