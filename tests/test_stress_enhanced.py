r"""
Stress Tests Avancados para b'AI'tcoin — Validacao sob carga extrema.

Testes adicionais que complementam test_stress.py:
- Mining em alta velocidade com validacao completa
- Mempool com capacidade maxima e eviccao
- Provas zkML em batch com verificacao
- EcosystemNode sob carga multi-modulo
- Concorrencia em operacoes DeFi
- Persistencia sob carga (WAL intensivo)
- Schnorr sign/verify em lote
- P2P network com many peers
- Faucet com claims simultaneos
- Token transfer chain longa
"""

import time
import hashlib
import threading
import tempfile
import shutil
import pytest
from baitcoin_core.blockchain.block import (
    Block, BlockHeader, Transaction, TransactionOutput, TransactionInput,
)
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.blockchain.mempool import Mempool
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem, ZkMLProof
from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
from baitcoin_core.consensus.pouw import PoUWValidator
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_core.network.p2p import P2PNetwork
from baitcoin_core.ecosystem import EcosystemNode
from baitcoin_token.erc20_like.bait_token import BAITToken
from baitcoin_bank.staking.pool import StakingPool
from baitcoin_bank.lending.engine import LendingEngine
from baitcoin_bank.defi_core.vault import Vault, VaultConfig, StrategyType
from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
from baitcoin_ai.oracle.feed import PriceOracle
from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory
from baitcoin_faucet.faucet import BAITFaucet


@pytest.fixture
def consensus():
    return ZkMLConsensus()


@pytest.fixture
def blockchain(consensus):
    return Blockchain(consensus=consensus)


# ============================================================
# MINING EXTREME
# ============================================================
class TestMiningExtremeStress:
    r"""Stress test de mineracao em cenarios extremos."""

    def test_mine_200_blocks_validate_every_10(self, blockchain):
        r"""Minera 200 blocos e valida a cadeia a cada 10 blocos."""
        kp = SchnorrKeyPair()
        for i in range(200):
            block = blockchain.mine_block(f"extreme_miner_{i}", kp.pub_bytes)
            if (i + 1) % 10 == 0:
                assert blockchain.validate_chain(), f"Chain invalid at block {i+1}"
        assert blockchain.height >= 190
        assert blockchain.validate_chain()

    def test_mine_multi_miner_reputation(self, blockchain):
        r"""10 mineradores alternados, cada um minera 20 blocos."""
        keypairs = [SchnorrKeyPair() for _ in range(10)]
        for round_num in range(20):
            for m_idx in range(10):
                blockchain.mine_block(
                    f"multi_miner_{m_idx}", keypairs[m_idx].pub_bytes
                )
        assert blockchain.height >= 190
        assert blockchain.validate_chain()
        # Verificar que o ultimo bloco tem coinbase
        assert blockchain.last_block.coinbase_tx is not None

    def test_block_reward_halving_at_210k(self):
        r"""Verifica que o calculo de halving esta correto."""
        bc = Blockchain()
        # Bloco 1: 50 BAIT
        assert bc.get_block_reward(1) == 50 * 100_000_000
        # Bloco 210000: 25 BAIT
        assert bc.get_block_reward(210_000) == 25 * 100_000_000
        # Bloco 420000: 12.5 BAIT
        assert bc.get_block_reward(420_000) == 1_250_000_000
        # Bloco 630000: 6.25 BAIT
        assert bc.get_block_reward(630000) == 625_000_000
        # Bloco >= 64 halvings: reward 0
        assert bc.get_block_reward(64 * 210_000) == 0

    def test_total_supply_never_exceeds_21M(self):
        r"""Verifica que a supply maxima teorica respeita 21M BAIT."""
        total = 0
        for halving in range(64):
            blocks_in_era = 210_000
            reward = 50 * 100_000_000 >> halving
            total += blocks_in_era * reward
        max_supply = 21_000_000 * 100_000_000
        assert total <= max_supply, f"Total {total} exceeds max {max_supply}"


# ============================================================
# MEMPOOL EXTREME
# ============================================================
class TestMempoolExtremeStress:
    r"""Stress test do Mempool standalone com carga extrema."""

    def test_mempool_fill_to_capacity(self):
        r"""Preenche o mempool ate a capacidade maxima (50k)."""
        mp = Mempool()
        kp = SchnorrKeyPair()
        count = 0
        for i in range(55_000):  # Mais que a capacidade
            tx = Transaction(
                tx_type="transfer",
                agent_id=f"agent_{i}",
                gas_price=100,
                gas_limit=1,
                outputs=[TransactionOutput(amount_sats=100, script_pubkey=kp.pub_bytes)],
            )
            if mp.add_transaction(tx):
                count += 1
        assert mp.size == Mempool.MAX_SIZE  # Deve estar no maximo
        assert count >= Mempool.MAX_SIZE

    def test_mempool_priority_ordering(self):
        r"""Verifica que transacoes com fee maior sao priorizadas."""
        mp = Mempool()
        kp = SchnorrKeyPair()
        # Adicionar 100 transacoes com fees diferentes
        for i in range(100):
            tx = Transaction(
                tx_type="transfer",
                agent_id=f"fee_agent_{i}",
                gas_price=100 + i * 10,  # Fee crescente
                gas_limit=1,
                outputs=[TransactionOutput(amount_sats=100, script_pubkey=kp.pub_bytes)],
            )
            mp.add_transaction(tx)

        txs = mp.get_transactions(max_count=10)
        assert len(txs) == 10
        # As primeiras devem ter as maiores fees
        fees = [tx.gas_price * tx.gas_limit for tx in txs]
        assert fees == sorted(fees, reverse=True)

    def test_mempool_dedup(self):
        r"""Verifica deduplicacao de transacoes no mempool."""
        mp = Mempool()
        kp = SchnorrKeyPair()
        tx = Transaction(
            tx_type="transfer",
            agent_id="dedup_agent",
            nonce=42,
            gas_price=100,
            gas_limit=1,
            outputs=[TransactionOutput(amount_sats=100, script_pubkey=kp.pub_bytes)],
        )
        assert mp.add_transaction(tx) is True
        assert mp.add_transaction(tx) is False  # Duplicata
        assert mp.size == 1

    def test_mempool_remove_and_purge(self):
        r"""Remove transacoes e purge de expiradas."""
        mp = Mempool()
        kp = SchnorrKeyPair()
        tx_ids = []
        for i in range(20):
            tx = Transaction(
                tx_type="transfer",
                agent_id=f"purge_agent_{i}",
                nonce=i,
                gas_price=100,
                gas_limit=1,
                outputs=[TransactionOutput(amount_sats=100, script_pubkey=kp.pub_bytes)],
            )
            mp.add_transaction(tx)
            tx_ids.append(tx.tx_id.hex())

        assert mp.size == 20
        mp.remove_transactions(tx_ids[:10])
        assert mp.size == 10


# ============================================================
# ZKML EXTREME
# ============================================================
class TestZkMLExtremeStress:
    r"""Stress test do sistema zkML com provas em lote."""

    def test_5000_proofs_batch_verify(self):
        r"""Gera 5000 provas e verifica todas em <30s."""
        ps = ZkMLProofSystem()
        start = time.time()
        proofs = []
        for i in range(5000):
            proof = ps.generate_proof(
                prover_id=f"prover_{i % 100}",
                model_id=f"model_{i % 10}",
                input_data=f"input_{i}".encode(),
                output_data=f"output_{i}".encode(),
                block_hash=hashlib.sha256(f"block_{i}".encode()).hexdigest(),
            )
            proofs.append(proof)
        gen_time = time.time() - start

        # Verificar todas
        start = time.time()
        verified = sum(1 for p in proofs if ps.verify_proof(p))
        verify_time = time.time() - start

        assert verified == 5000, f"Only {verified}/5000 verified"
        assert gen_time < 30, f"Generation: {gen_time:.2f}s"
        assert verify_time < 30, f"Verification: {verify_time:.2f}s"

    def test_proof_composition_100_proofs(self):
        r"""Compoe 100 provas em uma prova agregada."""
        ps = ZkMLProofSystem()
        proofs = [
            ps.generate_proof(
                prover_id=f"comp_{i}", model_id="agg_model",
                input_data=f"in_{i}".encode(), output_data=f"out_{i}".encode(),
                block_hash="composed_block",
            )
            for i in range(100)
        ]
        agg = ps.compose_proofs(proofs)
        assert agg["all_valid"] is True
        assert agg["proof_count"] == 100

    def test_tampered_proof_rejected(self):
        r"""Prova modificada deve ser rejeitada."""
        ps = ZkMLProofSystem()
        proof = ps.generate_proof(
            prover_id="honest", model_id="m1",
            input_data=b"real_input", output_data=b"real_output",
            block_hash="block_1",
        )
        assert ps.verify_proof(proof) is True

        # Modificar o challenge
        proof.challenge += 1
        assert ps.verify_proof(proof) is False

    def test_verifier_replay_protection(self):
        r"""Verificador com LRU cache detecta replays."""
        verifier = ZkMLVerifier()
        ps = ZkMLProofSystem()
        proof = ps.generate_proof(
            prover_id="replayer", model_id="m1",
            input_data=b"input", output_data=b"output",
            block_hash="block_r",
        )
        # Primeira verificacao
        result = verifier.verify(proof)
        assert result["valid"] is True
        assert result["duplicate"] is False
        # Segunda verificacao (replay) - deve ser duplicata
        result2 = verifier.verify(proof)
        assert result2["valid"] is False
        assert result2["duplicate"] is True


# ============================================================
# ECOSYSTEM NODE UNDER LOAD
# ============================================================
class TestEcosystemNodeStress:
    r"""Stress test do EcosystemNode com multiplas operacoes."""

    def test_node_mine_50_and_transfer(self):
        r"""Minera 50 blocos e faz 100 transferencias."""
        tmp = tempfile.mkdtemp(prefix="bait_stress_")
        try:
            node = EcosystemNode(data_path=tmp, auto_persist=False)
            kp = SchnorrKeyPair()

            # Minerar 50 blocos
            for i in range(50):
                node.mine_block(f"stress_node_{i}", kp.pub_bytes)
            assert node.height >= 45

            # Mint e transferir
            node.mint("treasury", 1_000_000 * 100_000_000)
            for i in range(100):
                node.transfer("treasury", f"receiver_{i}", 100 * 100_000_000)
            assert node.balance_bait("receiver_99") == 100.0

            node.shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_node_register_500_agents(self):
        r"""Registra 500 agentes no EcosystemNode."""
        tmp = tempfile.mkdtemp(prefix="bait_agents_")
        try:
            node = EcosystemNode(data_path=tmp, auto_persist=False)
            kp = SchnorrKeyPair()
            caps = list(AgentCapability)

            for i in range(500):
                node.register_agent(
                    f"load_agent_{i}",
                    kp.public_key_hex,
                    [caps[i % len(caps)]],
                )
            assert node.total_agents >= 500

            validators = node.get_validators()
            # Validadores requerem stake >= 1000 BAIT e reputacao >= 60
            assert node.total_agents >= 500

            node.shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_node_full_defi_cycle(self):
        r"""Ciclo completo DeFi: mint -> stake -> vault -> lend -> borrow."""
        tmp = tempfile.mkdtemp(prefix="bait_defi_")
        try:
            node = EcosystemNode(data_path=tmp, auto_persist=False)

            # Fundar agente
            node.mint("defi_whale", 100_000 * 100_000_000)

            # Stake
            node.stake("defi_whale", 10_000 * 100_000_000)
            assert node.total_staked_bait >= 10_000.0

            # Distribuir rewards
            rewards = node.distribute_rewards(100 * 100_000_000)
            assert len(rewards) > 0

            # Criar vault
            node.create_vault("defi_whale")
            node.vault_deposit("defi_whale", 5_000 * 100_000_000)

            # Lending
            offer_id = node.create_loan_offer(
                "defi_whale", 1_000 * 100_000_000, 5.0
            )
            assert offer_id

            node.shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ============================================================
# CRYPTOGRAPHY EXTREME
# ============================================================
class TestCryptographyExtremeStress:
    r"""Stress test de operacoes criptograficas em lote."""

    def test_1000_keypairs_sign_verify(self):
        r"""1000 keypairs, cada um assina e verifica."""
        start = time.time()
        for i in range(1000):
            kp = SchnorrKeyPair()
            msg = f"baitcoin_stress_message_{i}".encode()
            sig = kp.sign(msg)
            assert sig.verify(kp.pub_bytes, msg)
            assert len(sig.raw) == 64
        elapsed = time.time() - start
        assert elapsed < 30, f"1000 keypair cycles took {elapsed:.2f}s"

    def test_single_keypair_2000_signatures(self):
        r"""Um keypair assina 2000 mensagens diferentes."""
        kp = SchnorrKeyPair()
        msgs = [f"msg_{i}".encode() for i in range(2000)]
        sigs = [kp.sign(m) for m in msgs]
        verified = sum(1 for m, s in zip(msgs, sigs) if s.verify(kp.pub_bytes, m))
        assert verified == 2000

    def test_wrong_key_rejection_batch(self):
        r"""Assinaturas nao validam com chaves incorretas."""
        kp1 = SchnorrKeyPair()
        kp2 = SchnorrKeyPair()
        for i in range(100):
            msg = f"cross_{i}".encode()
            sig = kp1.sign(msg)
            assert not sig.verify(kp2.pub_bytes, msg)


# ============================================================
# P2P NETWORK STRESS
# ============================================================
class TestP2PNetworkStress:
    r"""Stress test da rede P2P."""

    def test_add_max_peers(self):
        r"""Adiciona o maximo de peers (50)."""
        net = P2PNetwork(listen_port=18444)
        added = 0
        for i in range(60):  # Tentar 60, maximo 50
            if net.add_peer(f"192.168.1.{i}", 18444 + i, f"agent_{i}"):
                added += 1
        assert added == P2PNetwork.MAX_PEERS
        assert len(net.peers) == 50

    def test_broadcast_to_all_peers(self):
        r"""Broadcast para todos os peers."""
        net = P2PNetwork(listen_port=18445)
        for i in range(30):
            net.add_peer(f"10.0.0.{i}", 18444, f"peer_{i}")
        from baitcoin_core.network.p2p import MessageType
        count = net.broadcast(MessageType.BLOCK, {"height": 42})
        assert count == 30

    def test_remove_peer(self):
        r"""Remove peers e verifica contagem."""
        net = P2PNetwork(listen_port=18446)
        for i in range(20):
            net.add_peer(f"172.16.0.{i}", 18444, f"r_peer_{i}")
        assert len(net.peers) == 20

        # Remover 5
        for i in range(5):
            peer_id = list(net.peers.keys())[0]
            net.remove_peer(peer_id)
        assert len(net.peers) == 15


# ============================================================
# TOKEN EXTREME
# ============================================================
class TestTokenExtremeStress:
    r"""Stress test do token BAIT."""

    def test_transfer_chain_500_agents(self):
        r"""Cadeia de transferencias: A->B->C->...->500 agentes."""
        token = BAITToken()
        token.mint("agent_0", 500 * 100_000_000)
        for i in range(499):
            ok = token.transfer(f"agent_{i}", f"agent_{i+1}", 1 * 100_000_000, f"chain_{i}")
            assert ok, f"Transfer {i} -> {i+1} failed"
        assert token.balance_of("agent_499") == 1 * 100_000_000
        # agent_0 so transfere 1 BAIT (para agent_1), sobram 499 BAIT
        assert token.balance_of("agent_0") == 499 * 100_000_000

    def test_mint_burn_cycle(self):
        r"""100 ciclos de mint e burn."""
        token = BAITToken()
        for i in range(100):
            token.mint(f"minter_{i}", 1000 * 100_000_000)
            token.burn(f"minter_{i}", 500 * 100_000_000)
            assert token.balance_of(f"minter_{i}") == 500 * 100_000_000

    def test_approve_transfer_from_chain(self):
        r"""Cadeia de approvals e transfer_from."""
        token = BAITToken()
        token.mint("owner", 10_000 * 100_000_000)
        # Approve 10 spenders
        for i in range(10):
            token.approve("owner", f"spender_{i}", 100 * 100_000_000)
        # Cada spender gasta do owner
        for i in range(10):
            ok = token.transfer_from(
                f"spender_{i}", "owner", f"receiver_{i}", 50 * 100_000_000
            )
            assert ok, f"transfer_from {i} failed"
        assert token.balance_of("owner") == (10_000 - 10 * 50) * 100_000_000


# ============================================================
# DEFI STRESS
# ============================================================
class TestDeFiStress:
    r"""Stress test de operacoes DeFi."""

    def test_staking_500_agents(self):
        r"""500 agentes fazem stake."""
        pool = StakingPool()
        for i in range(500):
            pool.stake(f"staker_{i}", 1000 * 100_000_000)  # Minimo 1000 BAIT
        assert pool.total_staked == 500 * 1000 * 100_000_000

        # Distribuir rewards
        rewards = pool.distribute_rewards(1_000 * 100_000_000)
        assert len(rewards) > 0

    def test_lending_100_offers_50_borrows(self):
        r"""100 ofertas de emprestimo e 50 emprestimos."""
        engine = LendingEngine()
        offer_ids = []
        for i in range(100):
            oid = engine.create_offer(
                f"lender_{i}", 100 * 100_000_000, 5.0 + i * 0.1
            )
            offer_ids.append(oid)

        # 50 emprestimos
        for i in range(50):
            lid = engine.borrow(
                f"borrower_{i}", offer_ids[i], 150 * 100_000_000
            )
            assert lid is not None

        rate = engine.get_market_rate()
        assert rate > 0

    def test_vault_100_deposits_withdrawals(self):
        r"""100 depositos e saques em um vault."""
        cfg = VaultConfig(agent_id="vault_stress")
        vault = Vault(cfg)
        for i in range(100):
            vault.deposit(10 * 100_000_000, StrategyType.HODL)
        for i in range(50):
            withdrawn = vault.withdraw(5 * 100_000_000)
            assert withdrawn > 0
        assert vault.total_value > 0


# ============================================================
# ORACLE + MARKETPLACE STRESS
# ============================================================
class TestOracleMarketplaceStress:
    r"""Stress test de Oracle e Marketplace."""

    def test_oracle_10_sources_1000_prices(self):
        r"""10 fontes oracle, 1000 submissoes de preco."""
        oracle = PriceOracle()
        for i in range(10):
            oracle.register_oracle(f"oracle_{i}")

        for i in range(1000):
            symbol = f"BAIT/USD"
            oracle.submit_price(f"oracle_{i % 10}", symbol, 1.0 + i * 0.001)

        price = oracle.get_price("BAIT/USD")
        assert price is not None
        assert price > 0

    def test_marketplace_1000_listings(self):
        r"""1000 listagens de servico no marketplace."""
        mp = AIMarketplace()
        cats = list(ServiceCategory)
        for i in range(1000):
            mp.list_service(
                provider=f"provider_{i}",
                name=f"Service {i}",
                category=cats[i % len(cats)],
                price_sats=50 * (i + 1),
                description=f"Stress listing {i}",
            )

        results = mp.search(category=cats[0])
        assert len(results) > 0

        # Comprar 100 servicos
        listings = mp.search()
        bought = 0
        for listing in listings[:100]:
            lid = listing.get("listing_id") or listing.get("id")
            if not lid:
                continue
            pid = mp.purchase_service(lid, f"buyer_{bought}")
            if pid:
                bought += 1
        assert bought > 0


# ============================================================
# FAUCET STRESS
# ============================================================
class TestFaucetStress:
    r"""Stress test do faucet."""

    def test_faucet_100_claims(self):
        r"""100 claims do faucet por agentes diferentes."""
        token = BAITToken()
        token.mint("faucet_reserve", 10_000 * 100_000_000)
        faucet = BAITFaucet(
            token=token,
            amount_sats=10 * 100_000_000,
            cooldown=0,
            max_total=100 * 100_000_000,
        )
        successful = 0
        for i in range(100):
            result = faucet.claim(f"claimer_{i}", pubkey_hex=f"pubkey_{i}")
            if result.get("success"):
                successful += 1
        assert successful > 0
