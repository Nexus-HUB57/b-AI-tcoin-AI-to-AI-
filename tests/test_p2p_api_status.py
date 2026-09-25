import json
import threading
import urllib.request

from baitcoin_api.server import BaitcoinAPIHandler, create_app


class FakeP2P:
    def get_public_status(self):
        return {
            "node_id": "api-test-node",
            "running": True,
            "listen_host": "0.0.0.0",
            "listen_port": 18444,
            "configured_seeds": [
                {"host": "seed-a.example", "port": 18444},
                {"host": "seed-b.example", "port": 18444},
                {"host": "seed-c.example", "port": 18444},
            ],
            "peer_count": 3,
            "inbound_count": 1,
            "outbound_count": 2,
            "handshake_peers": 3,
            "peers": [],
            "attestation": "transport-only",
        }


def test_p2p_status_route_returns_transport_evidence():
    previous = BaitcoinAPIHandler.p2p_node
    server = create_app(host="127.0.0.1", port=0)
    BaitcoinAPIHandler.p2p_node = FakeP2P()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/v1/p2p/status",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read())
        assert payload["attestation"] == "transport-only"
        assert payload["running"] is True
        assert payload["peer_count"] == 3
        assert payload["handshake_peers"] == 3
        assert "chain_height" not in payload
    finally:
        server.shutdown()
        server.server_close()
        BaitcoinAPIHandler.p2p_node = previous
