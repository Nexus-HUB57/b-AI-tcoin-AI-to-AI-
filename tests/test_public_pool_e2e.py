import asyncio

from scripts.run_public_pool_e2e import run


def test_four_node_public_pool_transport_e2e():
    result = asyncio.run(run(4))
    assert result["status"] == "GO"
    assert result["mode"] == "local-transport-only"
    assert result["node_count"] == 4
    assert result["gossip"]["recipients"] == 3
    for node in result["nodes"]:
        assert node["running"] is True
        assert node["peer_count"] == 3
        assert node["handshake_peers"] == 3
        assert node["listen_port"] > 0
