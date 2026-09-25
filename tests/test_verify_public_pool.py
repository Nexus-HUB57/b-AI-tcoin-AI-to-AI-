from __future__ import annotations

import json
import sys

from scripts import verify_public_pool


HASH_A = "a" * 64
HASH_B = "b" * 64


def run_main(monkeypatch, origins, responses, require_tip_hash=False):
    def fake_get_json(url):
        for origin, payload in responses.items():
            if url.startswith(origin):
                return payload
        raise AssertionError(f"unexpected URL: {url}")

    argv = ["verify_public_pool.py"]
    for origin in origins:
        argv.extend(["--api", origin])
    argv.extend(["--min-peers", "3"])
    if require_tip_hash:
        argv.append("--require-tip-hash")
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(verify_public_pool, "get_json", fake_get_json)
    return verify_public_pool.main()


def node_responses(origin, tip_hash=HASH_A):
    return {
        f"{origin}/api/v1/status": {
            "chain_height": 10,
            "tip_hash": tip_hash,
            "chain_valid": True,
        },
        f"{origin}/api/v1/p2p/status": {
            "running": True,
            "peer_count": 3,
            "handshake_peers": 3,
            "attestation": "transport-only",
        },
    }


def test_rejects_duplicate_origins_after_normalization(monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "verify_public_pool.py",
        "--api", "https://NODE-A.test/api/",
        "--api", "https://node-a.test:443/api",
        "--api", "https://node-b.test/api",
    ])
    try:
        verify_public_pool.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("duplicate origins were not rejected")


def test_accepts_matching_tip_hashes(monkeypatch, capsys):
    origins = ["https://node-a.test/api", "https://node-b.test/api", "https://node-c.test/api"]
    responses = {}
    for origin in origins:
        responses.update(node_responses(origin))
    assert run_main(monkeypatch, origins, responses, require_tip_hash=True) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "GO"
    assert result["tip_hash_verified"] is True


def test_rejects_divergent_tip_hashes(monkeypatch, capsys):
    origins = ["https://node-a.test/api", "https://node-b.test/api", "https://node-c.test/api"]
    responses = {}
    for index, origin in enumerate(origins):
        responses.update(node_responses(origin, HASH_B if index == 2 else HASH_A))
    assert run_main(monkeypatch, origins, responses, require_tip_hash=True) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "NO-GO"
    assert any("tip hashes diverge" in failure for failure in result["failures"])


def test_strict_mode_rejects_missing_tip_hash(monkeypatch, capsys):
    origins = ["https://node-a.test/api", "https://node-b.test/api", "https://node-c.test/api"]
    responses = {}
    for origin in origins:
        responses.update(node_responses(origin))
        responses[f"{origin}/api/v1/status"].pop("tip_hash")
    assert run_main(monkeypatch, origins, responses, require_tip_hash=True) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "NO-GO"
    assert any("tip_hash is required" in failure for failure in result["failures"])
