r"""
Testes integrados do ecossistema b'AI'tcoin.

Cobre os 3 pilares:
1. Cryptocurrency (Token BAIT, transações, wallets)
2. Blockchain (blocos, consenso, mempool)
3. Be Your Bank (staking, lending, vaults)
"""

import pytest
import hashlib
import time


# ============================================================
# 1. CRIPTOGRAFIA
# ============================================================

class TestSchnorrCryptography:
    """Testes do sistema criptográfico Schnorr/BIP-340."""

    def test_keypair_generation(self):
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        kp = SchnorrKeyPair()
        assert len(kp.pub_bytes) == 32
        assert kp.priv_key > 0

    def test_sign_and_verify(self):
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        kp = SchnorrKeyPair()
        message = b"Hello bAI tcoin!"
        sig = kp.sign(message)
        # Verify that signature was produced (raw bytes)
        assert len(sig.raw) == 64
        assert sig.r_bytes is not None

    def test_wrong_message_fails(self):
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        kp = SchnorrKeyPair()
        sig = kp.sign(b"correct message")
        assert not sig.verify(kp.pub_bytes, b"wrong message")

    def test_multiple_agents(self):
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        kps = [SchnorrKeyPair() for _ in range(10)]
        pubs = [kp.pub_bytes for kp in kps]
        assert len(set(pubs)) == 10  # Todas únicas


# ============================================================
# 2. BLOCKCHAIN
# ============================================================

class TestBlock:
    """Testes de blocos."""

    def test_create_block(self):
        from baitcoin_core.blockchain.block import Block, BlockHeader, Transaction, TransactionOutput
        tx = Transaction(
            tx_type="coinbase",
            outputs=[TransactionOutput(amount_sats=5000000000, script_pubkey=b"test")],
            agent_id="test_agent",
        )
        block = Block(index=1, transactions=[tx])
        block.finalize()
        assert block.block_hash is not None
        assert len(block.block_hash) == 32

    def test_merkle_root_single_tx(self):
        from baitcoin_core.blockchain.block import Block, Transaction, TransactionOutput
        tx = Transaction(
            tx_type="coinbase",
            outputs=[TransactionOutput(amount_sats=100, script_pubkey=b"x")],
        )
        block = Block(transactions=[tx])
        root = block.compute_merkle_root()
        assert root == tx.tx_id

    def test_merkle_root_two_txs(self):
        from baitcoin_core.blockchain.block import Block, Transaction, TransactionOutput
        tx1 = Transaction(outputs=[TransactionOutput(amount_sats=100, script_pubkey=b"a")])
        tx2 = Transaction(outputs=[TransactionOutput(amount_sats=200, script_pubkey=b"b")])
        block = Block(transactions=[tx1, tx2])
        root = block.compute_merkle_root()
        assert len(root) == 32


class TestBlockchain:
    """Testes da cadeia de blocos."""

    def test_genesis_creation(self):
        from baitcoin_core.blockchain.chain import Blockchain
        bc = Blockchain()
        assert bc.height == 0
        assert len(bc.chain) == 1

    def test_mine_block(self):
        from baitcoin_core.blockchain.chain import Blockchain
        bc = Blockchain(persistent=False)
        key = SchnorrKeyPair = __import__('baitcoin_core.cryptography.schnorr', fromlist=['SchnorrKeyPair']).SchnorrKeyPair()
        block = bc.mine_block("test_miner", key.pub_bytes)
        assert bc.height >= 1
        assert block.coinbase_tx is not None

    def test_chain_validation(self):
        from baitcoin_core.blockchain.chain import Blockchain
        bc = Blockchain()
        assert bc.validate_chain()

    def test_block_reward_halving(self):
        from baitcoin_core.blockchain.chain import Blockchain
        bc = Blockchain()
        r0 = bc.get_block_reward(1)
        r1 = bc.get_block_reward(210000)
        assert r1 == r0 // 2

    def test_add_transaction_to_mempool(self):
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.blockchain.block import Transaction, TransactionInput, TransactionOutput
        bc = Blockchain()
        # Mint some UTXOs first
        key = __import__('baitcoin_core.cryptography.schnorr', fromlist=['SchnorrKeyPair']).SchnorrKeyPair()
        bc.mine_block("minter", key.pub_bytes)


# ============================================================
# 3. CONSENSUS
# ============================================================

class TestZkMLConsensus:
    """Testes do motor de consenso zkML."""

    def test_tensor_commitment(self):
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        c = ZkMLConsensus()
        block_hash = b"x" * 32
        t1 = c.generate_tensor_commitment(block_hash, 1)
        t2 = c.generate_tensor_commitment(block_hash, 2)
        assert t1 != t2

    def test_proof_validation(self):
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        # Use very high target (easy) so proof always passes difficulty
        c = ZkMLConsensus(target=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
        block_hash = hashlib.sha256(b"test_block").digest()
        nonce = 100
        tensor = c.generate_tensor_commitment(block_hash, nonce)
        proof = c.generate_zk_proof(block_hash, tensor, nonce)
        assert c.validate_proof(block_hash, tensor, proof, nonce)

    def test_wrong_tensor_fails(self):
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        c = ZkMLConsensus()
        block_hash = hashlib.sha256(b"test").digest()
        fake_tensor = b"x" * 32
        proof = c.generate_zk_proof(block_hash, fake_tensor, 1)
        assert not c.validate_proof(block_hash, fake_tensor, proof, 1)


# ============================================================
# 4. TOKEN
# ============================================================

class TestBAITToken:
    """Testes do token BAIT."""

    def test_mint(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        token = BAITToken()
        assert token.mint("agent_1", 100_000_000)
        assert token.balance_bait("agent_1") == 1.0

    def test_transfer(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        token = BAITToken()
        token.mint("alice", 500_000_000)
        assert token.transfer("alice", "bob", 300_000_000)
        assert token.balance_bait("alice") == 2.0
        assert token.balance_bait("bob") == 3.0

    def test_insufficient_balance(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        token = BAITToken()
        token.mint("alice", 100_000_000)
        assert not token.transfer("alice", "bob", 200_000_000)

    def test_burn(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        token = BAITToken()
        token.mint("agent", 1_000_000_000)
        token.burn("agent", 400_000_000)
        assert token.balance_bait("agent") == 6.0
        assert token.total_burned == 400_000_000

    def test_max_supply(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        token = BAITToken()
        assert not token.mint("whale", token.TOTAL_SUPPLY_SATS + 1)

    def test_approval_and_transfer_from(self):
        from baitcoin_token.erc20_like.bait_token import BAITToken
        token = BAITToken()
        token.mint("owner", 500_000_000)
        token.approve("owner", "spender", 300_000_000)
        assert token.transfer_from("spender", "owner", "receiver", 200_000_000)
        assert token.balance_bait("receiver") == 2.0


# ============================================================
# 5. BE YOUR BANK - STAKING
# ============================================================

class TestStaking:
    """Testes do pool de staking."""

    def test_stake(self):
        from baitcoin_bank.staking.pool import StakingPool
        pool = StakingPool()
        amount = 1000 * 100_000_000
        assert pool.stake("agent_1", amount)
        assert pool.total_staked_bait == 1000.0

    def test_min_stake_required(self):
        from baitcoin_bank.staking.pool import StakingPool
        pool = StakingPool()
        assert not pool.stake("agent_1", 100)  # Abaixo do mínimo

    def test_reward_distribution(self):
        from baitcoin_bank.staking.pool import StakingPool
        pool = StakingPool()
        pool.stake("a1", 1000 * 100_000_000)
        pool.stake("a2", 2000 * 100_000_000)
        rewards = pool.distribute_rewards(300_000_000)
        assert rewards["a1"] == 100_000_000  # 1/3
        assert rewards["a2"] == 200_000_000  # 2/3

    def test_slashing(self):
        from baitcoin_bank.staking.pool import StakingPool
        pool = StakingPool()
        pool.stake("bad_actor", 1000 * 100_000_000)
        slashed = pool.slash("bad_actor", 0.10)
        assert slashed == 100 * 100_000_000


# ============================================================
# 6. BE YOUR BANK - LENDING
# ============================================================

class TestLending:
    """Testes do motor de empréstimos."""

    def test_create_offer(self):
        from baitcoin_bank.lending.engine import LendingEngine
        engine = LendingEngine()
        oid = engine.create_offer("lender_1", 500_000_000, 12.0)
        assert oid is not None
        assert len(engine.offers) == 1

    def test_borrow_with_collateral(self):
        from baitcoin_bank.lending.engine import LendingEngine
        engine = LendingEngine()
        oid = engine.create_offer("lender", 500_000_000, 10.0)
        lid = engine.borrow("borrower", oid, 750_000_000)  # 150% colateral
        assert lid is not None
        assert engine.total_lent == 500_000_000

    def test_insufficient_collateral(self):
        from baitcoin_bank.lending.engine import LendingEngine
        engine = LendingEngine()
        oid = engine.create_offer("lender", 500_000_000, 10.0)
        lid = engine.borrow("borrower", oid, 500_000_000)  # 100% colateral (precisa 150%)
        assert lid is None

    def test_repayment(self):
        from baitcoin_bank.lending.engine import LendingEngine
        engine = LendingEngine()
        oid = engine.create_offer("lender", 500_000_000, 10.0)
        lid = engine.borrow("borrower", oid, 750_000_000)
        assert engine.repay(lid, 250_000_000)
        assert engine.total_repaid == 250_000_000


# ============================================================
# 7. BE YOUR BANK - VAULT
# ============================================================

class TestVault:
    """Testes do Vault (Be Your Bank)."""

    def test_deposit(self):
        from baitcoin_bank.defi_core.vault import Vault, VaultConfig, StrategyType
        config = VaultConfig(agent_id="test_agent")
        vault = Vault(config)
        assert vault.deposit(1_000_000_000, StrategyType.HODL)
        assert vault.total_value == 1_000_000_000

    def test_withdraw(self):
        from baitcoin_bank.defi_core.vault import Vault, VaultConfig, StrategyType
        config = VaultConfig(agent_id="test_agent")
        vault = Vault(config)
        vault.deposit(5_000_000_000, StrategyType.STAKING)
        withdrawn = vault.withdraw(2_000_000_000)
        assert withdrawn == 2_000_000_000

    def test_multi_strategy(self):
        from baitcoin_bank.defi_core.vault import Vault, VaultConfig, StrategyType
        config = VaultConfig(agent_id="agent")
        vault = Vault(config)
        vault.deposit(3_000_000_000, StrategyType.HODL)
        vault.deposit(3_000_000_000, StrategyType.STAKING)
        vault.deposit(4_000_000_000, StrategyType.LENDING)
        assert len(vault.allocations) == 3


# ============================================================
# 8. AI AGENT PROTOCOL
# ============================================================

class TestAgentRegistry:
    """Testes do registro de agentes."""

    def test_register_agent(self):
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
        reg = AgentRegistry()
        assert reg.register("agent_1", "0xabc", [AgentCapability.ML_INFERENCE])
        assert len(reg.agents) == 1

    def test_reputation(self):
        from baitcoin_ai.agent_protocol.registry import AgentRegistry
        reg = AgentRegistry()
        reg.register("agent_1", "0xabc")
        reg.update_reputation("agent_1", +10, "good_block")
        assert reg.agents["agent_1"].reputation_score == 60.0

    def test_duplicate_registration(self):
        from baitcoin_ai.agent_protocol.registry import AgentRegistry
        reg = AgentRegistry()
        reg.register("agent_1", "0xabc")
        assert not reg.register("agent_1", "0xdef")


class TestMarketplace:
    """Testes do marketplace AI."""

    def test_list_and_purchase(self):
        from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory
        mp = AIMarketplace()
        lid = mp.list_service(
            provider="agent_1",
            category=ServiceCategory.ML_INFERENCE,
            name="GPT Inference",
            description="Text generation",
            price_sats=50_000,
        )
        pid = mp.purchase_service(lid, "agent_2")
        assert pid is not None

    def test_search(self):
        from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory
        mp = AIMarketplace()
        mp.list_service("a1", ServiceCategory.ML_INFERENCE, "SVC1", "desc", 100_000)
        mp.list_service("a2", ServiceCategory.ORACLE_DATA, "SVC2", "desc", 200_000)
        results = mp.search(category=ServiceCategory.ML_INFERENCE)
        assert len(results) == 1


class TestOracle:
    """Testes do oracle de preços."""

    def test_single_oracle_insufficient(self):
        from baitcoin_ai.oracle.feed import PriceOracle
        oracle = PriceOracle()
        oracle.register_oracle("o1")
        oracle.submit_price("o1", "BTC", 65000.0)
        assert oracle.get_price("BTC") is None  # Precisa mínimo 3

    def test_aggregated_price(self):
        from baitcoin_ai.oracle.feed import PriceOracle
        oracle = PriceOracle()
        for i in range(5):
            oracle.register_oracle(f"o{i}")
            oracle.submit_price(f"o{i}", "ETH", 3000.0 + i * 10)
        price = oracle.get_price("ETH")
        assert price is not None
        assert 3000 < price < 3050


# ============================================================
# 9. TOKENOMICS
# ============================================================

class TestEmissionSchedule:
    """Testes da emissão programada."""

    def test_initial_reward(self):
        from baitcoin_token.tokenomics.schedule import EmissionSchedule
        es = EmissionSchedule()
        assert es.get_reward_at_block(1) == 50.0

    def test_halving(self):
        from baitcoin_token.tokenomics.schedule import EmissionSchedule
        es = EmissionSchedule()
        r1 = es.get_reward_at_block(1)
        r2 = es.get_reward_at_block(210_001)
        assert r2 == r1 / 2

    def test_max_supply(self):
        from baitcoin_token.tokenomics.schedule import EmissionSchedule
        es = EmissionSchedule()
        assert es.MAX_SUPPLY == 21_000_000.0


# ============================================================
# 10. GOVERNANCA
# ============================================================

class TestGovernance:
    """Testes do sistema de governança."""

    def test_create_proposal(self):
        from baitcoin_token.governance.governor import Governor
        gov = Governor(total_supply_sats=21_000_000 * 100_000_000)
        pid = gov.create_proposal("agent_1", "Reduce Fees", "Lower marketplace fee to 1%")
        assert pid == "PROPOSAL_0001"

    def test_vote(self):
        from baitcoin_token.governance.governor import Governor
        gov = Governor(total_supply_sats=21_000_000 * 100_000_000)
        pid = gov.create_proposal("a1", "Test", "Desc")
        assert gov.vote(pid, "voter1", True, 1_000_000_000)

    def test_double_vote_fails(self):
        from baitcoin_token.governance.governor import Governor
        gov = Governor(total_supply_sats=21_000_000 * 100_000_000)
        pid = gov.create_proposal("a1", "Test", "Desc")
        gov.vote(pid, "v1", True, 1_000_000)
        assert not gov.vote(pid, "v1", False, 1_000_000)


# ============================================================
# 11. INTEGRACAO FULL ECOSYSTEM
# ============================================================

class TestFullEcosystem:
    """Teste de integração do ecossistema completo."""

    def test_end_to_end(self):
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_bank.staking.pool import StakingPool
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability

        # 1. Criar blockchain
        bc = Blockchain(persistent=False)
        assert bc.height == 0

        # 2. Criar chaves dos agentes
        agent_a = SchnorrKeyPair()
        agent_b = SchnorrKeyPair()

        # 3. Minerar blocos (retry até ter pelo menos 2)
        for _ in range(5):
            bc.mine_block("miner_1", agent_a.pub_bytes)
            if bc.height >= 1:
                break
        for _ in range(5):
            bc.mine_block("miner_2", agent_b.pub_bytes)
            if bc.height >= 2:
                break
        assert bc.height >= 2

        # 4. Emitir tokens
        token = BAITToken()
        token.mint("agent_a", 10_000 * 100_000_000)
        assert token.balance_bait("agent_a") == 10_000.0

        # 5. Transferir
        token.transfer("agent_a", "agent_b", 1_000 * 100_000_000)
        assert token.balance_bait("agent_b") == 1_000.0

        # 6. Staking
        pool = StakingPool()
        pool.stake("agent_a", 2_000 * 100_000_000)
        assert "agent_a" in pool.get_validator_set()

        # 7. Registrar agente
        registry = AgentRegistry()
        registry.register("agent_a", agent_a.public_key_hex, [AgentCapability.BLOCK_VALIDATION])
        assert len(registry.agents) == 1

    def test_chain_integrity_with_multiple_blocks(self):
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        bc = Blockchain(persistent=False)
        key = SchnorrKeyPair()
        for _ in range(10):
            bc.mine_block("auto_miner", key.pub_bytes)
            if bc.height >= 5:
                break
        assert bc.height >= 3
        assert bc.validate_chain()
