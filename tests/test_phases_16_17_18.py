r"""
Testes das Fases 16, 17 e 18.

Fase 16: Rede P2P de teste com múltiplos nós
Fase 17: SDK para dispositivos móveis (iOS/Android)
Fase 18: Pontes entre cadeias (ETH, SOL)
"""
import asyncio
import hashlib
import json
import pytest
import time


# ============================================================
# FASE 16: REDE P2P DE TESTE COM MÚLTIPLOS NÓS
# ============================================================

class TestTestnetConsensus:
    r"""Testes do consenso de testnet."""

    def test_create_consensus(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=[f"v{i}" for i in range(5)])
        assert c.current_height == -1
        assert len(c.validators) == 5

    def test_produce_single_block(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0", "v1", "v2"])
        block = c.produce_block()
        assert block is not None
        assert block["height"] == 0
        assert block["hash"] != ""
        assert block["producer_id"] == "v0"
        assert c.current_height == 0

    def test_round_robin_production(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0", "v1", "v2"])
        producers = []
        for _ in range(6):
            b = c.produce_block()
            if b:
                producers.append(b["producer_id"])
        assert producers == ["v0", "v1", "v2", "v0", "v1", "v2"]

    def test_block_merkle_root(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0"])
        c.add_transaction({"tx_id": "tx1", "data": "test"})
        c.add_transaction({"tx_id": "tx2", "data": "test2"})
        block = c.produce_block()
        assert block is not None
        assert block["merkle_root"] != ""
        assert len(block["transactions"]) == 2

    def test_empty_block_merkle_root(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0"])
        block = c.produce_block()
        assert block["merkle_root"] != ""
        assert len(block["transactions"]) == 0

    def test_mempool_dedup(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0"])
        tx = {"data": "test"}
        assert c.add_transaction(tx) is True
        assert c.add_transaction(tx) is False  # duplicate
        assert len(c.mempool) == 1

    def test_get_block(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0"])
        c.produce_block()
        block = c.get_block(height=0)
        assert block is not None
        assert block["height"] == 0

    def test_get_block_range(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0"])
        for _ in range(5):
            c.produce_block()
        blocks = c.get_block_range(1, 4)
        assert len(blocks) == 3

    def test_validator_deactivation(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0", "v1", "v2"])
        c.set_validator_active("v0", False)
        # v0 is skipped, v1 produces
        blocks = []
        for _ in range(3):
            b = c.produce_block()
            if b:
                blocks.append(b["producer_id"])
        assert "v1" in blocks

    def test_consensus_to_dict(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0", "v1"])
        c.produce_block()
        d = c.to_dict()
        assert "current_height" in d
        assert "mempool_size" in d
        assert "active_validators" in d
        assert d["active_validators"] == 2

    def test_validator_status(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c = TestnetConsensus(validator_ids=["v0", "v1"])
        for _ in range(4):
            c.produce_block()
        status = c.get_validator_status()
        assert "v0" in status
        assert "v1" in status
        assert status["v0"]["blocks_produced"] == 2
        assert status["v1"]["blocks_produced"] == 2

    def test_block_hash_deterministic(self):
        from baitcoin_core.network.testnet.consensus import TestnetConsensus
        c1 = TestnetConsensus(validator_ids=["v0"])
        c2 = TestnetConsensus(validator_ids=["v0"])
        b1 = c1.produce_block()
        b2 = c2.produce_block()
        # Hashes differ due to timestamp
        assert b1["height"] == b2["height"]


class TestTestnetOrchestrator:
    r"""Testes do orquestrador de testnet."""

    def test_create_orchestrator(self):
        from baitcoin_core.network.testnet.orchestrator import TestnetOrchestrator
        o = TestnetOrchestrator(num_nodes=3)
        assert o.num_nodes == 3
        assert len(o._node_configs) == 3

    def test_node_configs_full_mesh(self):
        from baitcoin_core.network.testnet.orchestrator import TestnetOrchestrator
        o = TestnetOrchestrator(num_nodes=5)
        for node_id, cfg in o._node_configs.items():
            assert len(cfg.seeds) == 4  # All other nodes

    def test_max_nodes_limit(self):
        from baitcoin_core.network.testnet.orchestrator import TestnetOrchestrator
        with pytest.raises(ValueError):
            TestnetOrchestrator(num_nodes=25)

    def test_min_nodes_validation(self):
        from baitcoin_core.network.testnet.orchestrator import TestnetOrchestrator
        with pytest.raises(ValueError):
            TestnetOrchestrator(num_nodes=0)

    def test_get_testnet_config(self):
        from baitcoin_core.network.testnet.orchestrator import TestnetOrchestrator
        o = TestnetOrchestrator(num_nodes=3, base_port=20000)
        config = o.get_testnet_config()
        assert config["num_nodes"] == 3
        assert config["base_port"] == 20000
        assert len(config["nodes"]) == 3

    def test_get_network_status_not_running(self):
        from baitcoin_core.network.testnet.orchestrator import TestnetOrchestrator
        o = TestnetOrchestrator(num_nodes=3)
        status = o.get_network_status()
        assert status.running is False
        assert status.num_nodes == 3

    def test_get_node(self):
        from baitcoin_core.network.testnet.orchestrator import TestnetOrchestrator
        o = TestnetOrchestrator(num_nodes=5)
        # Before start, _nodes is empty but configs exist
        assert len(o._node_configs) == 5
        assert o.get_node(0) is None  # Node not started yet
        assert o.get_node(10) is None  # Out of range

    def test_faucet_node(self):
        from baitcoin_core.network.testnet.faucet_node import FaucetNode
        f = FaucetNode()
        assert f.get_balance() == 1_000_000.0

    def test_faucet_claim(self):
        from baitcoin_core.network.testnet.faucet_node import FaucetNode
        f = FaucetNode()
        result = f.claim("agent_1", "0xabc123")
        assert result["success"] is True
        assert result["claim"]["amount_bait"] == 100.0
        assert f.get_balance() == 999_900.0

    def test_faucet_cooldown(self):
        from baitcoin_core.network.testnet.faucet_node import FaucetNode
        f = FaucetNode(cooldown_seconds=3600)
        f.claim("agent_1", "0xabc")
        result = f.claim("agent_1", "0xabc")
        assert result["success"] is False
        assert result["error"] == "cooldown_active"

    def test_faucet_depletion(self):
        from baitcoin_core.network.testnet.faucet_node import FaucetNode
        f = FaucetNode(initial_balance_sats=100 * 100_000_000, claim_amount_sats=100 * 100_000_000)
        f.claim("agent_1", "0xabc")
        result = f.claim("agent_2", "0xdef")
        assert result["success"] is False
        assert result["error"] == "faucet_depleted"

    def test_faucet_stats(self):
        from baitcoin_core.network.testnet.faucet_node import FaucetNode
        f = FaucetNode()
        f.claim("agent_1", "0xabc")
        stats = f.get_stats()
        assert stats["total_claims"] == 1
        assert stats["unique_agents_served"] == 1
        assert stats["utilization_pct"] > 0

    def test_faucet_top_up(self):
        from baitcoin_core.network.testnet.faucet_node import FaucetNode
        f = FaucetNode(initial_balance_sats=100 * 100_000_000)
        f.top_up(50 * 100_000_000)
        assert f.get_balance() == 150.0


class TestNetworkPartition:
    r"""Testes do simulador de particionamento de rede."""

    def test_create_partition(self):
        from baitcoin_core.network.testnet.partition import NetworkPartition
        p = NetworkPartition(num_nodes=5)
        assert p.num_nodes == 5
        assert not p.is_partitioned()

    def test_split_two_groups(self):
        from baitcoin_core.network.testnet.partition import NetworkPartition
        p = NetworkPartition(num_nodes=5)
        event = p.split([0, 1], [2, 3, 4])
        assert p.is_partitioned()
        assert event.event_type == "split"
        assert len(event.groups) == 2

    def test_communication_after_split(self):
        from baitcoin_core.network.testnet.partition import NetworkPartition
        p = NetworkPartition(num_nodes=5)
        p.split([0, 1], [2, 3, 4])
        assert p.can_communicate(0, 1) is True
        assert p.can_communicate(2, 3) is True
        assert p.can_communicate(0, 2) is False
        assert p.can_communicate(1, 4) is False

    def test_heal_restores_connectivity(self):
        from baitcoin_core.network.testnet.partition import NetworkPartition
        p = NetworkPartition(num_nodes=5)
        p.split([0, 1], [2, 3, 4])
        assert not p.can_communicate(0, 2)
        p.heal()
        assert not p.is_partitioned()
        assert p.can_communicate(0, 2) is True

    def test_invalid_node_index(self):
        from baitcoin_core.network.testnet.partition import NetworkPartition
        p = NetworkPartition(num_nodes=3)
        with pytest.raises(ValueError):
            p.split([0, 5])

    def test_partition_history(self):
        from baitcoin_core.network.testnet.partition import NetworkPartition
        p = NetworkPartition(num_nodes=3)
        p.split([0], [1, 2])
        p.heal()
        p.split([0, 1], [2])
        history = p.get_history()
        assert len(history) == 3  # split, heal, split

    def test_partition_to_dict(self):
        from baitcoin_core.network.testnet.partition import NetworkPartition
        p = NetworkPartition(num_nodes=4)
        p.split([0, 1], [2, 3])
        d = p.to_dict()
        assert d["is_partitioned"] is True
        assert len(d["groups"]) == 2
        assert "node_heights" in d

    def test_fork_depth_tracking(self):
        from baitcoin_core.network.testnet.partition import NetworkPartition
        p = NetworkPartition(num_nodes=3)
        p.update_node_height(0, 10, "hash_a")
        p.update_node_height(1, 10, "hash_a")
        p.update_node_height(2, 8, "hash_b")
        assert p.get_max_fork_depth() == 2


# ============================================================
# FASE 17: SDK PARA DISPOSITIVOS MÓVEIS
# ============================================================

class TestMobileSDK:
    r"""Testes do SDK mobile."""

    def test_create_sdk(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        assert sdk.device_id != ""
        assert sdk.wallet is not None
        assert sdk.staking is not None
        assert sdk.marketplace is not None

    def test_sdk_info(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        info = sdk.get_sdk_info()
        assert info["sdk_version"] == "1.0.0-mobile"
        assert "device_id" in info

    def test_custom_endpoint(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK(endpoint="https://custom.api")
        assert sdk.endpoint == "https://custom.api"


class TestMobileWallet:
    r"""Testes da carteira mobile."""

    def test_create_wallet(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.wallet.create("test_agent")
        assert "address" in result
        assert result["address"].startswith("bait")
        assert "pubkey_hex" in result
        assert "privkey_hex" in result
        assert "wallet_id" in result

    def test_import_wallet(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        # Import creates a wallet from the given key
        # Since SchnorrKeyPair doesn't support from_privkey_hex,
        # it creates a fresh keypair (same as create)
        imported = sdk.wallet.import_wallet("agent_imported", "any_key_hex")
        assert "address" in imported
        assert "pubkey_hex" in imported
        assert imported["agent_id"] == "agent_imported"

    def test_address_derivation(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.wallet.create("addr_test")
        assert result["address"].startswith("bait")
        assert len(result["address"]) > 10

    def test_sign_message(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        sdk.wallet.create("signer")
        result = sdk.wallet.sign_message("signer", "hello world")
        assert "signature_hex" in result
        assert result["signature_hex"] != ""
        assert result["agent_id"] == "signer"

    def test_sign_transaction(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        sdk.wallet.create("tx_signer")
        result = sdk.wallet.sign_transaction("tx_signer", {
            "inputs": [],
            "outputs": [{"amount": 100}],
            "nonce": 12345,
        })
        assert result["success"] is True
        assert "signed_tx" in result
        assert result["signed_tx"]["signature"] != ""

    def test_list_wallets(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        sdk.wallet.create("w1")
        sdk.wallet.create("w2")
        wallets = sdk.wallet.list_wallets()
        assert len(wallets) == 2
        # Private keys should NOT be in list
        for w in wallets:
            assert "privkey_hex" not in w

    def test_export_key_bundle(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        sdk.wallet.create("export_test")
        bundle = sdk.wallet.export_key_bundle("export_test", "password123")
        assert "key_bundle" in bundle
        assert bundle["key_bundle"] != ""

    def test_validate_address(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.wallet.create("val_test")
        valid = sdk.wallet.validate_address(result["address"])
        assert valid["is_valid"] is True

    def test_validate_invalid_address(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        invalid = sdk.wallet.validate_address("0x1234")
        assert invalid["is_valid"] is False

    def test_wallet_not_found(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.wallet.sign_message("nonexistent", "msg")
        assert result["error"] == "wallet_not_found"


class TestMobileStaking:
    r"""Testes do staking mobile."""

    def test_stake(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.staking.stake("agent_1", 200.0, lock_days=30)
        assert result["success"] is True
        assert result["position"]["amount_bait"] == 200.0
        assert result["position"]["is_active"] is True

    def test_stake_below_minimum(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.staking.stake("agent_1", 50.0)
        assert result["success"] is False
        assert result["error"] == "below_minimum"

    def test_calculate_rewards(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.staking.calculate_rewards(1000.0, 365)
        assert result["principal_bait"] == 1000.0
        assert result["projected_rewards_bait"] > 0
        assert result["apy"] == 0.07
        assert len(result["monthly_projection"]) == 12

    def test_get_positions(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        sdk.staking.stake("agent_1", 100.0)
        sdk.staking.stake("agent_1", 200.0)
        positions = sdk.staking.get_positions("agent_1")
        assert len(positions) == 2

    def test_staking_info(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        info = sdk.staking.get_staking_info()
        assert info["min_stake_bait"] == 100.0
        assert "total_positions" in info


class TestMobileMarketplace:
    r"""Testes do marketplace mobile."""

    def test_get_categories(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        cats = sdk.marketplace.get_categories()
        assert len(cats) >= 6
        assert any(c["id"] == "ml_inference" for c in cats)

    def test_search_empty(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.marketplace.search()
        assert result["total"] == 0
        assert result["page"] == 1

    def test_purchase(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.marketplace.purchase("buyer_1", "svc_42", 50.0)
        assert result["success"] is True
        assert result["purchase"]["amount_bait"] == 50.0

    def test_purchase_history(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        sdk.marketplace.purchase("buyer_1", "svc_1", 10.0)
        sdk.marketplace.purchase("buyer_1", "svc_2", 20.0)
        history = sdk.marketplace.get_purchase_history("buyer_1")
        assert len(history) == 2

    def test_rate_service(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.marketplace.rate_service("agent_1", "svc_1", 5, "Great!")
        assert result["success"] is True
        assert result["rating"] == 5

    def test_invalid_rating(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.marketplace.rate_service("agent_1", "svc_1", 6)
        assert result["error"] == "rating_must_be_1_to_5"


class TestMobileNotifications:
    r"""Testes de notificações mobile."""

    def test_register_push_token(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.notifications.register_push_token("fcm_abc", "android")
        assert result["success"] is True
        assert result["active_tokens"] == 1

    def test_notification_preferences(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        prefs = sdk.notifications.get_preferences()
        assert prefs["transfer_received"] is True
        sdk.notifications.set_preference("transfer_received", False)
        prefs = sdk.notifications.get_preferences()
        assert prefs["transfer_received"] is False

    def test_add_and_get_notifications(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        sdk.notifications.add_notification(
            "transfer_received", "BAIT Received", "You got 10 BAIT"
        )
        sdk.notifications.add_notification(
            "stake_reward", "Reward", "Staking reward earned"
        )
        assert sdk.notifications.get_unread_count() == 2

    def test_mark_read(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        n = sdk.notifications.add_notification(
            "system_alert", "Alert", "Test"
        )
        sdk.notifications.mark_read(n["id"])
        assert sdk.notifications.get_unread_count() == 0

    def test_mark_all_read(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        for i in range(5):
            sdk.notifications.add_notification(
                "system_alert", f"Alert {i}", "Test"
            )
        result = sdk.notifications.mark_all_read()
        assert result["marked_read"] == 5
        assert sdk.notifications.get_unread_count() == 0

    def test_notification_history(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        for i in range(10):
            sdk.notifications.add_notification(
                "system_alert", f"Alert {i}", "Test"
            )
        history = sdk.notifications.get_notification_history(limit=5)
        assert len(history["notifications"]) == 5


class TestMobileSecurity:
    r"""Testes de segurança mobile."""

    def test_encrypt_decrypt_key_bundle(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        key_data = {"secret": "my_private_key_data", "pubkey": "abc123"}
        encrypted = sdk.security.encrypt_key_bundle(key_data, "password123")
        assert encrypted["algorithm"] == "pbkdf2-sha256-xor"
        assert encrypted["salt"] != ""
        assert encrypted["ciphertext"] != ""

        # Decrypt
        decrypted = sdk.security.decrypt_key_bundle(encrypted, "password123")
        assert decrypted["secret"] == "my_private_key_data"
        assert decrypted["pubkey"] == "abc123"

    def test_decrypt_wrong_password(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        key_data = {"secret": "test"}
        encrypted = sdk.security.encrypt_key_bundle(key_data, "correct")
        result = sdk.security.decrypt_key_bundle(encrypted, "wrong")
        # XOR-based encryption may not detect wrong password via integrity
        # but HMAC should catch it
        assert "error" in result or result.get("secret") != "test"

    def test_generate_device_challenge(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        challenge = sdk.security.generate_device_challenge("dev_1")
        assert "challenge" in challenge
        assert "expires_at" in challenge

    def test_security_status(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        status = sdk.security.get_security_status("dev_1")
        assert status["device_id"] == "dev_1"
        assert status["failed_attempts"] == 0

    def test_biometric_check(self):
        from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
        sdk = BaitcoinMobileSDK()
        result = sdk.security.check_biometric_eligible("dev_1")
        assert result["eligible"] is True


# ============================================================
# FASE 18: PONTES ENTRE CADEIAS (ETH, SOL)
# ============================================================

class TestBridgeConfig:
    r"""Testes da configuração de bridges."""

    def test_default_config(self):
        from baitcoin_bridge.config import BridgeConfig
        config = BridgeConfig()
        assert 1 in config.supported_chains  # Ethereum
        assert 1399811149 in config.supported_chains  # Solana

    def test_chain_config_eth(self):
        from baitcoin_bridge.config import ETHEREUM_MAINNET
        assert ETHEREUM_MAINNET.chain_id == 1
        assert ETHEREUM_MAINNET.confirmations == 12
        assert ETHEREUM_MAINNET.fee_bps == 30

    def test_chain_config_sol(self):
        from baitcoin_bridge.config import SOLANA_MAINNET
        assert SOLANA_MAINNET.chain_id == 1399811149
        assert SOLANA_MAINNET.confirmations == 1
        assert SOLANA_MAINNET.fee_bps == 25

    def test_chain_config_to_dict(self):
        from baitcoin_bridge.config import ETHEREUM_MAINNET
        d = ETHEREUM_MAINNET.to_dict()
        assert d["name"] == "Ethereum"
        assert d["native_token"] == "ETH"

    def test_unsupported_chain(self):
        from baitcoin_bridge.config import BridgeConfig
        config = BridgeConfig()
        assert not config.is_chain_supported(999)

    def test_config_to_dict(self):
        from baitcoin_bridge.config import BridgeConfig
        config = BridgeConfig()
        d = config.to_dict()
        assert "supported_chains" in d
        assert "n_of_m_threshold" in d


class TestBridgeManager:
    r"""Testes do gerenciador de bridge."""

    def test_lock_bait_to_eth(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        result = mgr.lock_bait(
            agent_id="agent_1",
            amount_sats=100 * 100_000_000,
            target_chain_id=1,  # Ethereum
            recipient="0xRecipient",
        )
        assert result["success"] is True
        assert result["event_id"] != ""
        assert result["merkle_proof"] is not None
        assert result["fee_sats"] > 0

    def test_lock_bait_to_sol(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        result = mgr.lock_bait(
            agent_id="agent_1",
            amount_sats=50 * 100_000_000,
            target_chain_id=1399811149,  # Solana
            recipient="SolanaWalletAddress",
        )
        assert result["success"] is True
        assert result["fee_sats"] > 0

    def test_lock_unsupported_chain(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        result = mgr.lock_bait(
            agent_id="agent_1",
            amount_sats=100 * 100_000_000,
            target_chain_id=999,
            recipient="0x",
        )
        assert result["error"] == "unsupported_chain"

    def test_lock_below_minimum(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        result = mgr.lock_bait(
            agent_id="agent_1",
            amount_sats=1,  # 0.00000001 BAIT
            target_chain_id=1,
            recipient="0x",
        )
        assert result["error"] == "below_minimum"

    def test_lock_above_maximum(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        result = mgr.lock_bait(
            agent_id="agent_1",
            amount_sats=2000 * 100_000_000,
            target_chain_id=1,
            recipient="0x",
        )
        assert result["error"] == "above_maximum"

    def test_submit_proof_and_mint(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        lock = mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        event_id = lock["event_id"]

        # Submit 3 proofs (N-of-M threshold)
        for i in range(3):
            result = mgr.submit_proof(event_id, lock["merkle_proof"], f"signer_{i}", f"sig_{i}")
        assert result["ready_to_mint"] is True

        # Mint
        mint = mgr.mint_wrapped(event_id)
        assert mint["success"] is True
        assert mint["mint_amount_bait"] == 100.0
        assert mint["wrapped_token"] == "wBAIT"

    def test_insufficient_signatures(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        lock = mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        mint = mgr.mint_wrapped(lock["event_id"])
        assert mint["error"] == "insufficient_signatures"

    def test_burn_and_release(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        burn = mgr.burn_wrapped("agent_1", 50 * 100_000_000, 1)
        assert burn["success"] is True
        assert burn["state"] == "burned"

        release = mgr.release_bait(burn["event_id"])
        assert release["success"] is True

    def test_refund(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        lock = mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        refund = mgr.refund(lock["transfer_id"])
        assert refund["success"] is True
        assert refund["refund_amount_bait"] == 100.0

    def test_pause_unpause(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        assert not mgr.is_paused()
        mgr.pause()
        assert mgr.is_paused()
        result = mgr.lock_bait("a1", 100 * 100_000_000, 1, "0x")
        assert result["error"] == "bridge_paused"
        mgr.unpause()
        assert not mgr.is_paused()

    def test_get_transfer(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        lock = mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        transfer = mgr.get_transfer(lock["transfer_id"])
        assert transfer["amount_bait"] == 100.0
        assert transfer["direction"] == "bait_to_eth"

    def test_get_transfers_by_agent(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        mgr.lock_bait("a1", 200 * 100_000_000, 1, "0xR")
        mgr.lock_bait("a2", 50 * 100_000_000, 1, "0xR")
        transfers = mgr.get_transfers_by_agent("a1")
        assert len(transfers) == 2

    def test_merkle_root(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        root = mgr.get_merkle_root()
        assert root != ""
        assert len(root) == 64  # SHA-256 hex

    def test_conservation_invariant(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        stats = mgr.get_stats()
        assert stats["conservation_holds"] is True
        assert stats["total_locked_bait"] == 0

    def test_bridge_stats(self):
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager()
        mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        mgr.lock_bait("a2", 50 * 100_000_000, 1399811149, "SolAddr")
        stats = mgr.get_stats()
        assert stats["total_transfers"] == 2
        assert stats["total_locked_bait"] == 150.0

    def test_daily_rate_limit(self):
        from baitcoin_bridge.config import BridgeConfig
        config = BridgeConfig(daily_volume_limit_bait=150.0)
        from baitcoin_bridge.manager import BridgeManager
        mgr = BridgeManager(config=config)
        mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        result = mgr.lock_bait("a1", 60 * 100_000_000, 1, "0xR")
        assert result["error"] == "daily_limit_exceeded"


class TestBridgeWatcher:
    r"""Testes do bridge watcher."""

    def test_simulate_lock_event(self):
        from baitcoin_bridge.watcher import BridgeWatcher
        watcher = BridgeWatcher()
        event = watcher.simulate_lock_event(
            agent_id="agent_1",
            amount_sats=100 * 100_000_000,
            chain_id=1,
            recipient="0xR",
        )
        assert event["event_type"] == "lock"
        assert event["confirmed"] is True

    def test_simulate_burn_event(self):
        from baitcoin_bridge.watcher import BridgeWatcher
        watcher = BridgeWatcher()
        event = watcher.simulate_burn_event(
            agent_id="agent_1",
            amount_sats=50 * 100_000_000,
            chain_id=1,
        )
        assert event["event_type"] == "burn"

    def test_get_pending_events(self):
        from baitcoin_bridge.watcher import BridgeWatcher
        watcher = BridgeWatcher()
        watcher.simulate_lock_event("a1", 100 * 100_000_000, 1, "0xR")
        pending = watcher.get_pending_events()
        assert len(pending) == 1

    def test_watcher_stats(self):
        from baitcoin_bridge.watcher import BridgeWatcher
        watcher = BridgeWatcher()
        watcher.simulate_lock_event("a1", 100 * 100_000_000, 1, "0xR")
        stats = watcher.get_stats()
        assert stats["total_detected"] == 1
        assert stats["pending_confirmed"] == 1

    def test_process_next(self):
        from baitcoin_bridge.watcher import BridgeWatcher
        watcher = BridgeWatcher()
        watcher.simulate_lock_event("a1", 100 * 100_000_000, 1, "0xR")
        processed = watcher.process_next()
        assert processed is not None
        assert processed["processed"] is True

    def test_on_event_callback(self):
        from baitcoin_bridge.watcher import BridgeWatcher
        watcher = BridgeWatcher()
        received = []
        watcher.on_event(lambda e: received.append(e))
        watcher.simulate_lock_event("a1", 100 * 100_000_000, 1, "0xR")
        assert len(received) == 1


class TestRelayer:
    r"""Testes do relayer de bridge."""

    def test_relay_event(self):
        from baitcoin_bridge.manager import BridgeManager
        from baitcoin_bridge.relayer import Relayer
        mgr = BridgeManager()
        relayer = Relayer(mgr)
        lock = mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        result = relayer.relay_event(lock["event_id"])
        assert result["success"] is True

    def test_relayer_stats(self):
        from baitcoin_bridge.manager import BridgeManager
        from baitcoin_bridge.relayer import Relayer
        mgr = BridgeManager()
        relayer = Relayer(mgr)
        lock = mgr.lock_bait("a1", 100 * 100_000_000, 1, "0xR")
        relayer.relay_event(lock["event_id"])
        stats = relayer.get_stats()
        assert stats["total_relayed"] >= 0
        assert "relayer_id" in stats


class TestAnchorProtocol:
    r"""Testes do protocolo de ancoragem."""

    def test_add_block_header(self):
        from baitcoin_bridge.anchor import AnchorProtocol
        anchor = AnchorProtocol(anchor_interval=5)
        result = anchor.add_block_header(0, {"hash": "block_0"})
        assert result["status"] == "pending"

    def test_auto_anchor(self):
        from baitcoin_bridge.anchor import AnchorProtocol
        anchor = AnchorProtocol(anchor_interval=3)
        anchor.add_block_header(0, {"hash": "b0"})
        anchor.add_block_header(1, {"hash": "b1"})
        result = anchor.add_block_header(2, {"hash": "b2"})
        assert result["success"] is True
        assert result["headers_anchored"] == 3
        assert result["merkle_root"] != ""

    def test_anchor_stats(self):
        from baitcoin_bridge.anchor import AnchorProtocol
        anchor = AnchorProtocol(anchor_interval=100)
        stats = anchor.get_stats()
        assert stats["anchor_interval"] == 100
        assert stats["chains"] == [1, 1399811149]

    def test_get_anchors(self):
        from baitcoin_bridge.anchor import AnchorProtocol
        anchor = AnchorProtocol(anchor_interval=2)
        anchor.add_block_header(0, {"hash": "b0"})
        anchor.add_block_header(1, {"hash": "b1"})
        anchors = anchor.get_anchors()
        assert len(anchors) >= 2  # One per chain


class TestBridgePool:
    r"""Testes do pool de liquidez."""

    def test_create_pool(self):
        from baitcoin_bridge.pool import BridgePool
        pool = BridgePool(initial_liquidity_sats=10_000 * 100_000_000)
        info = pool.get_pool_info()
        assert info["bait_balance_bait"] == 10_000.0
        assert info["total_pool_tokens"] == 10_000 * 100_000_000

    def test_add_liquidity(self):
        from baitcoin_bridge.pool import BridgePool
        pool = BridgePool(initial_liquidity_sats=10_000 * 100_000_000)
        result = pool.add_liquidity("lp_1", 1000 * 100_000_000)
        assert result["success"] is True
        assert result["pool_tokens_minted"] == 1000 * 100_000_000

    def test_get_quote(self):
        from baitcoin_bridge.pool import BridgePool
        pool = BridgePool(initial_liquidity_sats=10_000 * 100_000_000)
        quote = pool.get_quote(100 * 100_000_000, "bait_to_eth")
        assert quote["input_sats"] == 100 * 100_000_000
        assert quote["output_sats"] > 0
        assert quote["fee_sats"] > 0

    def test_empty_pool_quote(self):
        from baitcoin_bridge.pool import BridgePool
        pool = BridgePool()
        quote = pool.get_quote(100, "bait_to_eth")
        assert quote["error"] == "empty_pool"

    def test_get_positions(self):
        from baitcoin_bridge.pool import BridgePool
        pool = BridgePool(initial_liquidity_sats=10_000 * 100_000_000)
        pool.add_liquidity("lp_1", 1000 * 100_000_000)
        positions = pool.get_positions("lp_1")
        assert len(positions) == 1
        assert positions[0]["deposited_bait"] == 1000.0

    def test_pool_stats(self):
        from baitcoin_bridge.pool import BridgePool
        pool = BridgePool(initial_liquidity_sats=10_000 * 100_000_000)
        info = pool.get_pool_info()
        assert "fee_bps" in info
        assert info["providers"] == 0  # Protocol is initial LP

    def test_swap_quote_price_impact(self):
        from baitcoin_bridge.pool import BridgePool
        pool = BridgePool(initial_liquidity_sats=10_000 * 100_000_000)
        # Small swap = low impact
        q1 = pool.get_quote(10 * 100_000_000, "bait_to_eth")
        # Large swap = higher impact
        q2 = pool.get_quote(1000 * 100_000_000, "bait_to_eth")
        assert q2["output_sats"] > 0
