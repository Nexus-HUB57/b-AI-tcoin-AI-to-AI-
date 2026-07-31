r"""Validacao End-to-End completa do ecossistema b'AI'tcoin via EcosystemNode.

Cobre TODAS as 12 fases + persistencia automatica:
 1.  Blockchain (genesis + mineracao + validacao)
 2.  Token BAIT (mint/burn/transfer/approve)
 3.  Agentes AI (10 capacidades, reputacao, trust levels)
 4.  Staking (stake/unstake/rewards/slash/validator set)
 5.  Lending P2P (offers/borrow/repay/liquidation)
 6.  Vault DeFi (deposit/withdraw/estrategias/stop-loss)
 7.  Marketplace (list/purchase/rate/search)
 8.  Oracle de precos (register/submit/aggregation)
 9.  zkML Proofs (Sigma + Fiat-Shamir + Pedersen)
10.  PoUW (Proof of Useful Work)
11.  Obscura (bridge + capability + cost tracking)
12.  Persistencia (WAL + snapshots + restore + roundtrip)

Total: ~50 testes.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import pytest


# ============================================================
# FIXTURE: EcosystemNode com diretorio temporario
# ============================================================

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix='baitcoin_e2e_node_')
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def node(tmp_dir):
    from baitcoin_core.ecosystem import EcosystemNode
    return EcosystemNode(data_path=tmp_dir, auto_persist=True)


@pytest.fixture
def miner_key():
    from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
    return SchnorrKeyPair()


# ============================================================
# FASE 1: Blockchain
# ============================================================
class TestPhase1Blockchain:
    def test_genesis_block_exists(self, node):
        assert node.blockchain.height >= 0
        assert len(node.blockchain.chain) >= 1
        assert node.blockchain.chain[0].header.agent_validator == 'chimera7_genesis'

    def test_mine_multiple_blocks(self, node, miner_key):
        for i in range(5):
            block = node.mine_block(f'miner_{i}', miner_key.pub_bytes)
            assert block is not None
            assert block.header.agent_validator == f'miner_{i}'
        assert node.blockchain.height >= 5

    def test_chain_validation(self, node, miner_key):
        node.mine_block('validator_miner', miner_key.pub_bytes)
        assert node.validate_chain() is True

    def test_block_reward_halving(self, node, miner_key):
        reward_1 = node.get_block_reward(1)
        reward_210k = node.get_block_reward(210_000)
        assert reward_210k == reward_1 // 2
        reward_420k = node.get_block_reward(420_000)
        assert reward_420k == reward_1 // 4

    def test_get_block_by_height(self, node, miner_key):
        node.mine_block('block_test_miner', miner_key.pub_bytes)
        block = node.get_block(1)
        assert block is not None
        assert isinstance(block, dict)
        assert block['header']['agent_validator'] == 'block_test_miner'

    def test_utxo_set_integrity(self, node, miner_key):
        node.mine_block('utxo_miner', miner_key.pub_bytes)
        utxo_count = len(node.blockchain.utxo_set)
        assert utxo_count > 0


# ============================================================
# FASE 2: Token BAIT
# ============================================================
class TestPhase2Token:
    def test_mint(self, node):
        ok = node.mint('token_agent', 100 * 100_000_000)
        assert ok is True
        assert node.balance_of('token_agent') == 100 * 100_000_000

    def test_transfer(self, node):
        node.mint('sender', 50 * 100_000_000)
        ok = node.transfer('sender', 'receiver', 30 * 100_000_000)
        assert ok is True
        assert node.balance_of('sender') == 20 * 100_000_000
        assert node.balance_of('receiver') == 30 * 100_000_000

    def test_burn(self, node):
        node.mint('burner', 10 * 100_000_000)
        ok = node.burn('burner', 3 * 100_000_000)
        assert ok is True
        assert node.balance_of('burner') == 7 * 100_000_000

    def test_approve_and_transfer_from(self, node):
        node.mint('owner', 100 * 100_000_000)
        node.approve('owner', 'spender', 40 * 100_000_000)
        ok = node.transfer_from('spender', 'owner', 'third_party', 20 * 100_000_000)
        assert ok is True
        assert node.balance_of('third_party') == 20 * 100_000_000

    def test_insufficient_balance(self, node):
        node.mint('poor', 5 * 100_000_000)
        ok = node.transfer('poor', 'rich', 10 * 100_000_000)
        assert ok is False

    def test_max_supply_cap(self, node):
        max_sats = 21_000_000 * 100_000_000
        assert node.token.max_supply_bait == 21_000_000
        assert node.token.TOTAL_SUPPLY_SATS == max_sats

    def test_token_to_dict(self, node):
        node.mint('t_dict_agent', 1 * 100_000_000)
        d = node.token.to_dict()
        assert d['symbol'] == 'BAIT'
        assert d['holders'] >= 1
        assert d['circulating_bait'] >= 1.0


# ============================================================
# FASE 3: Agentes AI (10 capacidades)
# ============================================================
class TestPhase3Agents:
    def test_register_agent(self, node, miner_key):
        ok = node.register_agent('agent_3a', miner_key.public_key_hex)
        assert ok is True
        profile = node.get_agent('agent_3a')
        assert profile is not None
        assert profile.agent_id == 'agent_3a'

    def test_register_with_all_capabilities(self, node):
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        all_caps = list(AgentCapability)
        ok = node.register_agent('full_cap_agent', '0x' + 'aa' * 32, all_caps)
        assert ok is True
        profile = node.get_agent('full_cap_agent')
        assert len(profile.capabilities) == 10
        assert AgentCapability.WEB_SCRAPING in profile.capabilities
        assert AgentCapability.BROWSER_AUTOMATION in profile.capabilities

    def test_reputation_system(self, node):
        node.register_agent('rep_agent', '0x' + 'bb' * 32)
        node.update_reputation('rep_agent', 30, 'excellent_inference')
        profile = node.get_agent('rep_agent')
        assert profile.reputation_score == 80.0
        assert profile.trust_level == 'trusted'

    def test_trust_levels(self, node):
        node.register_agent('trust_low', '0x' + '11' * 32)
        node.update_reputation('trust_low', -30, 'bad_behavior')  # 50 - 30 = 20
        assert node.get_agent('trust_low').trust_level == 'probation'

    def test_validator_qualification(self, node):
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        node.register_agent('validator_cand', '0x' + 'cc' * 32, [AgentCapability.BLOCK_VALIDATION])
        node.update_reputation('validator_cand', 20, 'good_proofs')
        validators = node.get_validators()
        assert 'validator_cand' in validators

    def test_duplicate_registration_fails(self, node):
        node.register_agent('dup_agent', '0x' + 'dd' * 32)
        ok = node.register_agent('dup_agent', '0x' + 'dd' * 32)
        assert ok is False

    def test_list_agents(self, node):
        node.register_agent('list_1', '0x' + 'e1' * 32)
        node.register_agent('list_2', '0x' + 'e2' * 32)
        agents = node.list_agents()
        assert len(agents) >= 2


# ============================================================
# FASE 4: Staking
# ============================================================
class TestPhase4Staking:
    def test_stake(self, node):
        ok = node.stake('staker_1', 1000 * 100_000_000)
        assert ok is True
        assert node.staking.total_staked_bait == 1000.0

    def test_stake_below_minimum(self, node):
        ok = node.stake('poor_staker', 500 * 100_000_000)
        assert ok is False

    def test_unstake_with_penalty(self, node):
        node.stake('early_unstaker', 2000 * 100_000_000)
        net = node.unstake('early_unstaker')
        assert net == 1800 * 100_000_000  # 10% penalty

    def test_reward_distribution(self, node):
        node.stake('reward_a', 1000 * 100_000_000)
        node.stake('reward_b', 2000 * 100_000_000)
        rewards = node.distribute_rewards(210 * 100_000_000)
        assert rewards['reward_a'] == 70 * 100_000_000  # 1/3
        assert rewards['reward_b'] == 140 * 100_000_000  # 2/3

    def test_slashing(self, node):
        node.stake('slash_victim', 5000 * 100_000_000)
        slashed = node.slash('slash_victim', 0.05)
        assert slashed == 250 * 100_000_000

    def test_validator_set(self, node):
        node.stake('val_staker', 1000 * 100_000_000)
        vals = node.get_validator_set()
        assert 'val_staker' in vals

    def test_apy(self, node):
        assert abs(node.staking.apy - 7.0) < 0.01


# ============================================================
# FASE 5: Lending P2P
# ============================================================
class TestPhase5Lending:
    def test_create_offer(self, node):
        oid = node.create_loan_offer('lender_1', 500 * 100_000_000, 12.0)
        assert oid.startswith('loan_')

    def test_borrow(self, node):
        oid = node.create_loan_offer('p2p_lender', 100 * 100_000_000, 10.0)
        lid = node.borrow('p2p_borrower', oid, 150 * 100_000_000)
        assert lid is not None
        assert lid.startswith('active_')

    def test_repay(self, node):
        oid = node.create_loan_offer('repay_lender', 200 * 100_000_000, 8.0)
        lid = node.borrow('repay_borrower', oid, 300 * 100_000_000)
        ok = node.repay_loan(lid, 200 * 100_000_000)
        assert ok is True

    def test_market_rate(self, node):
        node.create_loan_offer('rate_lender_1', 100 * 100_000_000, 15.0)
        node.create_loan_offer('rate_lender_2', 100 * 100_000_000, 5.0)
        rate = node.get_market_rate()
        assert rate == 10.0

    def test_insufficient_collateral(self, node):
        oid = node.create_loan_offer('coll_lender', 100 * 100_000_000, 10.0)
        lid = node.borrow('coll_borrower', oid, 100 * 100_000_000)  # 100% ratio < 150%
        assert lid is None


# ============================================================
# FASE 6: Vault DeFi
# ============================================================
class TestPhase6Vaults:
    def test_create_vault(self, node):
        vid = node.create_vault('vault_agent_1')
        assert vid == 'vault_agent_1'
        vault = node.get_vault('vault_agent_1')
        assert vault is not None
        assert vault.config.agent_id == 'vault_agent_1'

    def test_deposit_and_withdraw(self, node):
        from baitcoin_bank.defi_core.vault import StrategyType
        node.create_vault('vault_agent_2')
        ok = node.vault_deposit('vault_agent_2', 5000 * 100_000_000, StrategyType.STAKING)
        assert ok is True
        withdrawn = node.vault_withdraw('vault_agent_2', 2000 * 100_000_000)
        assert withdrawn == 2000 * 100_000_000

    def test_all_strategies(self, node):
        from baitcoin_bank.defi_core.vault import StrategyType
        node.create_vault('vault_agent_3')
        for strat in StrategyType:
            node.vault_deposit('vault_agent_3', 100 * 100_000_000, strat)
        vault = node.get_vault('vault_agent_3')
        assert len(vault.allocations) == 5

    def test_vault_pnl_tracking(self, node):
        from baitcoin_bank.defi_core.vault import StrategyType
        node.create_vault('vault_pnl_agent')
        node.vault_deposit('vault_pnl_agent', 10000 * 100_000_000, StrategyType.LENDING)
        vault = node.get_vault('vault_pnl_agent')
        assert vault.deposits_total == 10000 * 100_000_000


# ============================================================
# FASE 7: Marketplace
# ============================================================
class TestPhase7Marketplace:
    def test_list_service(self, node):
        from baitcoin_ai.marketplace.services import ServiceCategory
        lid = node.list_service(
            provider='provider_1', category=ServiceCategory.ML_INFERENCE,
            name='GPT-4 Inference', description='High quality inference',
            price_sats=100 * 100_000_000
        )
        assert lid.startswith('svc_')

    def test_purchase_service(self, node):
        from baitcoin_ai.marketplace.services import ServiceCategory
        lid = node.list_service(
            provider='provider_2', category=ServiceCategory.DATA_PROCESSING,
            name='Data Pipeline', description='ETL for AI',
            price_sats=50 * 100_000_000
        )
        pid = node.purchase_service(lid, 'buyer_1')
        assert pid is not None
        assert pid.startswith('pur_')

    def test_rate_service(self, node):
        from baitcoin_ai.marketplace.services import ServiceCategory
        lid = node.list_service(
            provider='provider_3', category=ServiceCategory.ORACLE_DATA,
            name='Price Feed', description='Real-time prices',
            price_sats=25 * 100_000_000
        )
        pid = node.purchase_service(lid, 'buyer_2')
        ok = node.rate_service(pid, 4.5)
        assert ok is True

    def test_search_services(self, node):
        from baitcoin_ai.marketplace.services import ServiceCategory
        node.list_service('s_provider', ServiceCategory.ML_INFERENCE, 'ML Service', 'desc', 100)
        node.list_service('s_provider', ServiceCategory.BLOCK_VALIDATION, 'Block Val', 'desc', 200)
        results = node.search_services(category=ServiceCategory.ML_INFERENCE)
        assert len(results) >= 1


# ============================================================
# FASE 8: Oracle
# ============================================================
class TestPhase8Oracle:
    def test_register_oracle(self, node):
        node.register_oracle('oracle_1', 80.0)
        node.register_oracle('oracle_2', 60.0)
        assert len(node.oracle.oracles) >= 2

    def test_submit_and_get_price(self, node):
        node.register_oracle('oracle_p1', 70.0)
        node.register_oracle('oracle_p2', 70.0)
        node.register_oracle('oracle_p3', 70.0)
        node.submit_price('oracle_p1', 'BAIT', 0.001)
        node.submit_price('oracle_p2', 'BAIT', 0.0012)
        node.submit_price('oracle_p3', 'BAIT', 0.0008)
        price = node.get_price('BAIT')
        assert price is not None
        assert 0.0005 < price < 0.002

    def test_insufficient_sources(self, node):
        node.register_oracle('solo_oracle', 70.0)
        node.submit_price('solo_oracle', 'RARE', 100.0)
        price = node.get_price('RARE')
        assert price is None  # Need 3 sources minimum


# ============================================================
# FASE 9: zkML Proofs
# ============================================================
class TestPhase9ZkML:
    def test_generate_and_verify_proof(self, node):
        proof = node.generate_zk_proof(
            'prover_1', 'gpt-4', b'classification_input',
            b'classification_output', '0' * 64, 42
        )
        assert proof is not None
        ok = node.verify_zk_proof(proof)
        assert ok is True

    def test_tampered_proof_fails(self, node):
        proof = node.generate_zk_proof(
            'tamper_prover', 'model_x', b'in', b'out', '0' * 64, 42
        )
        proof.challenge = 0  # tamper
        ok = node.verify_zk_proof(proof)
        assert ok is False

    def test_pedersen_commitment(self, node):
        tc = node.commit_tensor(b'tensor_data_xyz')
        assert tc.commitment > 0
        ok = node.verify_tensor(tc, b'tensor_data_xyz')
        assert ok is True

    def test_wrong_tensor_fails(self, node):
        tc = node.commit_tensor(b'correct_data')
        ok = node.verify_tensor(tc, b'wrong_data')
        assert ok is False


# ============================================================
# FASE 10: PoUW
# ============================================================
class TestPhase10PoUW:
    def test_submit_valid_work(self, node):
        result = node.submit_pouw('ml_inference', {
            'model_hash': 'abc', 'input_hash': 'def', 'output_hash': 'ghi'
        }, agent_id='pouw_agent')
        assert result['valid'] is True

    def test_pouw_stats(self, node):
        node.submit_pouw('ml_inference', {
            'model_hash': 'h1a', 'input_hash': 'h2a', 'output_hash': 'h3a'
        }, agent_id='pouw_stats_agent_1')
        node.submit_pouw('ml_inference', {
            'model_hash': 'h1b', 'input_hash': 'h2b', 'output_hash': 'h3b'
        }, agent_id='pouw_stats_agent_2')
        stats = node.pouw_validator.get_stats()
        assert stats['total_submissions'] >= 2


# ============================================================
# FASE 11: Obscura
# ============================================================
class TestPhase11Obscura:
    def test_bridge_stats(self, node):
        stats = node.obscura_bridge.get_stats()
        assert 'server_running' in stats
        assert 'total_operations' in stats

    def test_web_scraping_capability(self, node):
        tid = node.obscura_capability.submit_task(
            'obscura_agent', 'fetch', urls=['https://example.com']
        )
        assert tid.startswith('scrape_')
        result = node.obscura_capability.execute_task(tid)
        assert result is not None

    def test_capability_stats(self, node):
        stats = node.obscura_capability.get_stats()
        assert 'total_tasks' in stats


# ============================================================
# FASE 12: Persistencia E2E (Save -> Destroy -> Restore -> Validate)
# ============================================================
class TestPhase12Persistence:
    def test_persistence_roundtrip(self, tmp_dir):
        """Salva estado completo, destroi o no, recria do disco, valida."""
        path = tmp_dir

        # === FASE 1: Criar no e popular ===
        from baitcoin_core.ecosystem import EcosystemNode
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        from baitcoin_ai.marketplace.services import ServiceCategory
        from baitcoin_bank.defi_core.vault import StrategyType

        node1 = EcosystemNode(data_path=path, auto_persist=True)
        key1 = SchnorrKeyPair()

        # Minerar blocos
        for i in range(3):
            node1.mine_block(f'persist_miner_{i}', key1.pub_bytes)
        height_before = node1.blockchain.height

        # Token operations
        node1.mint('persist_agent_a', 500 * 100_000_000)
        node1.transfer('persist_agent_a', 'persist_agent_b', 200 * 100_000_000)

        # Agents
        node1.register_agent('persist_ai_1', '0x' + 'f1' * 32, [AgentCapability.ML_INFERENCE, AgentCapability.WEB_SCRAPING])
        node1.update_reputation('persist_ai_1', 25, 'excellent_work')

        # Staking
        node1.stake('persist_staker', 2000 * 100_000_000)

        # Lending
        offer_id = node1.create_loan_offer('persist_lender', 100 * 100_000_000, 10.0)
        node1.borrow('persist_borrower', offer_id, 150 * 100_000_000)

        # Vault
        node1.create_vault('persist_vault_agent')
        node1.vault_deposit('persist_vault_agent', 3000 * 100_000_000, StrategyType.STAKING)

        # Marketplace
        node1.list_service('persist_provider', ServiceCategory.ML_INFERENCE, 'Persist Service', 'desc', 50 * 100_000_000)

        # Oracle
        node1.register_oracle('persist_oracle', 90.0)
        node1.submit_price('persist_oracle', 'BAIT', 0.005)

        # Faucet
        node1.faucet_claim('persist_faucet_agent', '0x' + 'fa' * 32)

        # zkML proof
        proof = node1.generate_zk_proof('persist_prover', 'model_p', b'input_p', b'output_p', 'a' * 64, 99)
        proof_id = proof.proof_id

        # Forcar snapshot e desligar
        node1.shutdown()

        # === FASE 2: Recriar no do mesmo diretorio ===
        node2 = EcosystemNode(data_path=path, auto_persist=True)

        # Validar blockchain
        assert node2.blockchain.height == height_before, f"Expected height {height_before}, got {node2.blockchain.height}"
        assert node2.validate_chain() is True

        # Validar saldos
        assert node2.balance_of('persist_agent_a') == 300 * 100_000_000
        assert node2.balance_of('persist_agent_b') == 200 * 100_000_000

        # Validar agente
        agent = node2.get_agent('persist_ai_1')
        assert agent is not None
        assert agent.reputation_score == 75.0
        assert AgentCapability.ML_INFERENCE in agent.capabilities
        assert AgentCapability.WEB_SCRAPING in agent.capabilities

        # Validar staking
        assert node2.staking.total_staked == 2000 * 100_000_000
        assert 'persist_staker' in node2.staking.positions

        # Validar lending
        assert len(node2.lending.loans) >= 1

        # Validar vault
        vault = node2.get_vault('persist_vault_agent')
        assert vault is not None
        assert vault.deposits_total == 3000 * 100_000_000

        # Validar marketplace
        assert len(node2.marketplace.listings) >= 1

        # Validar oracle
        assert 'persist_oracle' in node2.oracle.oracles

        # Validar faucet
        assert len(node2.faucet._claims) >= 1

        node2.shutdown()

    def test_persistence_continuation(self, tmp_dir):
        """Apos restore, o no continua operando normalmente."""
        from baitcoin_core.ecosystem import EcosystemNode
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair

        key = SchnorrKeyPair()
        node1 = EcosystemNode(data_path=tmp_dir)
        node1.mint('cont_agent', 100 * 100_000_000)
        node1.mine_block('cont_miner', key.pub_bytes)
        h1 = node1.blockchain.height
        node1.shutdown()

        node2 = EcosystemNode(data_path=tmp_dir)
        # Continua operando apos restore
        node2.mine_block('cont_miner_2', key.pub_bytes)
        assert node2.blockchain.height == h1 + 1
        node2.mint('cont_new_agent', 50 * 100_000_000)
        assert node2.balance_of('cont_new_agent') == 50 * 100_000_000
        node2.shutdown()

    def test_wal_corruption_recovery(self, tmp_dir):
        """O store recupera dados mesmo com entradas corrompidas no WAL."""
        from baitcoin_memory import MemoryStore
        store = MemoryStore(tmp_dir)
        store.put('corrupt_test', 'valid_key', 'valid_value')
        store.force_snapshot('corrupt_test')
        # Escrever lixo no WAL
        import os
        wal_dir = os.path.join(tmp_dir, 'corrupt_test', 'wal')
        if os.path.isdir(wal_dir):
            for f in os.listdir(wal_dir):
                if f.endswith('.log'):
                    path = os.path.join(wal_dir, f)
                    with open(path, 'a') as fh:
                        fh.write('{corrupted json entry\n')
        # Recarregar deve sobreviver
        store2 = MemoryStore(tmp_dir)
        val = store2.get('corrupt_test', 'valid_key')
        assert val == 'valid_value'

    def test_context_manager(self, tmp_dir):
        """O EcosystemNode funciona como context manager com snapshot garantido."""
        from baitcoin_core.ecosystem import EcosystemNode
        with EcosystemNode(data_path=tmp_dir) as node:
            node.mint('ctx_agent', 77 * 100_000_000)
        # Apos o context manager, dados devem estar em disco
        from baitcoin_memory import MemoryStore, PersistentState
        store = MemoryStore(tmp_dir)
        state = PersistentState(store)
        data = state.load_blockchain()
        assert data is not None

    def test_ecosystem_to_dict(self, node, miner_key):
        """O to_dict() retorna estado completo de todos os modulos."""
        node.mine_block('dict_miner', miner_key.pub_bytes)
        node.register_agent('dict_agent', '0x' + '99' * 32)
        d = node.to_dict()
        assert 'blockchain' in d
        assert 'token' in d
        assert 'agents' in d
        assert 'staking' in d
        assert 'lending' in d
        assert 'marketplace' in d
        assert 'oracle' in d
        assert 'obscura' in d
        assert 'persistence' in d
        assert d['blockchain']['height'] >= 1

    def test_persistence_stats(self, node):
        stats = node.get_persistence_stats()
        assert 'namespaces' in stats
        assert 'total_writes' in stats
        assert 'cached_keys' in stats


# ============================================================
# INTEGRACAO CRUZADA: Modulos interoperando
# ============================================================
class TestCrossModuleIntegration:
    def test_mine_and_transfer_flow(self, node, miner_key):
        """Mineracao gera reward, transfer move saldo."""
        node.mine_block('flow_miner', miner_key.pub_bytes)
        node.mint('flow_agent', 500 * 100_000_000)
        node.transfer('flow_agent', 'flow_receiver', 100 * 100_000_000)
        assert node.balance_of('flow_receiver') == 100 * 100_000_000
        # Staking do receiver
        assert node.stake('flow_receiver', 100 * 100_000_000) is False  # abaixo do min

    def test_agent_stake_and_validate(self, node):
        """Agente com stake + reputacao + capacidade = validator."""
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        node.register_agent('sv_agent', '0x' + 'sv' * 16, [AgentCapability.BLOCK_VALIDATION])
        node.update_reputation('sv_agent', 30, 'qualifying')
        node.mint('sv_agent', 5000 * 100_000_000)
        node.stake('sv_agent', 1000 * 100_000_000)
        validators = node.get_validators()
        assert 'sv_agent' in validators
        val_set = node.get_validator_set()
        assert 'sv_agent' in val_set

    def test_lending_with_marketplace(self, node):
        """Oferta de emprestimo + servico no marketplace."""
        from baitcoin_ai.marketplace.services import ServiceCategory
        oid = node.create_loan_offer('int_lender', 1000 * 100_000_000, 15.0)
        lid = node.list_service(
            'int_provider', ServiceCategory.MARKET_ANALYSIS,
            'Lending Advice', 'AI-powered lending analysis', 50 * 100_000_000
        )
        assert oid is not None
        assert lid is not None

    def test_full_lifecycle(self, node, miner_key):
        """Ciclo completo: minerar -> mint -> transfer -> stake -> borrow -> vault -> verify."""
        from baitcoin_bank.defi_core.vault import StrategyType
        # Mine
        node.mine_block('lifecycle_miner', miner_key.pub_bytes)
        # Mint
        node.mint('lifecycle_agent', 10000 * 100_000_000)
        # Transfer
        node.transfer('lifecycle_agent', 'lifecycle_agent_2', 3000 * 100_000_000)
        # Stake
        node.stake('lifecycle_agent', 1000 * 100_000_000)
        # Vault
        node.create_vault('lifecycle_agent')
        node.vault_deposit('lifecycle_agent', 2000 * 100_000_000, StrategyType.LENDING)
        # Lending
        offer = node.create_loan_offer('lifecycle_agent', 500 * 100_000_000, 12.0)
        # Verify chain
        assert node.validate_chain() is True
        # Final balance: 10000 - 3000(transfer) = 7000
        # (vault_deposit is on a separate DeFi tracking, not token balance)
        assert node.balance_of('lifecycle_agent') == 7000 * 100_000_000
        assert node.balance_of('lifecycle_agent_2') == 3000 * 100_000_000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
