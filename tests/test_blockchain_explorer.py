r"""
Testes completos do Blockch'AI'in Explorer — b'AI'tcoin Developer Portal.

Cobre:
  - Indices on-chain (BlockchAInIndex)
  - Analytics on-chain (OnChainAnalytics)
  - Busca universal (UniversalSearch)
  - Developer docs (DeveloperDocs + OpenAPI 3.0)
  - Rate limiter (RateLimiter + API keys)
  - Integracao com server.py (endpoints HTTP)

Total: ~60 testes
"""

import unittest
import json
import time
import tempfile
import os


class TestBlockchAInIndex(unittest.TestCase):
    r"""Testes dos indices on-chain do explorer."""

    def setUp(self):
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
        from baitcoin_explorer.indices import BlockchAInIndex

        self.blockchain = Blockchain(ZkMLConsensus())
        self.token = BAITToken()
        self.registry = AgentRegistry()
        self.index = BlockchAInIndex()

        # Minerar alguns blocos
        self.blockchain.mine_block("agent_alice", b"\x01" * 33)
        self.blockchain.mine_block("agent_bob", b"\x02" * 33)
        self.blockchain.mine_block("agent_carol", b"\x03" * 33)

        # Registrar agentes
        self.registry.register("agent_alice", "01" * 64,
                                [AgentCapability.ML_INFERENCE, AgentCapability.BLOCK_VALIDATION])
        self.registry.register("agent_bob", "02" * 64,
                                [AgentCapability.DEFI_TRADING])
        self.registry.register("agent_carol", "03" * 64,
                                [AgentCapability.STAKING, AgentCapability.ORACLE_PROVIDER])

        # Mint tokens para testes
        self.token.mint("agent_alice", 500 * 100_000_000)
        self.token.mint("agent_bob", 200 * 100_000_000)

        # Rebuild indices
        self.index.rebuild(self.blockchain, self.token, self.registry)

    def test_index_stats(self):
        r"""Stats dos indices devem refletir blocos e transacoes indexadas."""
        stats = self.index.stats
        self.assertGreater(stats['indexed_blocks'], 0)
        self.assertGreater(stats['indexed_transactions'], 0)
        self.assertGreaterEqual(stats['indexed_addresses'], 0)
        self.assertEqual(stats['last_indexed_height'], self.blockchain.height)

    def test_get_block_by_height(self):
        r"""Busca por altura deve retornar bloco correto."""
        block = self.index.get_block_by_height(0)
        self.assertIsNotNone(block)
        self.assertEqual(block.index, 0)
        self.assertEqual(block.validator, 'chimera7_genesis')

        block1 = self.index.get_block_by_height(1)
        self.assertIsNotNone(block1)
        self.assertEqual(block1.index, 1)
        self.assertEqual(block1.validator, 'agent_alice')

    def test_get_block_by_height_not_found(self):
        r"""Altura inexistente deve retornar None."""
        block = self.index.get_block_by_height(99999)
        self.assertIsNone(block)

    def test_get_block_by_hash(self):
        r"""Busca por hash deve funcionar."""
        block = self.index.get_block_by_height(0)
        found = self.index.get_block_by_hash(block.hash)
        self.assertIsNotNone(found)
        self.assertEqual(found.index, 0)

    def test_get_latest_blocks(self):
        r"""Ultimos blocos devem vir em ordem descendente."""
        blocks = self.index.get_latest_blocks(limit=10)
        self.assertGreater(len(blocks), 0)
        # Verificar ordem descendente
        for i in range(len(blocks) - 1):
            self.assertGreater(blocks[i].index, blocks[i + 1].index)

    def test_get_latest_blocks_pagination(self):
        r"""Paginacao de blocos deve funcionar."""
        all_blocks = self.index.get_latest_blocks(limit=100)
        page1 = self.index.get_latest_blocks(limit=2, offset=0)
        page2 = self.index.get_latest_blocks(limit=2, offset=2)
        self.assertEqual(len(page1), 2)
        if len(all_blocks) > 2:
            self.assertNotEqual(page1[0].hash, page2[0].hash)

    def test_get_tx(self):
        r"""Busca de transacao por hash."""
        txs = self.index.get_latest_txs(limit=1)
        if txs:
            tx = self.index.get_tx(txs[0].tx_id)
            self.assertIsNotNone(tx)
            self.assertEqual(tx.tx_id, txs[0].tx_id)

    def test_get_tx_not_found(self):
        r"""Hash inexistente deve retornar None."""
        tx = self.index.get_tx('00' * 32)
        self.assertIsNone(tx)

    def test_get_latest_txs(self):
        r"""Ultimas transacoes devem vir em ordem de timestamp descendente."""
        txs = self.index.get_latest_txs(limit=10)
        self.assertGreater(len(txs), 0)
        for i in range(len(txs) - 1):
            self.assertGreaterEqual(txs[i].timestamp, txs[i + 1].timestamp)

    def test_get_mempool_info(self):
        r"""Info do mempool deve incluir tamanho."""
        info = self.index.get_mempool_info(self.blockchain)
        self.assertIn('mempool_size', info)
        self.assertIn('sample_transactions', info)

    def test_update_confirmations(self):
        r"""Atualizar confirmacoes deve funcionar."""
        self.index.update_confirmations(self.blockchain.height)
        txs = self.index.get_latest_txs(limit=5)
        for tx in txs:
            if tx.block_height >= 0:
                self.assertGreater(tx.confirmations, 0)

    def test_get_total_addresses(self):
        r"""Contagem de enderecos deve ser >= 0."""
        total = self.index.get_total_addresses()
        self.assertGreaterEqual(total, 0)

    def test_block_to_dict(self):
        r"""Serializacao de BlockInfo deve incluir campos do consenso."""
        block = self.index.get_block_by_height(0)
        d = block.to_dict()
        self.assertIn('block_height', d)
        self.assertIn('hash', d)
        self.assertIn('validator', d)
        self.assertIn('consensus', d)
        self.assertIn('zkml_proof_hash', d['consensus'])
        self.assertIn('pouw_work_hash', d['consensus'])
        self.assertIn('tensor_commitment', d['consensus'])
        self.assertIn('reward_bait', d)
        self.assertIn('tx_ids', d)

    def test_tx_to_dict(self):
        r"""Serializacao de TxInfo deve incluir campos financeiros."""
        txs = self.index.get_latest_txs(limit=1)
        if txs:
            d = txs[0].to_dict()
            self.assertIn('tx_id', d)
            self.assertIn('tx_type', d)
            self.assertIn('agent_id', d)
            self.assertIn('confirmations', d)
            self.assertIn('total_output_bait', d)
            self.assertIn('fee_bait', d)
            self.assertIn('is_coinbase', d)


class TestOnChainAnalytics(unittest.TestCase):
    r"""Testes das analytics on-chain."""

    def setUp(self):
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
        from baitcoin_explorer.analytics import OnChainAnalytics

        self.blockchain = Blockchain(ZkMLConsensus())
        self.token = BAITToken()
        self.registry = AgentRegistry()
        self.analytics = OnChainAnalytics()

        self.blockchain.mine_block("agent_a", b"\x01" * 33)
        self.token.mint("agent_a", 1000 * 100_000_000)
        self.registry.register("agent_a", "01" * 64, [AgentCapability.ML_INFERENCE])

    def test_supply_analysis(self):
        r"""Supply analysis deve incluir campos obrigatorios."""
        supply = self.analytics.supply_analysis(self.blockchain, self.token)
        self.assertEqual(supply['max_supply_bait'], 21_000_000.0)
        self.assertIn('circulating_supply_bait', supply)
        self.assertIn('halving', supply)
        self.assertIn('inflation', supply)
        self.assertIn('holders', supply)
        self.assertIn('gini_coefficient', supply)
        self.assertIn('top_holders', supply)
        self.assertIn('current_reward_bait', supply['halving'])
        self.assertIn('blocks_until', supply['halving'])

    def test_supply_analysis_without_token(self):
        r"""Supply analysis sem token deve funcionar (usar apenas on-chain)."""
        supply = self.analytics.supply_analysis(self.blockchain, token=None)
        self.assertIn('on_chain_minted_bait', supply)
        self.assertEqual(supply['holders'], 0)

    def test_network_health(self):
        r"""Network health deve incluir metricas de rede."""
        health = self.analytics.network_health(self.blockchain)
        self.assertIn('status', health)
        self.assertIn('height', health)
        self.assertIn('avg_block_interval_s', health)
        self.assertIn('difficulty', health)
        self.assertIn('mempool_size', health)
        self.assertIn('utxo_count', health)
        self.assertIn('tps_last_hour', health)
        self.assertIn('chain_valid', health)
        self.assertTrue(health['chain_valid'])

    def test_agent_analysis(self):
        r"""Agent analysis deve incluir distribuicao de reputacao."""
        analysis = self.analytics.agent_analysis(self.registry)
        self.assertEqual(analysis['total'], 1)
        self.assertIn('active_24h', analysis)
        self.assertIn('validators', analysis)
        self.assertIn('avg_reputation', analysis)
        self.assertIn('reputation_distribution', analysis)
        self.assertIn('capability_coverage', analysis)
        self.assertIn('top_agents', analysis)
        self.assertEqual(len(analysis['top_agents']), 1)

    def test_agent_analysis_empty(self):
        r"""Agent analysis sem registry deve funcionar."""
        from baitcoin_ai.agent_protocol.registry import AgentRegistry
        empty = AgentRegistry()
        analysis = self.analytics.agent_analysis(empty)
        self.assertEqual(analysis['total'], 0)

    def test_staking_analysis_not_initialized(self):
        r"""Staking analysis sem pool deve retornar status."""
        result = self.analytics.staking_analysis(None)
        self.assertEqual(result['status'], 'not_initialized')

    def test_consensus_health(self):
        r"""Consensus health deve cobrir zkML, PoUW e tensor."""
        health = self.analytics.consensus_health(self.blockchain)
        self.assertIn('total_blocks', health)
        self.assertIn('zkml_proof_coverage_pct', health)
        self.assertIn('pouw_work_coverage_pct', health)
        self.assertIn('tensor_commitment_coverage_pct', health)
        self.assertIn('unique_validators', health)
        self.assertIn('consensus_engine', health)
        self.assertIn('status', health)

    def test_full_dashboard(self):
        r"""Dashboard completo deve agregar todas as metricas."""
        dashboard = self.analytics.full_dashboard(
            self.blockchain, self.token, self.registry
        )
        self.assertIn('generated_at', dashboard)
        self.assertIn('supply', dashboard)
        self.assertIn('network', dashboard)
        self.assertIn('agents', dashboard)
        self.assertIn('staking', dashboard)
        self.assertIn('consensus', dashboard)


class TestUniversalSearch(unittest.TestCase):
    r"""Testes da busca universal on-chain."""

    def setUp(self):
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
        from baitcoin_explorer.indices import BlockchAInIndex
        from baitcoin_explorer.search import UniversalSearch

        self.blockchain = Blockchain(ZkMLConsensus())
        self.token = BAITToken()
        self.registry = AgentRegistry()

        self.blockchain.mine_block("chimera7_miner", b"\xaa" * 33)
        self.blockchain.mine_block("deepseek_agent", b"\xbb" * 33)

        self.registry.register("chimera7_miner", "aa" * 64,
                                [AgentCapability.ML_INFERENCE, AgentCapability.BLOCK_VALIDATION])
        self.registry.register("deepseek_agent", "bb" * 64,
                                [AgentCapability.DEFI_TRADING])

        self.index = BlockchAInIndex()
        self.index.rebuild(self.blockchain, self.token, self.registry)
        self.search = UniversalSearch(self.index, self.registry)

    def test_search_empty_query(self):
        r"""Query vazia deve retornar 0 resultados."""
        result = self.search.query('')
        self.assertEqual(result['total'], 0)

    def test_search_by_height(self):
        r"""Buscar por numero deve encontrar bloco."""
        result = self.search.query('0')
        self.assertGreater(result['total'], 0)
        self.assertEqual(result['results'][0]['type'], 'block')

    def test_search_by_agent_id(self):
        r"""Buscar por agente deve encontrar resultado."""
        result = self.search.query('chimera7_miner')
        self.assertGreater(result['total'], 0)
        types_found = [r['type'] for r in result['results']]
        self.assertIn('agent', types_found)

    def test_search_by_block_hash(self):
        r"""Buscar por hash de bloco deve encontrar resultado exato."""
        block = self.index.get_block_by_height(0)
        result = self.search.query(block.hash)
        self.assertGreater(result['total'], 0)
        self.assertEqual(result['results'][0]['score'], 1.0)

    def test_search_filter_by_type(self):
        r"""Filtrar por tipo deve funcionar."""
        result = self.search.query('0', types=['block'])
        for r in result['results']:
            self.assertEqual(r['type'], 'block')

    def test_search_pagination(self):
        r"""Paginacao de resultados deve funcionar."""
        all_results = self.search.query('chimera', limit=100)
        page1 = self.search.query('chimera', limit=1, offset=0)
        self.assertEqual(len(page1['results']), 1)

    def test_search_result_structure(self):
        r"""Cada resultado deve ter campos obrigatorios."""
        result = self.search.query('0')
        for r in result['results']:
            self.assertIn('type', r)
            self.assertIn('id', r)
            self.assertIn('title', r)
            self.assertIn('score', r)
            self.assertIn('matched_field', r)
            self.assertGreaterEqual(r['score'], 0.05)

    def test_search_elapsed_ms(self):
        r"""Resultado deve incluir tempo de execucao."""
        result = self.search.query('0')
        self.assertIn('elapsed_ms', result)
        self.assertGreater(result['elapsed_ms'], 0)


class TestDeveloperDocs(unittest.TestCase):
    r"""Testes do Developer Docs e OpenAPI spec."""

    def setUp(self):
        from baitcoin_explorer.docs import DeveloperDocs
        self.docs = DeveloperDocs()

    def test_get_spec(self):
        r"""Spec OpenAPI deve ser gerada com campos obrigatorios."""
        spec = self.docs.get_spec()
        self.assertEqual(spec['openapi'], '3.0.3')
        self.assertIn('info', spec)
        self.assertIn('paths', spec)
        self.assertIn('components', spec)
        self.assertIn('servers', spec)
        self.assertIn('tags', spec)

    def test_spec_has_info(self):
        r"""Info deve ter title, version, description."""
        spec = self.docs.get_spec()
        info = spec['info']
        self.assertIn('title', info)
        self.assertIn('version', info)
        self.assertIn('description', info)
        self.assertIn('contact', info)
        self.assertIn('license', info)

    def test_spec_has_explorer_paths(self):
        r"""Spec deve ter paths do explorer."""
        spec = self.docs.get_spec()
        paths = spec['paths']
        self.assertIn('/api/v1/explorer/blocks', paths)
        self.assertIn('/api/v1/explorer/search', paths)
        self.assertIn('/api/v1/explorer/tx/{hash}', paths)
        self.assertIn('/api/v1/explorer/address/{address}', paths)

    def test_spec_has_analytics_paths(self):
        r"""Spec deve ter paths de analytics."""
        spec = self.docs.get_spec()
        paths = spec['paths']
        self.assertIn('/api/v1/analytics/supply', paths)
        self.assertIn('/api/v1/analytics/dashboard', paths)
        self.assertIn('/api/v1/analytics/consensus', paths)

    def test_spec_has_dev_paths(self):
        r"""Spec deve ter paths de developer tools."""
        spec = self.docs.get_spec()
        paths = spec['paths']
        self.assertIn('/api/v1/dev/spec', paths)
        self.assertIn('/api/v1/dev/docs', paths)
        self.assertIn('/api/v1/dev/endpoints', paths)

    def test_spec_has_components(self):
        r"""Components deve ter schemas, securitySchemes."""
        spec = self.docs.get_spec()
        components = spec['components']
        self.assertIn('schemas', components)
        self.assertIn('securitySchemes', components)
        self.assertIn('MoltbookAuth', components['securitySchemes'])
        self.assertIn('BaitAPIKey', components['securitySchemes'])
        self.assertIn('BlockDetail', components['schemas'])
        self.assertIn('TransactionDetail', components['schemas'])
        self.assertIn('AddressInfo', components['schemas'])
        self.assertIn('SearchResponse', components['schemas'])

    def test_spec_has_tags(self):
        r"""Tags devem cobrir todos os grupos."""
        spec = self.docs.get_spec()
        tag_names = [t['name'] for t in spec['tags']]
        self.assertIn('Explorer', tag_names)
        self.assertIn('Developer Tools', tag_names)
        self.assertIn('Analytics', tag_names)
        self.assertIn('Core', tag_names)
        self.assertIn('Obscura', tag_names)

    def test_list_all_endpoints(self):
        r"""Listar endpoints deve retornar lista categorizada."""
        result = self.docs.list_all_endpoints()
        self.assertIn('total', result)
        self.assertIn('endpoints', result)
        self.assertGreater(result['total'], 0)

    def test_get_playground_html(self):
        r"""HTML playground deve ser gerado e conter elementos-chave."""
        html = self.docs.get_playground_html()
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Blockch', html)
        self.assertIn('Developer Portal', html)
        self.assertIn('sidebar', html)
        self.assertIn('stats', html)

    def test_playground_html_contains_explorer_endpoints(self):
        r"""HTML playground deve referenciar endpoints do explorer."""
        html = self.docs.get_playground_html()
        self.assertIn('/api/v1/explorer/blocks', html)
        self.assertIn('/api/v1/explorer/search', html)

    def test_spec_description_mentions_zkml(self):
        r"""Descricao da spec deve mencionar zkML e PoUW."""
        spec = self.docs.get_spec()
        desc = spec['info']['description']
        self.assertIn('zkML', desc)
        self.assertIn('PoUW', desc)
        self.assertTrue(len(desc) > 50)


class TestRateLimiter(unittest.TestCase):
    r"""Testes do rate limiter e API keys."""

    def setUp(self):
        from baitcoin_explorer.rate_limiter import RateLimiter
        self.limiter = RateLimiter()

    def test_create_api_key(self):
        r"""Criar API key deve retornar chave e informacoes."""
        result = self.limiter.create_key(agent_id="test_agent", tier="free")
        self.assertIn('api_key', result)
        self.assertIn('key_prefix', result)
        self.assertIn('tier', result)
        self.assertEqual(result['tier'], 'free')
        self.assertTrue(result['api_key'].startswith('bait_'))

    def test_create_api_key_tiers(self):
        r"""Criar keys com diferentes tiers."""
        for tier in ['free', 'developer', 'pro', 'enterprise']:
            result = self.limiter.create_key(agent_id=f"agent_{tier}", tier=tier)
            self.assertEqual(result['tier'], tier)

    def test_verify_api_key(self):
        r"""Verificar key valida deve retornar info."""
        created = self.limiter.create_key(agent_id="test_verify", tier="developer")
        info = self.limiter.verify_key(created['api_key'])
        self.assertIsNotNone(info)
        self.assertEqual(info.agent_id, 'test_verify')
        self.assertTrue(info.is_active)

    def test_verify_invalid_key(self):
        r"""Key invalida deve retornar None."""
        info = self.limiter.verify_key('invalid_key_123')
        self.assertIsNone(info)

    def test_check_rate_allowed(self):
        r"""Request dentro do limite deve ser permitido."""
        created = self.limiter.create_key(agent_id="test_rate", tier="free")
        allowed, info = self.limiter.check_rate(created['api_key'])
        self.assertTrue(allowed)
        self.assertIn('remaining_minute', info)

    def test_check_rate_limit_exceeded(self):
        r"""Requests alem do limite devem ser bloqueados."""
        created = self.limiter.create_key(agent_id="test_exceed", tier="free")
        # Fazer 101 requests (limite free = 100/min)
        for _ in range(101):
            allowed, _ = self.limiter.check_rate(created['api_key'])
        # Proximo deve ser bloqueado
        allowed, info = self.limiter.check_rate(created['api_key'])
        self.assertFalse(allowed)
        self.assertEqual(info['error'], 'rate_limit_exceeded')

    def test_revoke_key(self):
        r"""Revogar key deve impedir uso."""
        created = self.limiter.create_key(agent_id="test_revoke", tier="free")
        ok = self.limiter.revoke_key(created['key_prefix'])
        self.assertTrue(ok)
        info = self.limiter.verify_key(created['api_key'])
        self.assertIsNone(info)

    def test_list_keys(self):
        r"""Listar keys deve retornar todas as chaves ativas."""
        self.limiter.create_key(agent_id="agent_a", tier="free")
        self.limiter.create_key(agent_id="agent_b", tier="developer")
        keys = self.limiter.list_keys()
        self.assertEqual(len(keys), 2)

    def test_list_keys_by_agent(self):
        r"""Filtrar keys por agente."""
        self.limiter.create_key(agent_id="agent_x", tier="free")
        self.limiter.create_key(agent_id="agent_y", tier="pro")
        self.limiter.create_key(agent_id="agent_x", tier="developer")
        keys = self.limiter.list_keys(agent_id="agent_x")
        self.assertEqual(len(keys), 2)

    def test_get_usage_stats(self):
        r"""Stats de uso devem incluir contagem por tier."""
        self.limiter.create_key(agent_id="a", tier="free")
        self.limiter.create_key(agent_id="b", tier="developer")
        stats = self.limiter.get_usage_stats()
        self.assertEqual(stats['total_active_keys'], 2)
        self.assertIn('free', stats['keys_by_tier'])
        self.assertIn('developer', stats['keys_by_tier'])
        self.assertIn('tier_pricing_bait_monthly', stats)


class TestExplorerIntegration(unittest.TestCase):
    r"""Teste de integracao: indices + search + server handler."""

    def setUp(self):
        from baitcoin_core.blockchain.chain import Blockchain
        from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
        from baitcoin_token.erc20_like.bait_token import BAITToken
        from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
        from baitcoin_explorer.indices import BlockchAInIndex
        from baitcoin_explorer.search import UniversalSearch
        from baitcoin_explorer.analytics import OnChainAnalytics
        from baitcoin_explorer.docs import DeveloperDocs
        from baitcoin_explorer.rate_limiter import RateLimiter

        self.blockchain = Blockchain(ZkMLConsensus())
        self.token = BAITToken()
        self.registry = AgentRegistry()

        # Minerar blocos com diferentes agentes
        for i in range(5):
            agent = f"miner_{i}"
            self.blockchain.mine_block(agent, bytes([i + 1]) * 33)

        # Registrar e dar reputation
        for i in range(5):
            self.registry.register(f"miner_{i}", f"{i:02d}" * 32,
                                    [AgentCapability.ML_INFERENCE])
            self.registry.update_reputation(f"miner_{i}", 10 * (i + 1), "mining_reward")

        # Mint e transfer
        self.token.mint("miner_0", 1000 * 100_000_000)
        self.token.transfer("miner_0", "miner_1", 100 * 100_000_000, "test")

        # Setup explorer
        self.index = BlockchAInIndex()
        self.index.rebuild(self.blockchain, self.token, self.registry)
        self.search = UniversalSearch(self.index, self.registry)
        self.analytics = OnChainAnalytics()
        self.docs = DeveloperDocs()
        self.rate_limiter = RateLimiter()

    def test_full_workflow(self):
        r"""Workflow completo: minerar -> indexar -> buscar -> analisar."""
        # 1. Verificar indices
        stats = self.index.stats
        self.assertGreater(stats['indexed_blocks'], 3)

        # 2. Buscar bloco genesis
        genesis = self.index.get_block_by_height(0)
        self.assertIsNotNone(genesis)
        self.assertEqual(genesis.validator, 'chimera7_genesis')

        # 3. Buscar transacoes
        txs = self.index.get_latest_txs(limit=5)
        self.assertGreater(len(txs), 0)

        # 4. Buscar universal
        results = self.search.query('miner_0')
        self.assertGreater(results['total'], 0)

        # 5. Analytics
        supply = self.analytics.supply_analysis(self.blockchain, self.token)
        self.assertGreater(supply['circulating_supply_bait'], 0)

        # 6. Consensus health
        consensus = self.analytics.consensus_health(self.blockchain)
        self.assertGreater(consensus['total_blocks'], 0)

        # 7. API key
        key_result = self.rate_limiter.create_key("miner_0", "developer")
        self.assertTrue(self.rate_limiter.verify_key(key_result['api_key']))

        # 8. OpenAPI spec
        spec = self.docs.get_spec()
        self.assertGreater(len(spec['paths']), 20)

    def test_incremental_index(self):
        r"""Indexacao incremental de novo bloco."""
        initial_count = self.index.stats['indexed_blocks']
        new_block = self.blockchain.mine_block("new_miner", b"\xff" * 33)
        txs_indexed = self.index.index_new_block(new_block, self.blockchain.height)
        self.assertGreaterEqual(txs_indexed, 1)
        self.assertEqual(self.index.stats['indexed_blocks'], initial_count + 1)

    def test_address_format(self):
        r"""Enderecos devem comecar com 'bait'."""
        addrs = self.index.get_all_addresses(limit=10)
        for addr in addrs:
            self.assertTrue(addr.address.startswith('bait'),
                            f"Address {addr.address} doesn't start with 'bait'")

    def test_html_playground_valid(self):
        r"""HTML playground deve ser valido (conter DOCTYPE e fechar tags)."""
        html = self.docs.get_playground_html()
        self.assertTrue(html.strip().startswith('<!DOCTYPE html>'))
        self.assertTrue(html.strip().endswith('</html>'))
        self.assertIn('SPEC=', html)
        self.assertIn('renderEndpoint', html)


if __name__ == '__main__':
    unittest.main()
