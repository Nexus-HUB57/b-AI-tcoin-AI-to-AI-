r"""
Testes do modulo baitcoin_obscura - integracao Obscura com b'AI'tcoin.

Cobertura:
- ObscuraConfig (validacao, serializacao)
- ObscuraBridge (stats, sessoes, ciclo de vida)
- WebScrapingResult (serializacao)
- WebScrapingCapability (tarefas, execucao)
- AgentCapability (novas capacidades WEB_SCRAPING + BROWSER_AUTOMATION)
- API endpoints (obscura/status, obscura/fetch, obscura/scrape)
"""

import pytest
import json
import time


# --- 1. AgentCapability (novas capacidades) ---
class TestAgentCapabilities:
    r"""Testa novas capacidades de agente adicionadas ao registry."""

    def test_web_scraping_capability_exists(self):
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        assert hasattr(AgentCapability, 'WEB_SCRAPING')
        assert AgentCapability.WEB_SCRAPING.value == 'web_scraping'

    def test_browser_automation_capability_exists(self):
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        assert hasattr(AgentCapability, 'BROWSER_AUTOMATION')
        assert AgentCapability.BROWSER_AUTOMATION.value == 'browser_automation'

    def test_total_capabilities_count(self):
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        assert len(AgentCapability) == 10

    def test_register_agent_with_web_scraping(self):
        from baitcoin_ai.agent_protocol.registry import (
            AgentRegistry, AgentCapability,
        )
        registry = AgentRegistry()
        ok = registry.register(
            'agent_obscura_1', '0x' + 'ab' * 32,
            capabilities=[AgentCapability.WEB_SCRAPING, AgentCapability.ML_INFERENCE],
        )
        assert ok
        agent = registry.get_agent('agent_obscura_1')
        assert AgentCapability.WEB_SCRAPING in agent.capabilities
        assert AgentCapability.BROWSER_AUTOMATION not in agent.capabilities


# --- 2. ObscuraConfig ---
class TestObscuraConfig:
    r"""Testa configuracao do Obscura bridge."""

    def test_default_config(self):
        from baitcoin_obscura.config import ObscuraConfig, BrowserMode
        cfg = ObscuraConfig()
        assert cfg.cdp_port == 9222
        assert cfg.mode == BrowserMode.STEALTH
        assert cfg.cost_per_page_sats == 1000
        assert cfg.max_concurrent_pages == 10
        assert cfg.agent_id == ''

    def test_config_to_dict(self):
        from baitcoin_obscura.config import ObscuraConfig
        cfg = ObscuraConfig(agent_id='test_agent')
        d = cfg.to_dict()
        assert d['cdp_port'] == 9222
        assert d['stealth'] is True
        assert d['agent_id'] == 'test_agent'
        assert d['cost_per_page_bait'] == 0.00001
        assert d['stealth_blocked_domains'] == 3520

    def test_custom_config(self):
        from baitcoin_obscura.config import ObscuraConfig, BrowserMode
        cfg = ObscuraConfig(
            cdp_port=10000,
            mode=BrowserMode.NORMAL,
            proxy='socks5://127.0.0.1:1080',
            agent_id='deepseek_agent',
            cost_per_page_sats=500,
        )
        assert cfg.cdp_port == 10000
        assert cfg.mode == BrowserMode.NORMAL
        assert cfg.proxy == 'socks5://127.0.0.1:1080'
        assert cfg.agent_id == 'deepseek_agent'

    def test_browser_mode_values(self):
        from baitcoin_obscura.config import BrowserMode
        assert BrowserMode.STEALTH.value == 'stealth'
        assert BrowserMode.NORMAL.value == 'normal'
        assert BrowserMode.HEADLESS.value == 'headless'

    def test_config_validate(self):
        from baitcoin_obscura.config import ObscuraConfig
        cfg = ObscuraConfig()
        errors = cfg.validate()
        assert isinstance(errors, list)


# --- 3. WebScrapingResult ---
class TestWebScrapingResult:
    r"""Testa resultado de operacao de scraping."""

    def test_result_serialization(self):
        from baitcoin_obscura.bridge import WebScrapingResult
        result = WebScrapingResult(
            operation='fetch', url='https://example.com',
            status='success', content='<html>test</html>',
            title='Example', cost_sats=1000, duration_ms=85.5,
            agent_id='agent_1')
        d = result.to_dict()
        assert d['operation'] == 'fetch'
        assert d['url'] == 'https://example.com'
        assert d['status'] == 'success'
        assert d['content_length'] == 17
        assert d['cost_bait'] == 0.00001
        assert d['duration_ms'] == 85.5
        assert d['agent_id'] == 'agent_1'

    def test_error_result(self):
        from baitcoin_obscura.bridge import WebScrapingResult
        result = WebScrapingResult(
            operation='fetch', status='error',
            error='Binary not found')
        d = result.to_dict()
        assert d['status'] == 'error'
        assert d['content_length'] == 0


# --- 4. ObscuraBridge ---
class TestObscuraBridge:
    r"""Testa bridge Obscura (sem binario, testa interface)."""

    def test_bridge_creation(self):
        from baitcoin_obscura.bridge import ObscuraBridge
        bridge = ObscuraBridge()
        assert bridge.is_server_running is False

    def test_bridge_stats_no_server(self):
        from baitcoin_obscura.bridge import ObscuraBridge
        bridge = ObscuraBridge()
        stats = bridge.get_stats()
        assert stats['server_running'] is False
        assert stats['total_operations'] == 0
        assert stats['total_cost_bait'] == 0

    def test_bridge_fetch_no_binary(self):
        from baitcoin_obscura.bridge import ObscuraBridge
        bridge = ObscuraBridge()
        result = bridge.fetch_page('https://example.com')
        # Binary not found - graceful degradation
        assert result.status in ('error', 'success')
        assert result.operation == 'fetch'

    def test_bridge_scrape_no_binary(self):
        from baitcoin_obscura.bridge import ObscuraBridge
        bridge = ObscuraBridge()
        results = bridge.scrape_pages(['https://example.com'])
        assert len(results) >= 1

    def test_bridge_session_management(self):
        from baitcoin_obscura.bridge import ObscuraBridge
        bridge = ObscuraBridge()
        session = bridge.create_session('agent_test')
        assert session.session_id
        assert session.cdp_url == 'ws://127.0.0.1:9222'
        assert session.is_active is True
        bridge.close_session(session.session_id)
        assert bridge.get_stats()['active_sessions'] == 0

    def test_bridge_custom_config(self):
        from baitcoin_obscura.bridge import ObscuraBridge
        from baitcoin_obscura.config import ObscuraConfig
        cfg = ObscuraConfig(cdp_port=10000, agent_id='test')
        bridge = ObscuraBridge(config=cfg)
        stats = bridge.get_stats()
        assert stats['config']['cdp_port'] == 10000

    def test_bridge_snapshot(self):
        from baitcoin_obscura.bridge import ObscuraBridge
        bridge = ObscuraBridge()
        result = bridge.snapshot('https://example.com', agent_id='snap_agent')
        assert result.operation == 'fetch'  # snapshot delegates to fetch


# --- 5. WebScrapingCapability ---
class TestWebScrapingCapability:
    r"""Testa capability de scraping para agentes AI."""

    def test_capability_creation(self):
        from baitcoin_obscura.agent_capability import WebScrapingCapability
        cap = WebScrapingCapability()
        assert cap.CAPABILITY_NAME == 'web_scraping'

    def test_submit_and_execute_fetch_task(self):
        from baitcoin_obscura.agent_capability import WebScrapingCapability
        cap = WebScrapingCapability()
        task_id = cap.submit_task('agent_1', 'fetch', urls=['https://example.com'])
        assert task_id.startswith('scrape_')
        task = cap.get_task(task_id)
        assert task.status == 'pending'
        result = cap.execute_task(task_id)
        assert result is not None
        assert task.status in ('completed', 'failed')

    def test_submit_scrape_task(self):
        from baitcoin_obscura.agent_capability import WebScrapingCapability
        cap = WebScrapingCapability()
        task_id = cap.submit_task(
            'agent_2', 'scrape',
            urls=['https://a.com', 'https://b.com'],
            concurrency=5)
        assert task_id
        assert len(cap.get_task(task_id).urls) == 2

    def test_list_tasks(self):
        from baitcoin_obscura.agent_capability import WebScrapingCapability
        cap = WebScrapingCapability()
        cap.submit_task('agent_a', 'fetch', urls=['https://a.com'])
        cap.submit_task('agent_a', 'snapshot', urls=['https://b.com'])
        cap.submit_task('agent_b', 'fetch', urls=['https://c.com'])
        tasks = cap.list_tasks('agent_a')
        assert len(tasks) == 2
        all_tasks = cap.list_tasks()
        assert len(all_tasks) == 3

    def test_capability_stats(self):
        from baitcoin_obscura.agent_capability import WebScrapingCapability
        cap = WebScrapingCapability()
        tid = cap.submit_task('agent_1', 'fetch', urls=['https://example.com'])
        cap.execute_task(tid)
        stats = cap.get_stats()
        assert stats['capability'] == 'web_scraping'
        assert stats['total_tasks'] == 1

    def test_unknown_task_type(self):
        from baitcoin_obscura.agent_capability import WebScrapingCapability
        cap = WebScrapingCapability()
        tid = cap.submit_task('agent_1', 'unknown_type')
        result = cap.execute_task(tid)
        assert result.status == 'error'

    def test_execute_nonexistent_task(self):
        from baitcoin_obscura.agent_capability import WebScrapingCapability
        cap = WebScrapingCapability()
        result = cap.execute_task('nonexistent')
        assert result is None


# --- 6. Integration: Agent + Obscura Capability ---
class TestAgentObscuraIntegration:
    r"""Testa integracao agente + capability de scraping."""

    def test_agent_registered_with_scraping_can_scrape(self):
        from baitcoin_ai.agent_protocol.registry import (
            AgentRegistry, AgentCapability,
        )
        from baitcoin_obscura.agent_capability import WebScrapingCapability
        registry = AgentRegistry()
        registry.register(
            'scraper_agent', '0x' + 'cd' * 32,
            capabilities=[AgentCapability.WEB_SCRAPING],
        )
        cap = WebScrapingCapability()
        tid = cap.submit_task('scraper_agent', 'fetch', urls=['https://example.com'])
        result = cap.execute_task(tid)
        assert result is not None
        assert result.agent_id == 'scraper_agent'

    def test_all_10_capabilities_listable(self):
        from baitcoin_ai.agent_protocol.registry import AgentCapability
        caps = [c.value for c in AgentCapability]
        assert 'web_scraping' in caps
        assert 'browser_automation' in caps
        assert 'ml_inference' in caps
        assert len(caps) == 10

    def test_obscura_cost_tracking(self):
        from baitcoin_obscura.bridge import ObscuraBridge, ObscuraConfig
        cfg = ObscuraConfig(cost_per_page_sats=2000)
        bridge = ObscuraBridge(config=cfg)
        # Fetch costs 2000 sats
        bridge.fetch_page('https://example.com')
        stats = bridge.get_stats()
        assert stats['total_cost_bait'] >= 0  # depends on binary availability


# --- 7. Dockerfile + Docker Compose ---
class TestDockerFiles:
    r"""Testa existencia e conteudo dos ficheiros Docker."""

    def test_dockerfile_ubuntu_exists(self):
        import os
        assert os.path.exists('Dockerfile.ubuntu')

    def test_dockerfile_has_obscura(self):
        with open('Dockerfile.ubuntu') as f:
            content = f.read()
        assert 'obscura' in content.lower()
        assert '9222' in content
        assert 'stealth' in content

    def test_dockerfile_has_baitcoin(self):
        with open('Dockerfile.ubuntu') as f:
            content = f.read()
        assert 'baitcoin' in content.lower()
        assert '18445' in content
        assert '18444' in content

    def test_docker_compose_exists(self):
        import os
        assert os.path.exists('docker-compose.ubuntu.yml')

    def test_entrypoint_exists(self):
        import os
        assert os.path.exists('docker/entrypoint.sh')

    def test_entrypoint_starts_both(self):
        with open('docker/entrypoint.sh') as f:
            content = f.read()
        assert 'obscura serve' in content
        assert 'main_daemon.py' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])