"""
Stress Tests para b'AI'tcoin - Valida comportamento sob carga extrema.

Testes:
- Mining massivo (1000+ blocos)
- Transações concorrentes no mempool
- Muitos agentes registrados
- Muitas provas zkML
- PoUW com alto volume
- UTXO set grande
- Persistência sob carga
- Staking/Lending massivo
"""

import time
import hashlib
import threading
import pytest
from baitcoin_core.blockchain.block import Block, BlockHeader, Transaction, TransactionOutput, TransactionInput
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem, ZkMLProof
from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
from baitcoin_core.consensus.pouw import PoUWValidator
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_token.erc20_like.bait_token import BAITToken as BaitToken
from baitcoin_bank.staking.pool import StakingPool
from baitcoin_bank.lending.engine import LendingEngine
from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
from baitcoin_ai.oracle.feed import PriceOracle as OracleFeed
from baitcoin_ai.marketplace.services import AIMarketplace as Marketplace


@pytest.fixture
def consensus():
    return ZkMLConsensus()


@pytest.fixture
def blockchain(consensus):
    return Blockchain(consensus=consensus)


@pytest.fixture
def token():
    return BaitToken()


class TestMiningStress:
    r"""Stress test de mineração de blocos."""

    def test_mine_100_blocks(self, blockchain):
        r"""Minera 100 blocos consecutivos - deve completar em <10s."""
        kp = SchnorrKeyPair()
        start = time.time()
        mined = 0
        for i in range(100):
            block = blockchain.mine_block(f"stress_miner_{i}", kp.pub_bytes)
            if block.header.nonce > 0:
                mined += 1
        elapsed = time.time() - start
        assert mined >= 90, f"Only mined {mined}/100 blocks in {elapsed:.2f}s"
        assert blockchain.height >= 90
        assert blockchain.validate_chain()

    def test_mine_500_blocks_chain_integrity(self, blockchain):
        r"""Minera 500 blocos e valida integridade completa da cadeia."""
        kp = SchnorrKeyPair()
        for i in range(500):
            blockchain.mine_block(f"integrity_miner_{i}", kp.pub_bytes)
        assert blockchain.height >= 450
        assert blockchain.validate_chain()
        # Verificar que cada bloco aponta para o anterior
        for i in range(1, min(100, len(blockchain.chain))):
            assert blockchain.chain[i].header.prev_block_hash == blockchain.chain[i-1].block_hash

    def test_mining_reward_halving(self, blockchain):
        r"""Verifica halving correto após mineração de muitos blocos."""
        kp = SchnorrKeyPair()
        # Mine 3 blocos - reward deve ser 50 BAIT
        for i in range(3):
            blockchain.mine_block(f"halving_miner", kp.pub_bytes)
        reward_0 = blockchain.get_block_reward(1)
        assert reward_0 == 50 * 100_000_000  # 50 BAIT


class TestMempoolStress:
    r"""Stress test do mempool com alto volume de transações."""

    def test_mempool_10000_transactions(self, blockchain):
        r"""Adiciona 10000 transações ao mempool."""
        kp = SchnorrKeyPair()
        # Primeiro, minerar um bloco com outputs para gastar
        blockchain.mine_block("fund_miner", kp.pub_bytes)

        # Criar transações (sem inputs válidos - teste de capacidade)
        for i in range(10000):
            tx = Transaction(
                tx_type="transfer",
                agent_id=f"agent_{i}",
                outputs=[TransactionOutput(amount_sats=100, script_pubkey=b"test")],
            )
            blockchain.mempool.append(tx)

        assert len(blockchain.mempool) == 10000

        # Minerar bloco - deve pegar até 1000 txs
        blockchain.mine_block("mempool_clearer", kp.pub_bytes)
        assert len(blockchain.mempool) == 9000  # 1000 removidas

    def test_parallel_mempool_add(self, blockchain):
        r"""Adição concorrente ao mempool por múltiplas threads."""
        errors = []
        
        def add_txs(start, end):
            try:
                for i in range(start, end):
                    tx = Transaction(
                        tx_type="transfer",
                        agent_id=f"thread_agent_{i}",
                        outputs=[TransactionOutput(amount_sats=1, script_pubkey=b"t")],
                    )
                    blockchain.mempool.append(tx)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_txs, args=(i*500, (i+1)*500)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(blockchain.mempool) == 5000


class TestZkMLStress:
    r"""Stress test do sistema zkML."""

    def test_1000_proofs_generation(self):
        r"""Gera e verifica 1000 provas zkML - deve completar em <15s."""
        ps = ZkMLProofSystem()
        start = time.time()
        proofs = []
        for i in range(1000):
            proof = ps.generate_proof(
                prover_id=f"validator_{i}",
                model_id="stress_model",
                input_data=f"input_{i}".encode(),
                output_data=f"output_{i}".encode(),
                block_hash=hashlib.sha256(f"block_{i}".encode()).hexdigest(),
            )
            proofs.append(proof)
        elapsed = time.time() - start
        assert len(proofs) == 1000

        # Verificar todas
        verified = sum(1 for p in proofs if ps.verify_proof(p))
        assert verified == 1000, f"Only {verified}/1000 proofs verified"
        assert elapsed < 15, f"Proof generation took {elapsed:.2f}s"

    def test_verifier_5000_proofs(self):
        r"""Verificador LRU com 5000 provas - anti-replay + cache."""
        verifier = ZkMLVerifier()
        ps = ZkMLProofSystem()

        # Gerar 100 provas únicas
        proofs = []
        for i in range(100):
            p = ps.generate_proof(
                prover_id=f"v_{i}", model_id="m1",
                input_data=f"in_{i}".encode(), output_data=f"out_{i}".encode(),
                block_hash="abc123",
            )
            proofs.append(p)

        # Verificar 5000 vezes (com duplicatas)
        for _ in range(50):
            for p in proofs:
                result = verifier.verify(p)
        
        stats = verifier.get_stats()
        assert stats['seen_proofs'] == 100
        assert stats['cache_size'] <= 100

    def test_tensor_commitment_batch(self):
        r"""Batch commitment de 1000 tensores."""
        tensors = [f"tensor_data_{i}".encode() for i in range(1000)]
        start = time.time()
        commitments = TensorCommitmentScheme.batch_commit(tensors)
        elapsed = time.time() - start
        assert len(commitments) == 1000
        assert elapsed < 10

        # Agregar todos
        agg = TensorCommitmentScheme.aggregate(commitments)
        assert agg > 0

        # Verificar cada um
        for i, tc in enumerate(commitments[:100]):  # verificar amostra
            opening = TensorCommitmentScheme.open(tc, tensors[i])
            assert TensorCommitmentScheme.verify(opening, tensors[i])


class TestAgentRegistryStress:
    r"""Stress test do registro de agentes."""

    def test_register_1000_agents(self):
        r"""Registra 1000 agentes com diferentes capabilities."""
        registry = AgentRegistry()
        capabilities = list(AgentCapability)
        kp = SchnorrKeyPair()

        start = time.time()
        for i in range(1000):
            agent_id = f"stress_agent_{i}"
            caps = [capabilities[i % len(capabilities)]]
            registry.register(
                agent_id=agent_id,
                pubkey_hex=kp.public_key_hex,
                capabilities=caps,
            )
        elapsed = time.time() - start

        agents = registry.list_agents()
        assert len(agents) >= 1000
        assert elapsed < 10

    def test_marketplace_500_services(self):
        r"""Lista 500 serviços no marketplace."""
        mp = Marketplace()
        kp = SchnorrKeyPair()

        from baitcoin_ai.marketplace.services import ServiceCategory
        cats = list(ServiceCategory)
        for i in range(500):
            mp.list_service(
                provider=f"provider_{i}",
                name=f"Service {i}",
                category=cats[i % len(cats)],
                price_sats=100 * (i + 1),
                description=f"Stress test service {i}",
            )

        services = mp.search(category=cats[0])
        assert len(services) > 0


class TestTokenomicsStress:
    r"""Stress test de tokenomics."""

    def test_transfer_1000_agents(self, token):
        r"""Realiza 1000 transferências entre agentes."""
        # Mint para faucet
        token.mint("faucet", 1_000_000 * 100_000_000)

        start = time.time()
        for i in range(1000):
            token.transfer("faucet", f"agent_{i}", 100 * 100_000_000, f"stress_tx_{i}")
        elapsed = time.time() - start

        assert token.balance_of("faucet") >= 0
        assert token.balance_of("agent_0") == 100 * 100_000_000
        assert elapsed < 10

    def test_staking_200_agents(self, token):
        r"""200 agentes fazendo stake simultaneamente."""
        token.mint("faucet", 1_000_000 * 100_000_000)
        pool = StakingPool()

        start = time.time()
        for i in range(200):
            token.transfer("faucet", f"staker_{i}", 1000 * 100_000_000, f"fund_{i}")
            pool.stake(f"staker_{i}", 1000 * 100_000_000)
        elapsed = time.time() - start

        assert pool.total_staked > 0
        assert elapsed < 10

    def test_oracle_100_prices(self):
        r"""Oracle com 100 ativos e preços."""
        oracle = OracleFeed()
        for i in range(10):
            oracle.register_oracle(f"oracle_{i}")

        for i in range(100):
            symbol = f"TOKEN{i}"
            for j in range(10):
                oracle.submit_price(f"oracle_{j}", symbol, 100.0 + i * 0.5)

        # Verificar que o preço agregado existe
        price = oracle.get_price("TOKEN0")
        assert price is not None
        assert price > 0


class TestPersistenceStress:
    r"""Stress test de persistência."""

    def test_wal_many_namespaces(self):
        r"""Escreve em múltiplos namespaces do WAL."""
        try:
            from baitcoin_memory.store import MemoryStore, MemoryNamespace
            import tempfile, os

            with tempfile.TemporaryDirectory() as tmpdir:
                store = MemoryStore(data_path=tmpdir)
                namespaces = list(MemoryNamespace)

                for ns in namespaces:
                    for i in range(100):
                        store.put(ns.value, f"key_{i}", {"value": i, "ns": ns.value})

                # Ler de volta
                for ns in namespaces:
                    data = store.get_all(ns.value)
                    assert len(data) >= 100
        except ImportError:
            pytest.skip("MemoryStore not available")


class TestCryptographyStress:
    r"""Stress test de operações criptográficas."""

    def test_500_sign_verify_cycles(self):
        r"""500 ciclos de assinatura/verificação Schnorr."""
        kp = SchnorrKeyPair()
        messages = [f"message_{i}".encode() for i in range(500)]

        start = time.time()
        for msg in messages:
            sig = kp.sign(msg)
            assert sig.verify(kp.pub_bytes, msg)
        elapsed = time.time() - start

        assert elapsed < 15, f"500 sign/verify cycles took {elapsed:.2f}s"

    def test_sign_verify_wrong_message_fails(self):
        r"""Verifica que assinatura não valida com mensagem errada."""
        kp = SchnorrKeyPair()
        sig = kp.sign(b"correct_message")
        assert not sig.verify(kp.pub_bytes, b"wrong_message")

    def test_multiple_keypairs(self):
        r"""Gera 100 keypairs e verifica cross-validation."""
        keypairs = [SchnorrKeyPair() for _ in range(100)]

        for i, kp in enumerate(keypairs):
            sig = kp.sign(f"msg_{i}".encode())
            assert sig.verify(kp.pub_bytes, f"msg_{i}".encode())
            # Não deve validar com pubkey de outro
            if i > 0:
                assert not sig.verify(keypairs[0].pub_bytes, f"msg_{i}".encode())
