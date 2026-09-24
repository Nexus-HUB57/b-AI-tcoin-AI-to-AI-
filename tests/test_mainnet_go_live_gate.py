import json

import pytest

from main_daemon import load_p2p_seeds


def test_mainnet_seeds_require_three_external_hosts():
    assert load_p2p_seeds("seed-a.example:18444,seed-b.example:18444,seed-c.example:18444") == [
        ("seed-a.example", 18444),
        ("seed-b.example", 18444),
        ("seed-c.example", 18444),
    ]


@pytest.mark.parametrize(
    "value",
    [
        "",
        "127.0.0.1:18444,seed-b.example:18444,seed-c.example:18444",
        "seed-a.example:18444,seed-b.example:18444",
        "seed-a.example:18444,seed-a.example:18444,seed-b.example:18444",
    ],
)
def test_mainnet_seeds_reject_unsafe_or_insufficient_values(value):
    with pytest.raises((RuntimeError, ValueError)):
        load_p2p_seeds(value)


def test_manifest_is_explicitly_not_deployed_until_evidence_exists():
    with open("deploy/mainnet-addresses.json", encoding="utf-8") as handle:
        manifest = json.load(handle)
    assert manifest["chain_id"] == 1
    assert manifest["deployed_at"] is None
    assert manifest["deploy_tx_hash"] is None
    assert manifest["uniswap_v3"]["pool_wbait_weth"]["address"] is None
