import pytest

from main_daemon import load_p2p_port, load_p2p_seeds


def test_public_pool_service_names_are_valid_external_seeds():
    assert len(load_p2p_seeds("bait-node-1:18444,bait-node-2:18444,bait-node-3:18444")) == 3


@pytest.mark.parametrize("value", ["0", "65536", "not-a-port"])
def test_p2p_port_is_validated(value):
    with pytest.raises((ValueError, TypeError)):
        load_p2p_port(value)


def test_p2p_port_accepts_valid_port():
    assert load_p2p_port("18444") == 18444
