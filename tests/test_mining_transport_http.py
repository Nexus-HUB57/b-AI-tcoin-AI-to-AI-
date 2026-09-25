import copy
import json
import threading
import urllib.error
import urllib.request

import pytest

from baitcoin_api.server import BaitcoinAPIHandler, create_app
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.mining_transport import MiningTransportService
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus


def post(url, payload, headers=None):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        response = urllib.request.urlopen(request, timeout=3)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())
    with response:
        return response.status, json.loads(response.read())


def test_mainnet_transport_is_fail_closed():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    with pytest.raises(ValueError, match="disabled"):
        MiningTransportService(chain, network="mainnet", chain_id="bait-mainnet")


def test_http_template_then_share_is_e2e_and_read_only():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    service = MiningTransportService(
        chain,
        network="regtest",
        chain_id="transport-test",
        share_target=2**256 - 1,
    )
    previous = BaitcoinAPIHandler.mining_transport
    server = create_app(host="127.0.0.1", port=0)
    BaitcoinAPIHandler.mining_transport = service
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        status, template = post(
            base + "/api/v1/mining/template",
            {"miner_id": "miner-http", "payout_script_hex": "7061796f7574"},
            {"X-Mining-Client": "test-client"},
        )
        assert status == 201
        assert template["network"] == "regtest"
        assert template["height"] == 1

        base_hash = bytes.fromhex(template["base_hash"])
        consensus = chain.consensus
        nonce = 11
        tensor = consensus.generate_tensor_commitment(base_hash, nonce)
        proof = consensus.generate_zk_proof(base_hash, tensor, nonce)
        payload = {
            "template_id": template["template_id"],
            "miner_id": "miner-http",
            "nonce": nonce,
            "tensor_commitment": tensor.hex(),
            "proof_hash": proof.hex(),
        }
        status, share = post(base + "/api/v1/mining/share", payload)
        assert status == 200
        assert share["status"] == "accepted"
        assert share["attestation"] == "share-only-no-payout"

        status, duplicate = post(base + "/api/v1/mining/share", payload)
        assert status == 200
        assert duplicate["status"] == "duplicate"
        assert duplicate["share_id"] == share["share_id"]
        assert chain.height == 0
    finally:
        server.shutdown()
        server.server_close()
        BaitcoinAPIHandler.mining_transport = previous


def test_http_candidate_block_is_validated_idempotently_without_application():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    service = MiningTransportService(
        chain,
        network="regtest",
        chain_id="transport-test",
        share_target=2**256 - 1,
    )
    previous = BaitcoinAPIHandler.mining_transport
    server = create_app(host="127.0.0.1", port=0)
    BaitcoinAPIHandler.mining_transport = service
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        _, template = post(
            base + "/api/v1/mining/template",
            {"miner_id": "miner-http", "payout_script_hex": "7061796f7574"},
        )
        candidate = copy.deepcopy(service.manager._templates[template["template_id"]].block)
        assert chain.consensus.mine_block(candidate, max_iterations=1) is True
        candidate.finalize()
        payload = {"template_id": template["template_id"], "block": candidate.to_dict()}

        status, result = post(base + "/api/v1/mining/block", payload)
        assert status == 200
        assert result["status"] == "accepted"
        assert result["validation"]["valid"] is True
        assert result["attestation"] == "candidate-only-no-application"

        status, duplicate = post(base + "/api/v1/mining/block", payload)
        assert status == 200
        assert duplicate["status"] == "duplicate"
        assert duplicate["block_hash"] == result["block_hash"]
        assert chain.height == 0

        tampered = copy.deepcopy(payload)
        tampered["block"]["header"]["nonce"] += 1
        status, rejected = post(base + "/api/v1/mining/block", tampered)
        assert status == 400
        assert rejected["status"] == "rejected"
    finally:
        server.shutdown()
        server.server_close()
        BaitcoinAPIHandler.mining_transport = previous


def test_disabled_http_transport_returns_503():
    previous = BaitcoinAPIHandler.mining_transport
    server = create_app(host="127.0.0.1", port=0)
    BaitcoinAPIHandler.mining_transport = None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_address[1]}/api/v1/mining/share",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request, timeout=3)
        assert exc.value.code == 503
    finally:
        server.shutdown()
        server.server_close()
        BaitcoinAPIHandler.mining_transport = previous


def test_rate_limit_is_enforced_before_template_creation():
    now = [1000.0]
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    service = MiningTransportService(
        chain,
        network="testnet",
        chain_id="transport-test",
        max_requests=1,
        clock=lambda: now[0],
    )
    service.issue_template(
        miner_id="miner-a",
        payout_script_hex="01",
        client_id="client-a",
    )
    with pytest.raises(PermissionError, match="rate limit"):
        service.issue_template(
            miner_id="miner-a",
            payout_script_hex="01",
            client_id="client-a",
        )
