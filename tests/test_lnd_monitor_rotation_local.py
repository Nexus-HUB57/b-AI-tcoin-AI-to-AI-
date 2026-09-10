from threading import Thread
from types import SimpleNamespace
from urllib.request import urlopen

import pytest

from scripts.lnd_monitor import LndMonitor
from scripts.macaroon_rotation import MacaroonRotationError, RotatingMacaroonProvider


class Messages:
    class GetInfoRequest:
        pass


class HealthyLnd:
    def GetInfo(self, request, timeout=None):
        return SimpleNamespace(
            alias="mock-lnd",
            identity_pubkey="02" + "11" * 32,
            block_height=900,
            num_active_channels=3,
            num_pending_channels=1,
            num_inactive_channels=2,
            chains=[SimpleNamespace(network="mainnet")],
        )


class BrokenLnd:
    def GetInfo(self, request, timeout=None):
        raise TimeoutError("mock timeout")


def test_monitor_healthcheck_persists_mock_snapshot(tmp_path):
    monitor = LndMonitor(HealthyLnd(), Messages, tmp_path / "monitor.sqlite3", now=lambda: 123.0)
    snapshot = monitor.check_once()
    assert snapshot.reachable is True
    assert snapshot.network == "mainnet"
    assert snapshot.num_active_channels == 3
    assert monitor.latest() == snapshot
    monitor.close()


def test_prometheus_endpoint_exports_metrics(tmp_path):
    monitor = LndMonitor(HealthyLnd(), Messages, tmp_path / "monitor.sqlite3", now=lambda: 123.0)
    monitor.check_once()
    server = monitor.serve_metrics(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/metrics", timeout=2) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
        assert 'lnd_monitor_up{network="mainnet"} 1' in body
        assert 'lnd_block_height{network="mainnet"} 900' in body
        assert 'lnd_channels{network="mainnet",state="active"} 3' in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        monitor.close()


def test_monitor_records_unreachable_without_crashing(tmp_path):
    monitor = LndMonitor(BrokenLnd(), Messages, tmp_path / "monitor.sqlite3", now=lambda: 123.0)
    snapshot = monitor.check_once()
    assert snapshot.reachable is False
    assert snapshot.error == "TimeoutError"
    monitor.close()


def test_rotation_stage_activate_and_rollback(tmp_path):
    provider = RotatingMacaroonProvider(tmp_path / "lnd.macaroon")
    provider.stage(b"macaroon-v1")
    provider.activate()
    assert provider.load() == b"macaroon-v1"
    provider.stage(b"macaroon-v2")
    provider.activate()
    assert provider.load() == b"macaroon-v2"
    provider.rollback()
    assert provider.load() == b"macaroon-v1"


def test_rotation_requires_staged_value(tmp_path):
    provider = RotatingMacaroonProvider(tmp_path / "lnd.macaroon")
    with pytest.raises(MacaroonRotationError):
        provider.activate()
