r"""
Smoke Tests Avancados b'AI'tcoin — Validacao de edge cases e caminhos criticos.

Complementa test_smoke.py com:
- Validacao de invariantes (supply, halving, endereco)
- Edge cases de assinatura (chave 0, mensagem vazia, etc)
- Mempool boundary (capacidade, eviccao, expiracao)
- Token edge cases (burn acima do saldo, transfer para si mesmo)
- zkML edge cases (proof vazio, tensor vazio)
- DeFi edge cases (unstake sem stake, double stake)
- Network edge cases (peer duplicado, broadcast vazio)
- API server endpoints
- Configuracao e constantes

Regra: Cada teste <2s. Total suite <30s.
"""

import time
import hashlib
import tempfile
import shutil
import pytest
from baitcoin_core.blockchain.block import (
    Block, BlockHeader, Transaction, TransactionOutput, TransactionInput,
)
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.blockchain.mempool import Mempool
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
from baitcoin_core.consensus.zkml_real.tensor_commitment import TensorCommitmentScheme
from baitcoin_core.consensus.zkml_real.verifier import ZkMLVerifier
from baitcoin_core.consensus.pouw import PoUWValidator
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_core.network.p2p import P2PNetwork, MessageType
from baitcoin_core.ecosystem import EcosystemNode
from baitcoin_token.erc20_like.bait_token import BAITToken
from baitcoin_token.tokenomics.schedule import EmissionSchedule
from baitcoin_token.governance.governor import Governor
from baitcoin_bank.staking.pool import StakingPool
from baitcoin_bank.lending.engine import LendingEngine
from baitcoin_bank.defi_core.vault import Vault, VaultConfig, StrategyType
from baitcoin_ai.agent_protocol.registry import AgentRegistry, AgentCapability
from baitcoin_ai.oracle.feed import PriceOracle
from baitcoin_ai.marketplace.services import AIMarketplace, ServiceCategory
from baitcoin_faucet.faucet import BAITFaucet


# ============================================================
# BLOCKCHAIN INVARIANTS
# ============================================================
class TestBlockchainInvariants:
    r"""Testa invariantes fundamentais da blockchain."""

    def test_genesis_block_is_immutable(self):
        r"""Genesis block tem campos fixos."""
        bc = Blockchain()
        genesis = bc.chain[0]
        assert genesis.index == 0
        assert genesis.header.prev_block_hash == b"\x00" * 32
        assert genesis.coinbase_tx is not None

    def test_chain_height_equals_len_minus_one(self):
        r"""height == len(chain) - 1."""
        bc = Blockchain()
        assert bc.height == 0
        kp = SchnorrKeyPair()
        bc.mine_block("inv_miner", kp.pub_bytes)
        assert bc.height == 1
        assert bc.height == len(bc.chain) - 1

    def test_block_hash_is_32_bytes(self):
        r"""Hash do bloco tem sempre 32 bytes."""
        bc = Blockchain()
        for block in bc.chain:
            assert len(block.block_hash) == 32

    def test_merkle_root_empty_txs(self):
        r"""Merkle root de bloco vazio e zero hash."""
        block = Block(index=99)
        root = block.compute_merkle_root()
        assert root == b"\x00" * 32

    def test_merkle_root_single_tx(self):
        r"""Merkle root de bloco com 1 tx = hash da tx."""
        tx = Transaction(
            tx_type="coinbase",
            outputs=[TransactionOutput(amount_sats=100, script_pubkey=b"pk")],
        )
        block = Block(index=99, transactions=[tx])
        root = block.compute_merkle_root()
        assert root == tx.tx_id

    def test_block_validate_wrong_prev_hash(self):
        r"""Bloco com prev_hash errado e rejeitado."""
        block = Block(index=1, header=BlockHeader(prev_block_hash=b"wrong" * 4))
        assert not block.validate(b"correct" * 4)

    def test_difficulty_adjustment_interval(self):
        r"""Constantes de dificuldade estao corretas."""
        assert Blockchain.DIFFICULTY_ADJUSTMENT_INTERVAL == 2016
        assert Blockchain.HALVING_INTERVAL == 210_000
        assert Blockchain.INITIAL_REWARD_SATS == 50 * 100_000_000


# ============================================================
# CRYPTOGRAPHY EDGE CASES
# ============================================================
class TestCryptographyEdgeCases:
    r"""Edge cases de Schnorr/BIP-340."""

    def test_sign_empty_message(self):
        r"""Assina mensagem vazia."""
        kp = SchnorrKeyPair()
        sig = kp.sign(b"")
        assert sig.verify(kp.pub_bytes, b"")
        assert len(sig.raw) == 64

    def test_sign_large_message(self):
        r"""Assina mensagem de 1MB."""
        kp = SchnorrKeyPair()
        msg = b"x" * 1_000_000
        sig = kp.sign(msg)
        assert sig.verify(kp.pub_bytes, msg)

    def test_pubkey_is_32_bytes(self):
        r"""Chave publica tem exatamente 32 bytes (x-only)."""
        kp = SchnorrKeyPair()
        assert len(kp.pub_bytes) == 32

    def test_private_key_in_range(self):
        r"""Chave privada esta em [1, n-1]."""
        kp = SchnorrKeyPair()
        assert 1 <= kp.priv_key < kp.n

    def test_deterministic_keypair(self):
        r"""Mesma chave privada gera mesmo pubkey."""
        k1 = SchnorrKeyPair(private_key=12345)
        k2 = SchnorrKeyPair(private_key=12345)
        assert k1.public_key_hex == k2.public_key_hex
        assert k1.private_key_hex == k2.private_key_hex

    def test_different_keys_different_pubkeys(self):
        r"""Chaves diferentes geram pubkeys diferentes."""
        keys = [SchnorrKeyPair() for _ in range(50)]
        pubkeys = set(k.public_key_hex for k in keys)
        assert len(pubkeys) == 50  # Todas unicas


# ============================================================
# MEMPOOL EDGE CASES
# ============================================================
class TestMempoolEdgeCases:
    r"""Edge cases do mempool."""

    def test_empty_mempool_get(self):
        r"""Mempool vazio retorna lista vazia."""
        mp = Mempool()
        assert mp.get_transactions() == []

    def test_purge_expired_empty(self):
        r"""Purge de mempool vazio retorna 0."""
        mp = Mempool()
        assert mp.purge_expired() == 0

    def test_get_agent_txs_empty(self):
        r"""Tx de agente inexistente retorna vazio."""
        mp = Mempool()
        assert mp.get_agent_txs("nonexistent") == []

    def test_max_size_constant(self):
        r"""Constantes do mempool sao razoaveis."""
        assert Mempool.MAX_SIZE >= 10_000
        assert Mempool.MAX_TX_SIZE_BYTES >= 10_000
        assert Mempool.TX_EXPIRY_SECONDS >= 300

    def test_fee_tracking(self):
        r"""Total de fees e rastreado corretamente."""
        mp = Mempool()
        kp = SchnorrKeyPair()
        tx = Transaction(
            tx_type="transfer",
            agent_id="fee_test",
            gas_price=100,
            gas_limit=10,
            outputs=[TransactionOutput(amount_sats=100, script_pubkey=kp.pub_bytes)],
        )
        mp.add_transaction(tx)
        assert mp.total_fees == 1000  # 100 * 10

    def test_stats_counters(self):
        r"""Contadores de stats funcionam."""
        mp = Mempool()
        kp = SchnorrKeyPair()
        for i in range(5):
            tx = Transaction(
                tx_type="transfer",
                agent_id=f"stat_{i}",
                nonce=i,
                gas_price=1,
                gas_limit=1,
                outputs=[TransactionOutput(amount_sats=1, script_pubkey=kp.pub_bytes)],
            )
            mp.add_transaction(tx)
        assert mp._stats["added"] == 5
        mp.remove_transactions([tx.tx_id.hex() for tx in mp.get_transactions(3)])
        assert mp._stats["removed"] == 3


# ============================================================
# TOKEN EDGE CASES
# ============================================================
class TestTokenEdgeCases:
    r"""Edge cases do token BAIT."""

    def test_balance_nonexistent_agent(self):
        r"""Saldo de agente inexistente e 0."""
        token = BAITToken()
        assert token.balance_of("nonexistent") == 0
        assert token.balance_bait("nonexistent") == 0.0

    def test_burn_more_than_balance(self):
        r"""Burn acima do saldo falha."""
        token = BAITToken()
        token.mint("burn_test", 100 * 100_000_000)
        assert not token.burn("burn_test", 200 * 100_000_000)
        assert token.balance_of("burn_test") == 100 * 100_000_000

    def test_transfer_more_than_balance(self):
        r"""Transfer acima do saldo falha."""
        token = BAITToken()
        token.mint("poor_agent", 50 * 100_000_000)
        assert not token.transfer("poor_agent", "rich_agent", 100 * 100_000_000)

    def test_transfer_to_self(self):
        r"""Transferencia para si mesmo."""
        token = BAITToken()
        token.mint("self_agent", 100 * 100_000_000)
        ok = token.transfer("self_agent", "self_agent", 10 * 100_000_000)
        # Saldo final deve ser igual (enviou e recebeu de volta)
        assert token.balance_of("self_agent") == 100 * 100_000_000

    def test_zero_transfer(self):
        r"""Transferencia de valor zero."""
        token = BAITToken()
        token.mint("zero_agent", 100 * 100_000_000)
        # Comportamento pode ser True ou False, nao deve crashar
        result = token.transfer("zero_agent", "dest", 0)
        assert isinstance(result, bool)

    def test_max_supply_constant(self):
        r"""Max supply e 21M BAIT."""
        token = BAITToken()
        assert token.TOTAL_SUPPLY_SATS == 21_000_000 * 100_000_000

    def test_decimals_constant(self):
        r"""Decimais e 8 (sai'toshis)."""
        token = BAITToken()
        assert token.DECIMALS == 8


# ============================================================
# CONSENSUS EDGE CASES
# ============================================================
class TestConsensusEdgeCases:
    r"""Edge cases do consenso zkML."""

    def test_mining_with_very_easy_target(self):
        r"""Mineracao com target muito facil (1 iteracao)."""
        consensus = ZkMLConsensus(target=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
        bc = Blockchain(consensus=consensus)
        kp = SchnorrKeyPair()
        block = bc.mine_block("easy_miner", kp.pub_bytes)
        assert bc.height == 1

    def test_pouw_unknown_type(self):
        r"""PoUW com tipo desconhecido falha."""
        pouw = PoUWValidator()
        result = pouw.submit_work("unknown_type", {}, "agent")
        assert result["valid"] is False
        assert "Unknown" in result["error"]

    def test_pouw_empty_input(self):
        r"""PoUW com input vazio falha."""
        pouw = PoUWValidator()
        result = pouw.submit_work("ml_inference", {}, "agent")
        assert result["valid"] is False

    def test_zkml_proof_stats(self):
        r"""Stats do proof system rastreiam corretamente."""
        ps = ZkMLProofSystem()
        for i in range(5):
            proof = ps.generate_proof(
                prover_id=f"p_{i}", model_id="m",
                input_data=b"in", output_data=b"out",
                block_hash="block",
            )
            ps.verify_proof(proof)
        stats = ps.get_stats()
        assert stats["proofs_generated"] == 5
        assert stats["proofs_verified"] == 5
        assert stats["proofs_failed"] == 0


# ============================================================
# DEFI EDGE CASES
# ============================================================
class TestDeFiEdgeCases:
    r"""Edge cases de DeFi."""

    def test_unstake_without_stake(self):
        r"""Unstake sem stake retorna 0."""
        pool = StakingPool()
        result = pool.unstake("nonexistent")
        assert result == 0

    def test_double_stake_same_agent(self):
        r"""Segundo stake do mesmo agente falha."""
        pool = StakingPool()
        pool.stake("double_staker", 1000 * 100_000_000)
        assert not pool.stake("double_staker", 1000 * 100_000_000)

    def test_stake_below_minimum(self):
        r"""Stake abaixo do minimo falha."""
        pool = StakingPool()
        assert not pool.stake("small_staker", 1)

    def test_vault_withdraw_more_than_deposited(self):
        r"""Saque acima do depositado retorna o total disponivel."""
        cfg = VaultConfig(agent_id="vault_edge")
        vault = Vault(cfg)
        vault.deposit(100 * 100_000_000, StrategyType.HODL)
        result = vault.withdraw(200 * 100_000_000)
        assert result == 100 * 100_000_000  # Retorna tudo disponivel

    def test_lending_no_offers(self):
        r"""Market rate sem ofertas retorna 0."""
        engine = LendingEngine()
        assert engine.get_market_rate() == 0.0

    def test_governance_quorum(self):
        r"""Governancia rastreia propostas e votos."""
        gov = Governor(21_000_000 * 100_000_000)
        gov.create_proposal("prop_q", "Test quorum", "proposer")
        gov.vote("prop_q", "voter1", True, 100 * 100_000_000)
        info = gov.to_dict()
        assert info["total_proposals"] >= 1


# ============================================================
# NETWORK EDGE CASES
# ============================================================
class TestNetworkEdgeCases:
    r"""Edge cases da rede P2P."""

    def test_duplicate_peer(self):
        r"""Peer duplicado e ignorado (mesmo ID)."""
        net = P2PNetwork(listen_port=18450)
        net.add_peer("192.168.1.1", 18444, "agent_1")
        count_before = len(net.peers)
        net.add_peer("192.168.1.1", 18444, "agent_1")
        # Peer ID e hash do endereco:porta, entao mesmo endereco = mesmo ID
        # Se o peer_id for o mesmo, o dict sobrescreve
        assert len(net.peers) == count_before  # Nao duplicou

    def test_remove_nonexistent_peer(self):
        r"""Remover peer inexistente nao causa erro."""
        net = P2PNetwork(listen_port=18451)
        net.remove_peer("nonexistent")  # Nao deve crashar

    def test_broadcast_empty_network(self):
        r"""Broadcast em rede vazia envia 0 mensagens."""
        net = P2PNetwork(listen_port=18452)
        count = net.broadcast(MessageType.PING, {})
        assert count == 0

    def test_message_serialization_roundtrip(self):
        r"""Mensagem serializa e desserializa corretamente."""
        from baitcoin_core.network.p2p import NetworkMessage
        msg = NetworkMessage(
            msg_type=MessageType.BLOCK,
            payload={"height": 42},
            sender_id="node_1",
        )
        raw = msg.serialize()
        restored = NetworkMessage.deserialize(raw)
        assert restored is not None
        assert restored.msg_type == MessageType.BLOCK
        assert restored.payload["height"] == 42

    def test_deserialize_invalid(self):
        r"""Desserializacao de dados invalidos retorna None."""
        from baitcoin_core.network.p2p import NetworkMessage
        assert NetworkMessage.deserialize(b"invalid") is None
        assert NetworkMessage.deserialize(b"") is None


# ============================================================
# ECOSYSTEM NODE EDGE CASES
# ============================================================
class TestEcosystemNodeEdgeCases:
    r"""Edge cases do EcosystemNode."""

    def test_node_shutdown_idempotent(self):
        r"""Shutdown pode ser chamado multiplas vezes."""
        tmp = tempfile.mkdtemp(prefix="bait_edge_")
        try:
            node = EcosystemNode(data_path=tmp, auto_persist=False)
            node.shutdown()
            node.shutdown()  # Segunda chamada nao deve crashar
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_node_context_manager(self):
        r"""Context manager faz shutdown automatico."""
        tmp = tempfile.mkdtemp(prefix="bait_ctx_")
        try:
            with EcosystemNode(data_path=tmp, auto_persist=False) as node:
                assert node.height == 0
            # Apos o with, o node foi desligado
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_node_get_nonexistent_block(self):
        r"""Bloco inexistente retorna None."""
        tmp = tempfile.mkdtemp(prefix="bait_block_")
        try:
            node = EcosystemNode(data_path=tmp, auto_persist=False)
            assert node.get_block(999) is None
            node.shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_node_get_nonexistent_agent(self):
        r"""Agente inexistente retorna None."""
        tmp = tempfile.mkdtemp(prefix="bait_agent_")
        try:
            node = EcosystemNode(data_path=tmp, auto_persist=False)
            assert node.get_agent("nonexistent") is None
            node.shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_node_persist_and_restore(self):
        r"""Node persiste e restaura estado."""
        tmp = tempfile.mkdtemp(prefix="bait_persist_")
        try:
            # Criar, minerar, registrar agente
            node1 = EcosystemNode(data_path=tmp, auto_persist=True)
            kp = SchnorrKeyPair()
            node1.mine_block("persist_miner", kp.pub_bytes)
            node1.mint("persist_agent", 500 * 100_000_000)
            node1.register_agent("persist_agent", kp.public_key_hex, [AgentCapability.ML_INFERENCE])
            h1 = node1.height
            bal1 = node1.balance_of("persist_agent")
            agents1 = node1.total_agents
            node1.shutdown()

            # Restaurar
            node2 = EcosystemNode(data_path=tmp, auto_persist=False)
            assert node2.height == h1
            assert node2.balance_of("persist_agent") == bal1
            assert node2.total_agents >= agents1
            node2.shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ============================================================
# ADDRESS FORMAT
# ============================================================
class TestAddressFormat:
    r"""Valida formato de endereco b'AI'tcoin."""

    def test_address_starts_with_bait(self):
        r"""Endereco gerado por paper wallet comeca com 'bait'."""
        from baitcoin_wallet.paper_wallet import generate_paper_wallet
        pw = generate_paper_wallet()
        assert pw["address"].startswith("bait")

    def test_paper_wallet_fields(self):
        r"""Paper wallet tem campos obrigatorios."""
        from baitcoin_wallet.paper_wallet import generate_paper_wallet
        pw = generate_paper_wallet()
        assert "address" in pw
        assert "private_key" in pw
        assert pw["address"].startswith("bait")


# ============================================================
# MODULE VERSIONS
# ============================================================
class TestModuleVersions:
    r"""Verifica versoes e metadados dos modulos."""

    def test_core_version(self):
        r"""Versao do core existe."""
        import baitcoin_core
        assert hasattr(baitcoin_core, "__version__")
        assert baitcoin_core.__version__ != ""

    def test_core_protocol(self):
        r"""Protocolo do core existe."""
        import baitcoin_core
        assert hasattr(baitcoin_core, "__protocol__")
        assert "zkML" in baitcoin_core.__protocol__

    def test_emission_schedule_constants(self):
        r"""Constantes de emissao estao corretas."""
        es = EmissionSchedule()
        assert es.MAX_SUPPLY == 21_000_000  # Em BAIT (float)
        assert es.HALVING_INTERVAL == 210_000
        assert es.INITIAL_REWARD == 50.0  # Em BAIT (float)

    def test_bait_token_decimals(self):
        r"""Decimais do token e 8."""
        t = BAITToken()
        assert t.DECIMALS == 8
        assert t.SATS_PER_BAIT == 100_000_000
