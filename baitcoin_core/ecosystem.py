r"""
Nó do Ecossistema b'AI'tcoin — Facade unificado com persistência automática.

Este módulo fornece a classe ``EcosystemNode`` que integra todos os
módulos do ecossistema b'AI'tcoin num único ponto de acesso, com
persistência automática via WAL + snapshots (módulo ``baitcoin_memory``).

Cada mutação de estado (mineração, transferência, staking, etc.)
é automaticamente persistida em disco, garantindo que o nó
sobreviva a reinicializações sem perda de dados.

Camadas integradas:
    - **baitcoin_core**: blockchain, consenso zkML, PoUW, Schnorr, P2P, mempool
    - **baitcoin_wallet**: construtor de transações (indireto via SDK)
    - **baitcoin_token**: BAIT (ERC-20-like), tokenomics
    - **baitcoin_bank**: staking, lending P2P, vaults DeFi
    - **baitcoin_ai**: registro de agentes, marketplace, oracle
    - **baitcoin_faucet**: distribuição de BAIT
    - **baitcoin_obscura**: browser headless Obscura
    - **baitcoin_memory**: WAL + snapshots (camada de persistência)

Modos de uso::

    # Criar nó com persistência em disco
    node = EcosystemNode("/caminho/para/dados")

    # Operações normais — persistência automática após cada mutação
    node.mine_block("miner_agent", pubkey_bytes)
    node.register_agent("agent_1", "0xabc", [AgentCapability.ML_INFERENCE])
    node.mint("agent_1", 100 * 100_000_000)
    node.transfer("agent_1", "agent_2", 50 * 100_000_000)
    node.stake("agent_1", 1000 * 100_000_000)

    # Fechar com snapshot garantido
    with EcosystemNode("/dados/baitcoin") as node:
        node.mine_block("agente", pubkey)

    # Restaurar de disco (automático na construção)
    node2 = EcosystemNode("/dados/baitcoin")
    assert node2.blockchain.height == node.blockchain.height
"""

import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Set

from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.blockchain.mempool import Mempool
from baitcoin_core.blockchain.block import (
    Block,
    BlockHeader,
    Transaction,
    TransactionInput,
    TransactionOutput,
)
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem
from baitcoin_core.consensus.zkml_real.tensor_commitment import (
    TensorCommitmentScheme,
)
from baitcoin_core.consensus.pouw import PoUWValidator
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_ai.agent_protocol.registry import (
    AgentRegistry,
    AgentProfile,
    AgentCapability,
)
from baitcoin_ai.marketplace.services import (
    AIMarketplace,
    ServiceCategory,
    ServiceListing,
    ListingState,
    PurchaseRecord,
)
from baitcoin_ai.oracle.feed import PriceOracle, PricePoint, OracleReport
from baitcoin_bank.staking.pool import StakingPool, StakePosition, StakeState
from baitcoin_bank.lending.engine import (
    LendingEngine,
    LoanOffer,
    ActiveLoan,
    LoanState,
)
from baitcoin_bank.defi_core.vault import Vault, VaultConfig, VaultAllocation, StrategyType
from baitcoin_token.erc20_like.bait_token import BAITToken, TokenLog, TokenEvent
from baitcoin_faucet.faucet import BAITFaucet, FaucetClaim
from baitcoin_obscura.bridge import ObscuraBridge, ObscuraConfig
from baitcoin_obscura.agent_capability import WebScrapingCapability
from baitcoin_memory import MemoryStore, PersistentState, MemoryNamespace

logger = logging.getLogger("baitcoin_core.ecosystem")

__all__ = ["EcosystemNode"]


# ============================================================
# Funções auxiliares de desserialização
# ============================================================


def _hex(value: str) -> bytes:
    """Converte string hex para bytes, tolerando prefixo 0x."""
    if value.startswith(("0x", "0X")):
        return bytes.fromhex(value[2:])
    return bytes.fromhex(value)


def _restore_block_header(d: dict) -> BlockHeader:
    """Reconstrói um BlockHeader a partir de dict serializado."""
    bits = d.get("bits", "0x1d00ffff")
    if isinstance(bits, str):
        bits = int(bits, 16)
    return BlockHeader(
        version=d.get("version", 1),
        prev_block_hash=_hex(d.get("prev_block_hash", "00" * 32)),
        merkle_root=_hex(d.get("merkle_root", "00" * 32)),
        timestamp=float(d.get("timestamp", 0)),
        bits=bits,
        nonce=d.get("nonce", 0),
        zkml_proof_hash=_hex(d.get("zkml_proof_hash", "00" * 32)),
        pouw_work_hash=_hex(d.get("pouw_work_hash", "00" * 32)),
        agent_validator=d.get("agent_validator", ""),
        tensor_commitment=_hex(d.get("tensor_commitment", "00" * 32)),
    )


def _restore_tx_output(d: dict) -> TransactionOutput:
    """Reconstrói um TransactionOutput."""
    return TransactionOutput(
        amount_sats=d["amount_sats"],
        script_pubkey=_hex(d["script_pubkey"]),
        output_index=d.get("output_index", 0),
    )


def _restore_tx_input(d: dict) -> TransactionInput:
    """Reconstrói um TransactionInput."""
    return TransactionInput(
        prev_tx_id=_hex(d["prev_tx_id"]),
        prev_output_index=d["prev_output_index"],
        script_sig=_hex(d.get("script_sig", "")),
        sequence=d.get("sequence", 0xFFFFFFFF),
    )


def _restore_transaction(d: dict) -> Transaction:
    """Reconstrói uma Transaction completa."""
    inputs = [_restore_tx_input(i) for i in d.get("inputs", [])]
    outputs = [_restore_tx_output(o) for o in d.get("outputs", [])]
    tx = Transaction(
        tx_type=d.get("tx_type", "transfer"),
        inputs=inputs,
        outputs=outputs,
        nonce=d.get("nonce", 0),
        timestamp=float(d.get("timestamp", 0)),
        agent_id=d.get("agent_id", ""),
        gas_limit=d.get("gas_limit", 0),
        gas_price=d.get("gas_price", 0),
        payload=_hex(d.get("payload", "")),
        signature=_hex(d.get("signature", "")),
    )
    return tx


def _restore_block(d: dict) -> Block:
    """Reconstrói um Block completo com header e transações."""
    header = _restore_block_header(d["header"])
    txs = [_restore_transaction(td) for td in d.get("transactions", [])]
    block = Block(index=d["index"], header=header, transactions=txs)
    return block


def _restore_agent_profile(d: dict) -> AgentProfile:
    """Reconstrói um AgentProfile a partir de dict."""
    caps: Set[AgentCapability] = set()
    for c in d.get("capabilities", []):
        try:
            if isinstance(c, str):
                caps.add(AgentCapability(c))
            else:
                caps.add(AgentCapability(c))
        except ValueError:
            pass
    return AgentProfile(
        agent_id=d["agent_id"],
        pubkey_hex=d["pubkey_hex"],
        capabilities=caps,
        reputation_score=d.get("reputation_score", 50.0),
        stake_sats=d.get("stake_sats", 0),
        registered_at=d.get("registered_at", time.time()),
        last_active=d.get("last_active", time.time()),
        metadata=d.get("metadata", {}),
        is_active=d.get("is_active", True),
    )


def _restore_stake_position(d: dict) -> StakePosition:
    """Reconstrói um StakePosition a partir de dict."""
    state_val = d.get("state", "active")
    if isinstance(state_val, str):
        state = StakeState(state_val)
    else:
        state = state_val
    return StakePosition(
        agent_id=d["agent_id"],
        amount_sats=d["amount_sats"],
        start_time=d.get("start_time", time.time()),
        lock_period=d.get("lock_period", 2592000),
        reward_earned=d.get("reward_earned", 0),
        state=state,
        unlock_time=d.get("unlock_time", 0.0),
    )


def _restore_loan_offer(d: dict) -> LoanOffer:
    """Reconstrói um LoanOffer a partir de dict."""
    return LoanOffer(
        offer_id=d["offer_id"],
        lender_agent=d["lender_agent"],
        amount_sats=d["amount_sats"],
        interest_rate=d["interest_rate"],
        duration_seconds=d.get("duration_seconds", 2592000),
        min_collateral_ratio=d.get("min_collateral_ratio", 1.5),
        created_at=d.get("created_at", time.time()),
    )


def _restore_active_loan(d: dict) -> ActiveLoan:
    """Reconstrói um ActiveLoan a partir de dict."""
    state_val = d.get("state", "active")
    if isinstance(state_val, str):
        state = LoanState(state_val)
    else:
        state = state_val
    return ActiveLoan(
        loan_id=d["loan_id"],
        borrower_agent=d["borrower_agent"],
        lender_agent=d["lender_agent"],
        principal_sats=d["principal_sats"],
        collateral_sats=d["collateral_sats"],
        interest_rate=d["interest_rate"],
        created_at=d.get("created_at", time.time()),
        due_at=d.get("due_at", time.time()),
        state=state,
    )


def _restore_vault_allocation(d: dict) -> VaultAllocation:
    """Reconstrói um VaultAllocation a partir de dict."""
    strat_val = d.get("strategy", "hodl")
    if isinstance(strat_val, str):
        strategy = StrategyType(strat_val)
    else:
        strategy = strat_val
    return VaultAllocation(
        strategy=strategy,
        amount_sats=d["amount_sats"],
        apy=d.get("apy", 0.0),
        entry_time=d.get("entry_time", time.time()),
    )


def _restore_vault(d: dict) -> Vault:
    """Reconstrói um Vault a partir de dict serializado."""
    cfg = d["config"]
    config = VaultConfig(
        agent_id=cfg["agent_id"],
        risk_tolerance=cfg.get("risk_tolerance", 0.5),
        auto_compound=cfg.get("auto_compound", True),
        rebalance_threshold=cfg.get("rebalance_threshold", 0.10),
        stop_loss_pct=cfg.get("stop_loss_pct", 0.20),
    )
    vault = Vault(config)
    vault.allocations = [_restore_vault_allocation(a) for a in d.get("allocations", [])]
    vault.deposits_total = d.get("deposits_total", 0)
    vault.withdrawals_total = d.get("withdrawals_total", 0)
    vault.created_at = d.get("created_at", time.time())
    vault._tx_history = d.get("tx_history", [])
    return vault


def _restore_faucet_claim(d: dict) -> FaucetClaim:
    """Reconstrói um FaucetClaim."""
    return FaucetClaim(
        claim_id=d["claim_id"],
        agent_id=d["agent_id"],
        amount_sats=d["amount_sats"],
        pubkey_hex=d.get("pubkey_hex", ""),
        challenge_sig=d.get("challenge_sig", ""),
        timestamp=d.get("timestamp", time.time()),
        tx_hash=d.get("tx_hash", ""),
    )


def _restore_service_listing(d: dict) -> ServiceListing:
    """Reconstrói um ServiceListing."""
    cat = d.get("category", "ml_inference")
    if isinstance(cat, str):
        cat = ServiceCategory(cat)
    state = d.get("state", "active")
    if isinstance(state, str):
        state = ListingState(state)
    return ServiceListing(
        listing_id=d["listing_id"],
        provider_agent=d["provider_agent"],
        category=cat,
        name=d["name"],
        description=d.get("description", ""),
        price_per_call_sats=d["price_per_call_sats"],
        state=state,
        created_at=d.get("created_at", time.time()),
        total_calls=d.get("total_calls", 0),
        total_revenue_sats=d.get("total_revenue_sats", 0),
        rating_avg=d.get("rating_avg", 0.0),
        rating_count=d.get("rating_count", 0),
    )


def _restore_purchase_record(d: dict) -> PurchaseRecord:
    """Reconstrói um PurchaseRecord."""
    return PurchaseRecord(
        purchase_id=d["purchase_id"],
        listing_id=d["listing_id"],
        buyer_agent=d["buyer_agent"],
        seller_agent=d["seller_agent"],
        price_sats=d["price_sats"],
        timestamp=d.get("timestamp", time.time()),
        status=d.get("status", "completed"),
    )


def _restore_token_log(d: dict) -> TokenLog:
    """Reconstrói um TokenLog."""
    evt = d.get("event_type", "transfer")
    if isinstance(evt, str):
        evt = TokenEvent(evt)
    return TokenLog(
        event_type=evt,
        from_agent=d.get("from_agent", ""),
        to_agent=d.get("to_agent", ""),
        amount_sats=d.get("amount_sats", 0),
        timestamp=d.get("timestamp", time.time()),
        tx_hash=d.get("tx_hash", ""),
        memo=d.get("memo", ""),
    )


def _restore_price_point(d: dict) -> PricePoint:
    """Reconstrói um PricePoint."""
    return PricePoint(
        symbol=d.get("symbol", ""),
        price=d.get("price", 0.0),
        timestamp=d.get("timestamp", time.time()),
        source=d.get("source", ""),
    )


def _restore_oracle_report(d: dict) -> OracleReport:
    """Reconstrói um OracleReport."""
    return OracleReport(
        agent_id=d.get("agent_id", ""),
        symbol=d.get("symbol", ""),
        price=d.get("price", 0.0),
        signature=d.get("signature", ""),
        timestamp=d.get("timestamp", time.time()),
    )


# ============================================================
# EcosystemNode — Facade unificado
# ============================================================


class EcosystemNode:
    r"""Nó completo do ecossistema b'AI'tcoin com persistência automática.

    Integra todos os subsistemas num único ponto de acesso.
    Cada mutação de estado é automaticamente persistida via
    WAL + snapshots (módulo ``baitcoin_memory``).

    Atributos públicos (subsistemas):
        blockchain        – :class:`Blockchain`
        mempool           – :class:`Mempool` (standalone, com priorização por fee)
        consensus         – :class:`ZkMLConsensus`
        token             – :class:`BAITToken`
        registry          – :class:`AgentRegistry`
        marketplace       – :class:`AIMarketplace`
        oracle            – :class:`PriceOracle`
        staking           – :class:`StakingPool`
        lending           – :class:`LendingEngine`
        vaults            – ``Dict[str, Vault]`` (agent_id → Vault)
        faucet            – :class:`BAITFaucet`
        obscura_bridge    – :class:`ObscuraBridge`
        obscura_capability – :class:`WebScrapingCapability`
        zkml_system       – :class:`ZkMLProofSystem`
        pouw_validator    – :class:`PoUWValidator`
        store             – :class:`MemoryStore`
        state             – :class:`PersistentState`

    Args:
        data_path: Caminho base para dados persistentes no disco.
                   Expandido com ``os.path.expanduser``.
        auto_persist: Se ``True`` (padrão), cada mutação de estado
                      persiste automaticamente. Se ``False``, o chamador
                      deve invocar :meth:`persist_all` manualmente.
        consensus_target: Alvo de dificuldade para o consenso zkML.
        faucet_amount_sats: Quantidade de BAIT por claim do faucet.
        faucet_cooldown: Cooldown entre claims do mesmo agente (segundos).
        faucet_max_total: Máximo total por agente no faucet (sats).
    """

    def __init__(
        self,
        data_path: str = "~/.baitcoin/memory",
        auto_persist: bool = True,
        consensus_target: int = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
        faucet_amount_sats: int = 10 * 100_000_000,
        faucet_cooldown: int = 86400,
        faucet_max_total: int = 100 * 100_000_000,
    ) -> None:
        self.auto_persist = auto_persist

        # ---- Memória persistente ----
        self.store = MemoryStore(data_path)
        self.state = PersistentState(self.store)

        # ---- Core: consenso ----
        self.consensus = ZkMLConsensus(target=consensus_target)
        self.zkml_system = ZkMLProofSystem()
        self.pouw_validator = PoUWValidator()

        # ---- Core: blockchain + mempool ----
        self.blockchain = Blockchain(self.consensus)
        self.mempool = Mempool()

        # ---- Token ----
        self.token = BAITToken()

        # ---- AI: agentes, marketplace, oracle ----
        self.registry = AgentRegistry()
        self.marketplace = AIMarketplace()
        self.oracle = PriceOracle()

        # ---- DeFi: staking, lending, vaults ----
        self.staking = StakingPool()
        self.lending = LendingEngine()
        self.vaults: Dict[str, Vault] = {}

        # ---- Faucet ----
        self.faucet = BAITFaucet(
            self.token,
            amount_sats=faucet_amount_sats,
            cooldown=faucet_cooldown,
            max_total=faucet_max_total,
        )

        # ---- Obscura ----
        self.obscura_bridge = ObscuraBridge(ObscuraConfig())
        self.obscura_capability = WebScrapingCapability()

        # ---- Restaurar estado persistido ----
        self._restore_all()

        logger.info(
            "EcosystemNode inicializado (height=%d, agents=%d, auto_persist=%s)",
            self.blockchain.height,
            len(self.registry.agents),
            self.auto_persist,
        )

    # ================================================================
    # Propriedades
    # ================================================================

    @property
    def height(self) -> int:
        """Altura atual da cadeia."""
        return self.blockchain.height

    @property
    def total_agents(self) -> int:
        """Número total de agentes registados."""
        return len(self.registry.agents)

    @property
    def total_staked_bait(self) -> float:
        """Total em stake em BAIT."""
        return self.staking.total_staked_bait

    # ================================================================
    # Ciclo de vida — context manager
    # ================================================================

    def __enter__(self) -> "EcosystemNode":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        r"""Fecha o nó com snapshot garantido de todo o estado."""
        self.force_snapshot()
        self.obscura_bridge.close()
        return False

    def shutdown(self) -> None:
        r"""Encerra o nó: snapshot final + limpeza de recursos."""
        self.force_snapshot()
        self.obscura_bridge.close()
        logger.info("EcosystemNode desligado (height=%d)", self.height)

    # ================================================================
    # BLOCKCHAIN
    # ================================================================

    def mine_block(self, miner_agent: str, miner_pubkey: bytes) -> Block:
        r"""Minera um novo bloco na cadeia.

        Sincroniza transações do mempool standalone para a blockchain,
        minera o bloco via consenso zkML, e persiste o resultado.

        Args:
            miner_agent: ID do agente minerador.
            miner_pubkey: Chave pública do minerador (32 bytes).

        Returns:
            O bloco minerado (pode não ter sido adicionado se
            o consenso falhar).
        """
        # Sincronizar mempool standalone → blockchain
        txs = self.mempool.get_transactions(max_count=1000)
        self.blockchain.mempool = txs

        old_height = self.blockchain.height
        block = self.blockchain.mine_block(miner_agent, miner_pubkey)

        # Se o bloco foi realmente adicionado, limpar mempool
        if self.blockchain.height > old_height:
            mined_ids = [
                tx.tx_id.hex()
                for tx in block.transactions
                if not tx.is_coinbase
            ]
            self.mempool.remove_transactions(mined_ids)

            if self.auto_persist:
                self._persist_blockchain()
                self._persist_mempool()

        return block

    def add_transaction(self, tx: Transaction) -> bool:
        r"""Adiciona transação ao mempool com validação UTXO.

        Args:
            tx: Transação a adicionar.

        Returns:
            True se adicionada com sucesso.
        """
        ok = self.blockchain.add_transaction(tx)
        if ok:
            ok2 = self.mempool.add_transaction(tx)
            if self.auto_persist and ok2:
                self._persist_mempool()
        return ok

    def validate_chain(self) -> bool:
        r"""Valida a integridade de toda a cadeia."""
        return self.blockchain.validate_chain()

    def get_block(self, height: int) -> Optional[dict]:
        r"""Retorna dados de um bloco por altura."""
        if 0 <= height < len(self.blockchain.chain):
            return self.blockchain.chain[height].to_dict()
        return None

    def get_balance(self, pubkey: bytes) -> int:
        r"""Calcula saldo UTXO de um endereço (pubkey)."""
        return self.blockchain.get_balance(pubkey)

    def get_block_reward(self, block_height: int) -> int:
        r"""Calcula recompensa do bloco com halving."""
        return self.blockchain.get_block_reward(block_height)

    # ================================================================
    # TOKEN BAIT
    # ================================================================

    def mint(self, agent_id: str, amount_sats: int) -> bool:
        r"""Emite novos tokens BAIT."""
        ok = self.token.mint(agent_id, amount_sats)
        if ok and self.auto_persist:
            self._persist_token()
        return ok

    def burn(self, agent_id: str, amount_sats: int) -> bool:
        r"""Queima tokens BAIT."""
        ok = self.token.burn(agent_id, amount_sats)
        if ok and self.auto_persist:
            self._persist_token()
        return ok

    def transfer(
        self,
        from_agent: str,
        to_agent: str,
        amount_sats: int,
        memo: str = "",
    ) -> bool:
        r"""Transfere BAIT entre agentes."""
        ok = self.token.transfer(from_agent, to_agent, amount_sats, memo)
        if ok and self.auto_persist:
            self._persist_token()
        return ok

    def approve(self, owner: str, spender: str, amount_sats: int) -> bool:
        r"""Aprova gasto delegado."""
        ok = self.token.approve(owner, spender, amount_sats)
        if ok and self.auto_persist:
            self._persist_token()
        return ok

    def transfer_from(
        self,
        spender: str,
        from_agent: str,
        to_agent: str,
        amount_sats: int,
    ) -> bool:
        r"""Transferência via approval."""
        ok = self.token.transfer_from(spender, from_agent, to_agent, amount_sats)
        if ok and self.auto_persist:
            self._persist_token()
        return ok

    def balance_of(self, agent_id: str) -> int:
        r"""Retorna saldo em s'AI'toshis."""
        return self.token.balance_of(agent_id)

    def balance_bait(self, agent_id: str) -> float:
        r"""Retorna saldo em BAIT."""
        return self.token.balance_bait(agent_id)

    # ================================================================
    # AGENTES AI
    # ================================================================

    def register_agent(
        self,
        agent_id: str,
        pubkey_hex: str,
        capabilities: Optional[List[AgentCapability]] = None,
    ) -> bool:
        r"""Regista um novo agente AI na rede."""
        ok = self.registry.register(agent_id, pubkey_hex, capabilities)
        if ok and self.auto_persist:
            self._persist_agents()
        return ok

    def update_reputation(
        self, agent_id: str, delta: float, reason: str = ""
    ) -> bool:
        r"""Actualiza reputação de um agente (+/-)."""
        ok = self.registry.update_reputation(agent_id, delta, reason)
        if ok and self.auto_persist:
            self._persist_agents()
            self._persist_reputation()
        return ok

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        r"""Retorna perfil de um agente."""
        return self.registry.get_agent(agent_id)

    def list_agents(
        self, capability: Optional[AgentCapability] = None
    ) -> List[dict]:
        r"""Lista agentes, opcionalmente filtrado por capacidade."""
        return self.registry.list_agents(capability)

    def get_validators(self) -> List[str]:
        r"""Retorna agentes qualificados como validadores."""
        return self.registry.get_validators()

    # ================================================================
    # STAKING
    # ================================================================

    def stake(
        self,
        agent_id: str,
        amount_sats: int,
        lock_period: Optional[float] = None,
    ) -> bool:
        r"""Faz stake de BAIT no pool."""
        ok = self.staking.stake(agent_id, amount_sats, lock_period or 2592000)
        if ok and self.auto_persist:
            self._persist_staking()
        return ok

    def unstake(self, agent_id: str) -> int:
        r"""Inicia unstake. Retorna valor líquido após penalty."""
        result = self.staking.unstake(agent_id)
        if result > 0 and self.auto_persist:
            self._persist_staking()
        return result

    def distribute_rewards(self, total_reward_sats: int) -> Dict[str, int]:
        r"""Distribui recompensas proporcionalmente ao stake."""
        rewards = self.staking.distribute_rewards(total_reward_sats)
        if rewards and self.auto_persist:
            self._persist_staking()
        return rewards

    def slash(self, agent_id: str, fraction: float = 0.05) -> int:
        r"""Aplica slashing por comportamento malicioso."""
        result = self.staking.slash(agent_id, fraction)
        if result > 0 and self.auto_persist:
            self._persist_staking()
        return result

    def get_validator_set(self) -> List[str]:
        r"""Retorna lista de validadores activos."""
        return self.staking.get_validator_set()

    # ================================================================
    # LENDING P2P
    # ================================================================

    def create_loan_offer(
        self,
        lender_agent: str,
        amount_sats: int,
        interest_rate: float,
        duration: Optional[float] = None,
    ) -> str:
        r"""Cria oferta de empréstimo."""
        oid = self.lending.create_offer(
            lender_agent, amount_sats, interest_rate, duration
        )
        if oid and self.auto_persist:
            self._persist_lending()
        return oid

    def borrow(
        self,
        borrower_agent: str,
        offer_id: str,
        collateral_sats: int,
    ) -> Optional[str]:
        r"""Toma empréstimo contra colateral."""
        lid = self.lending.borrow(borrower_agent, offer_id, collateral_sats)
        if lid and self.auto_persist:
            self._persist_lending()
        return lid

    def repay_loan(self, loan_id: str, amount_sats: int) -> bool:
        r"""Paga (parcialmente) um empréstimo."""
        ok = self.lending.repay(loan_id, amount_sats)
        if ok and self.auto_persist:
            self._persist_lending()
        return ok

    def check_liquidations(self) -> List[str]:
        r"""Verifica e liquida empréstimos undercollateralized."""
        liquidated = self.lending.check_liquidations()
        if liquidated and self.auto_persist:
            self._persist_lending()
        return liquidated

    def get_market_rate(self) -> float:
        r"""Retorna taxa de juros média do mercado."""
        return self.lending.get_market_rate()

    # ================================================================
    # VAULTS DeFi
    # ================================================================

    def create_vault(
        self,
        agent_id: str,
        risk_tolerance: float = 0.5,
        auto_compound: bool = True,
        rebalance_threshold: float = 0.10,
        stop_loss_pct: float = 0.20,
    ) -> str:
        r"""Cria um vault auto-custodiado para um agente."""
        config = VaultConfig(
            agent_id=agent_id,
            risk_tolerance=risk_tolerance,
            auto_compound=auto_compound,
            rebalance_threshold=rebalance_threshold,
            stop_loss_pct=stop_loss_pct,
        )
        vault = Vault(config)
        self.vaults[agent_id] = vault
        if self.auto_persist:
            self._persist_vaults()
        return agent_id

    def vault_deposit(
        self,
        agent_id: str,
        amount_sats: int,
        strategy: Optional[StrategyType] = None,
    ) -> bool:
        r"""Deposita fundos no vault de um agente."""
        vault = self.vaults.get(agent_id)
        if vault is None:
            return False
        ok = vault.deposit(amount_sats, strategy or StrategyType.HODL)
        if ok and self.auto_persist:
            self._persist_vaults()
        return ok

    def vault_withdraw(
        self,
        agent_id: str,
        amount_sats: int,
        strategy: Optional[StrategyType] = None,
    ) -> int:
        r"""Saca fundos do vault de um agente. Retorna valor sacado."""
        vault = self.vaults.get(agent_id)
        if vault is None:
            return 0
        result = vault.withdraw(amount_sats, strategy)
        if result > 0 and self.auto_persist:
            self._persist_vaults()
        return result

    def get_vault(self, agent_id: str) -> Optional[Vault]:
        r"""Retorna o vault de um agente."""
        return self.vaults.get(agent_id)

    def list_vaults(self) -> List[dict]:
        r"""Lista todos os vaults com resumo."""
        return [v.to_dict() for v in self.vaults.values()]

    # ================================================================
    # MEMPOOL
    # ================================================================

    def mempool_add(self, tx: Transaction) -> bool:
        r"""Adiciona transação ao mempool standalone."""
        ok = self.mempool.add_transaction(tx)
        if ok and self.auto_persist:
            self._persist_mempool()
        return ok

    def mempool_get_transactions(
        self, max_count: int = 1000, min_fee_rate: int = 0
    ) -> list:
        r"""Retorna transações priorizadas por fee."""
        return self.mempool.get_transactions(max_count, min_fee_rate)

    def mempool_purge_expired(self) -> int:
        r"""Remove transações expiradas do mempool."""
        count = self.mempool.purge_expired()
        if count > 0 and self.auto_persist:
            self._persist_mempool()
        return count

    def mempool_get_agent_txs(self, agent_id: str) -> list:
        r"""Retorna todas transações de um agente no mempool."""
        return self.mempool.get_agent_txs(agent_id)

    # ================================================================
    # MARKETPLACE
    # ================================================================

    def list_service(
        self,
        provider: str,
        category: ServiceCategory,
        name: str,
        description: str,
        price_sats: int,
    ) -> str:
        r"""Cria listagem de serviço no marketplace."""
        lid = self.marketplace.list_service(
            provider, category, name, description, price_sats
        )
        if self.auto_persist:
            self._persist_marketplace()
        return lid

    def purchase_service(self, listing_id: str, buyer: str) -> Optional[str]:
        r"""Compra/contrata um serviço."""
        pid = self.marketplace.purchase_service(listing_id, buyer)
        if pid and self.auto_persist:
            self._persist_marketplace()
        return pid

    def rate_service(self, purchase_id: str, score: float) -> bool:
        r"""Avalia serviço comprado (1.0 a 5.0)."""
        ok = self.marketplace.rate_service(purchase_id, score)
        if ok and self.auto_persist:
            self._persist_marketplace()
        return ok

    def search_services(
        self,
        category: Optional[ServiceCategory] = None,
        max_price: Optional[int] = None,
    ) -> List[dict]:
        r"""Busca serviços no marketplace."""
        return self.marketplace.search(category, max_price)

    # ================================================================
    # ORACLE
    # ================================================================

    def register_oracle(self, agent_id: str, reputation: float = 50.0) -> None:
        r"""Regista agente como oracle."""
        self.oracle.register_oracle(agent_id, reputation)
        if self.auto_persist:
            self._persist_oracle()

    def submit_price(
        self, agent_id: str, symbol: str, price: float
    ) -> bool:
        r"""Submete preço ao feed oracle."""
        ok = self.oracle.submit_price(agent_id, symbol, price)
        if ok and self.auto_persist:
            self._persist_oracle()
        return ok

    def get_price(self, symbol: str) -> Optional[float]:
        r"""Retorna preço agregado de um símbolo."""
        return self.oracle.get_price(symbol)

    # ================================================================
    # FAUCET
    # ================================================================

    def faucet_claim(
        self,
        agent_id: str,
        pubkey_hex: str = "",
        challenge_sig: str = "",
    ) -> dict:
        r"""Solicita BAIT do faucet."""
        result = self.faucet.claim(agent_id, pubkey_hex, challenge_sig)
        # Persistir faucet E token (o claim faz mint internamente)
        if result.get("success") and self.auto_persist:
            self._persist_faucet()
            self._persist_token()
        return result

    def faucet_get_balance(self, agent_id: str) -> float:
        r"""Retorna saldo via faucet."""
        return self.faucet.get_balance(agent_id)

    # ================================================================
    # CONSENSO zkML + PoUW
    # ================================================================

    def generate_zk_proof(
        self,
        prover_id: str,
        model_id: str,
        input_data: bytes,
        output_data: bytes,
        block_hash: str,
        nonce: int,
    ) -> Any:
        r"""Gera prova zkML."""
        return self.zkml_system.generate_proof(
            prover_id, model_id, input_data, output_data, block_hash, nonce
        )

    def verify_zk_proof(self, proof: Any) -> bool:
        r"""Verifica prova zkML."""
        return self.zkml_system.verify_proof(proof)

    def commit_tensor(
        self, tensor_data: bytes, dimensions: tuple = (4,)
    ) -> Any:
        r"""Cria Pedersen commitment de tensor."""
        return TensorCommitmentScheme.commit(tensor_data, dimensions)

    def verify_tensor(self, commitment: Any, tensor_data: bytes) -> bool:
        r"""Verifica opening de commitment de tensor."""
        opening = TensorCommitmentScheme.open(commitment, tensor_data)
        return TensorCommitmentScheme.verify(opening, tensor_data)

    def submit_pouw(
        self, work_type: str, work_data: dict, agent_id: str = ""
    ) -> dict:
        r"""Submete Proof of Useful Work."""
        return self.pouw_validator.submit_work(work_type, work_data, agent_id=agent_id)

    # ================================================================
    # CRIPTOGRAFIA
    # ================================================================

    def generate_keypair(self) -> SchnorrKeyPair:
        r"""Gera um novo par de chaves Schnorr/BIP-340."""
        return SchnorrKeyPair()

    # ================================================================
    # PERSISTÊNCIA — Serialização por subsistema
    # ================================================================

    def _persist_blockchain(self) -> None:
        r"""Persiste a cadeia completa e o conjunto UTXO."""
        chain_data = {
            "height": self.blockchain.height,
            "block_count": len(self.blockchain.chain),
            "utxo_count": len(self.blockchain.utxo_set),
            "total_supply_sats": sum(
                tx.outputs[0].amount_sats
                for b in self.blockchain.chain
                for tx in b.transactions
                if tx.is_coinbase
            ),
            "last_block_hash": self.blockchain.last_block.block_hash.hex(),
            "blocks": [b.to_dict() for b in self.blockchain.chain],
        }
        self.state.save_blockchain(chain_data)

        # UTXO set serializado
        utxo_data = {
            key: {
                "amount_sats": utxo.amount_sats,
                "script_pubkey": utxo.script_pubkey.hex(),
                "output_index": utxo.output_index,
            }
            for key, utxo in self.blockchain.utxo_set.items()
        }
        self.state.save_utxo_set(utxo_data)

    def _persist_mempool(self) -> None:
        r"""Persiste o estado do mempool standalone."""
        data = {
            "transactions": {
                tx_id_hex: tx.to_dict()
                for tx_id_hex, tx in self.mempool._transactions.items()
            },
            "by_agent": dict(self.mempool._by_agent),
            "by_fee": list(self.mempool._by_fee),
            "total_fees_sats": self.mempool._total_fees_sats,
            "stats": dict(self.mempool._stats),
        }
        self.store.put("mempool", "state", data)

    def _persist_token(self) -> None:
        r"""Persiste saldos, aprovações e contadores do token."""
        self.store.put("token", "balances", dict(self.token.balances))
        # Approvals: owner → (spender → amount)
        approvals = {
            owner: dict(spenders)
            for owner, spenders in self.token.allowances.items()
        }
        self.store.put("token", "allowances", approvals)
        self.store.put("token", "total_minted", self.token.total_minted)
        self.store.put("token", "total_burned", self.token.total_burned)
        self.store.put("token", "nonces", dict(self.token._nonces))
        # Event log (serializar TokenLog)
        events = [
            {
                "event_type": e.event_type.value,
                "from_agent": e.from_agent,
                "to_agent": e.to_agent,
                "amount_sats": e.amount_sats,
                "timestamp": e.timestamp,
                "tx_hash": e.tx_hash,
                "memo": e.memo,
            }
            for e in self.token.event_log
        ]
        self.store.put("token", "event_log", events)

    def _persist_agents(self) -> None:
        r"""Persiste todos os perfis de agentes."""
        agents_data = {}
        for agent_id, profile in self.registry.agents.items():
            agents_data[agent_id] = {
                "agent_id": profile.agent_id,
                "pubkey_hex": profile.pubkey_hex,
                "capabilities": [c.value for c in profile.capabilities],
                "reputation_score": profile.reputation_score,
                "stake_sats": profile.stake_sats,
                "registered_at": profile.registered_at,
                "last_active": profile.last_active,
                "metadata": profile.metadata,
                "is_active": profile.is_active,
            }
        self.state.save_all_agents(agents_data)

    def _persist_reputation(self) -> None:
        r"""Persiste histórico de eventos de reputação."""
        self.state.save_reputation_events(list(self.registry._reputation_events))

    def _persist_staking(self) -> None:
        r"""Persiste posições de staking e metadados."""
        # Posições
        positions = {}
        for aid, pos in self.staking.positions.items():
            positions[aid] = {
                "agent_id": pos.agent_id,
                "amount_sats": pos.amount_sats,
                "start_time": pos.start_time,
                "lock_period": pos.lock_period,
                "reward_earned": pos.reward_earned,
                "state": pos.state.value,
                "unlock_time": pos.unlock_time,
            }
        self.state.save_staking_positions(positions)

        # Metadados
        meta = {
            "total_staked": self.staking.total_staked,
            "total_rewards_distributed": self.staking.total_rewards_distributed,
            "reward_accumulator": self.staking._reward_accumulator,
        }
        self.state.save_staking_meta(meta)

    def _persist_lending(self) -> None:
        r"""Persiste ofertas, empréstimos activos e contadores."""
        data = {
            "offers": {
                oid: {
                    "offer_id": o.offer_id,
                    "lender_agent": o.lender_agent,
                    "amount_sats": o.amount_sats,
                    "interest_rate": o.interest_rate,
                    "duration_seconds": o.duration_seconds,
                    "min_collateral_ratio": o.min_collateral_ratio,
                    "created_at": o.created_at,
                }
                for oid, o in self.lending.offers.items()
            },
            "loans": {
                lid: {
                    "loan_id": l.loan_id,
                    "borrower_agent": l.borrower_agent,
                    "lender_agent": l.lender_agent,
                    "principal_sats": l.principal_sats,
                    "collateral_sats": l.collateral_sats,
                    "interest_rate": l.interest_rate,
                    "created_at": l.created_at,
                    "due_at": l.due_at,
                    "state": l.state.value,
                }
                for lid, l in self.lending.loans.items()
            },
            "liquidity_pool": self.lending.liquidity_pool,
            "total_lent": self.lending.total_lent,
            "total_repaid": self.lending.total_repaid,
        }
        self.state.save_lending_state(data)

    def _persist_vaults(self) -> None:
        r"""Persiste todos os vaults."""
        vaults_data = {}
        for agent_id, vault in self.vaults.items():
            vaults_data[agent_id] = {
                "config": {
                    "agent_id": vault.config.agent_id,
                    "risk_tolerance": vault.config.risk_tolerance,
                    "auto_compound": vault.config.auto_compound,
                    "rebalance_threshold": vault.config.rebalance_threshold,
                    "stop_loss_pct": vault.config.stop_loss_pct,
                },
                "allocations": [
                    {
                        "strategy": a.strategy.value,
                        "amount_sats": a.amount_sats,
                        "apy": a.apy,
                        "entry_time": a.entry_time,
                    }
                    for a in vault.allocations
                ],
                "deposits_total": vault.deposits_total,
                "withdrawals_total": vault.withdrawals_total,
                "created_at": vault.created_at,
                "tx_history": vault._tx_history,
            }
        self.state.save_all_vaults(vaults_data)

    def _persist_marketplace(self) -> None:
        r"""Persiste listings e compras do marketplace."""
        data = {
            "listings": {
                lid: {
                    "listing_id": l.listing_id,
                    "provider_agent": l.provider_agent,
                    "category": l.category.value,
                    "name": l.name,
                    "description": l.description,
                    "price_per_call_sats": l.price_per_call_sats,
                    "state": l.state.value,
                    "created_at": l.created_at,
                    "total_calls": l.total_calls,
                    "total_revenue_sats": l.total_revenue_sats,
                    "rating_avg": l.rating_avg,
                    "rating_count": l.rating_count,
                }
                for lid, l in self.marketplace.listings.items()
            },
            "purchases": {
                pid: {
                    "purchase_id": p.purchase_id,
                    "listing_id": p.listing_id,
                    "buyer_agent": p.buyer_agent,
                    "seller_agent": p.seller_agent,
                    "price_sats": p.price_sats,
                    "timestamp": p.timestamp,
                    "status": p.status,
                }
                for pid, p in self.marketplace.purchases.items()
            },
            "total_volume": self.marketplace._total_volume,
        }
        self.state.save_marketplace(data)

    def _persist_oracle(self) -> None:
        r"""Persiste estado do oracle (feeds + registo de oracles)."""
        feeds = {
            symbol: [
                {
                    "symbol": p.symbol,
                    "price": p.price,
                    "timestamp": p.timestamp,
                    "source": p.source,
                }
                for p in points
            ]
            for symbol, points in self.oracle.feeds.items()
        }
        reports = [
            {
                "agent_id": r.agent_id,
                "symbol": r.symbol,
                "price": r.price,
                "signature": r.signature,
                "timestamp": r.timestamp,
            }
            for r in self.oracle.reports
        ]
        data = {
            "oracles": dict(self.oracle.oracles),
            "feeds": feeds,
            "reports": reports,
        }
        self.state.save_oracle_prices(data)

    def _persist_faucet(self) -> None:
        r"""Persiste estado do faucet (claims, contadores)."""
        claims = {
            agent_id: [
                {
                    "claim_id": c.claim_id,
                    "agent_id": c.agent_id,
                    "amount_sats": c.amount_sats,
                    "pubkey_hex": c.pubkey_hex,
                    "challenge_sig": c.challenge_sig,
                    "timestamp": c.timestamp,
                    "tx_hash": c.tx_hash,
                }
                for c in claim_list
            ]
            for agent_id, claim_list in self.faucet._claims.items()
        }
        data = {
            "amount_sats": self.faucet.amount_sats,
            "cooldown": self.faucet.cooldown,
            "max_total_sats": self.faucet.max_total_sats,
            "claims": claims,
            "global_claims": self.faucet._global_claims,
            "total_distributed": self.faucet._total_distributed,
            "rate_limit_window": self.faucet._rate_limit_window,
            "rate_limit_count": self.faucet._rate_limit_count,
            "rate_limit_start": self.faucet._rate_limit_start,
        }
        self.state.save_faucet_state(data)

    def _persist_obscura(self) -> None:
        r"""Persiste estado do Obscura (sessões)."""
        sessions = {
            sid: {
                "session_id": s.session_id,
                "cdp_url": s.cdp_url,
                "created_at": s.created_at,
                "page_count": s.page_count,
                "total_cost_sats": s.total_cost_sats,
                "is_active": s.is_active,
            }
            for sid, s in self.obscura_bridge._sessions.items()
        }
        self.state.save_obscura_sessions(sessions)
        stats = {
            "total_ops": self.obscura_bridge._total_ops,
            "total_cost_sats": self.obscura_bridge._total_cost_sats,
        }
        self.state.save_obscura_tasks(stats)

    def persist_all(self) -> None:
        r"""Persiste o estado completo de todos os subsistemas.

        Pode ser chamado manualmente quando ``auto_persist=False``
        ou para garantir um ponto de salvaguarda.
        """
        self._persist_blockchain()
        self._persist_mempool()
        self._persist_token()
        self._persist_agents()
        self._persist_reputation()
        self._persist_staking()
        self._persist_lending()
        self._persist_vaults()
        self._persist_marketplace()
        self._persist_oracle()
        self._persist_faucet()
        self._persist_obscura()
        logger.debug("persist_all: todos os subsistemas persistidos.")

    # ================================================================
    # RESTAURAÇÃO — Desserialização por subsistema
    # ================================================================

    def _restore_all(self) -> None:
        r"""Restaura todos os subsistemas a partir do disco.

        Cada subsistema é restaurado independentemente com
        tolerância a erros parciais — se um subsistema falhar
        ao restaurar, os demais não são afectados.
        """
        self._restore_blockchain()
        self._restore_mempool()
        self._restore_token()
        self._restore_agents()
        self._restore_staking()
        self._restore_lending()
        self._restore_vaults()
        self._restore_marketplace()
        self._restore_oracle()
        self._restore_faucet()
        self._restore_obscura()

    def _restore_blockchain(self) -> None:
        r"""Restaura a cadeia de blocos e UTXO set."""
        try:
            chain_data = self.state.load_blockchain()
            if chain_data and "blocks" in chain_data:
                self.blockchain.chain = [
                    _restore_block(bd) for bd in chain_data["blocks"]
                ]
                logger.info(
                    "Blockchain restaurada: %d blocos (height=%d)",
                    len(self.blockchain.chain),
                    self.blockchain.height,
                )

            utxo_data = self.state.load_utxo_set()
            if utxo_data:
                self.blockchain.utxo_set = {
                    key: _restore_tx_output(val)
                    for key, val in utxo_data.items()
                }
                logger.info("UTXO set restaurado: %d entradas", len(self.blockchain.utxo_set))
        except Exception as exc:
            logger.warning("Falha ao restaurar blockchain: %s", exc)

    def _restore_mempool(self) -> None:
        r"""Restaura o mempool standalone."""
        try:
            data = self.store.get("mempool", "state")
            if data is None:
                return

            # Restaurar transações
            txs = data.get("transactions", {})
            if txs:
                self.mempool._transactions = {
                    tx_id: _restore_transaction(td)
                    for tx_id, td in txs.items()
                }
            self.mempool._by_agent = data.get("by_agent", {})
            self.mempool._by_fee = data.get("by_fee", [])
            self.mempool._total_fees_sats = data.get("total_fees_sats", 0)
            self.mempool._stats = data.get("stats", {"added": 0, "removed": 0, "expired": 0})
            logger.info("Mempool restaurado: %d transações", self.mempool.size)
        except Exception as exc:
            logger.warning("Falha ao restaurar mempool: %s", exc)

    def _restore_token(self) -> None:
        r"""Restaura saldos, aprovações e contadores do token."""
        try:
            balances = self.store.get("token", "balances")
            if balances is not None:
                self.token.balances = {k: int(v) for k, v in balances.items()}

            approvals = self.store.get("token", "allowances")
            if approvals is not None:
                self.token.allowances = {
                    owner: {sp: int(amt) for sp, amt in spenders.items()}
                    for owner, spenders in approvals.items()
                }

            minted = self.store.get("token", "total_minted")
            if minted is not None:
                self.token.total_minted = int(minted)

            burned = self.store.get("token", "total_burned")
            if burned is not None:
                self.token.total_burned = int(burned)

            nonces = self.store.get("token", "nonces")
            if nonces is not None:
                self.token._nonces = {k: int(v) for k, v in nonces.items()}

            events = self.store.get("token", "event_log")
            if events is not None:
                self.token.event_log = [_restore_token_log(e) for e in events]

            holders = len(self.token.balances)
            if holders > 0:
                logger.info("Token restaurado: %d holders", holders)
        except Exception as exc:
            logger.warning("Falha ao restaurar token: %s", exc)

    def _restore_agents(self) -> None:
        r"""Restaura perfis de agentes."""
        try:
            agents_data = self.state.load_all_agents()
            if not agents_data:
                return
            for agent_id, profile_data in agents_data.items():
                profile = _restore_agent_profile(profile_data)
                self.registry.agents[agent_id] = profile
            logger.info("Agentes restaurados: %d", len(self.registry.agents))
        except Exception as exc:
            logger.warning("Falha ao restaurar agentes: %s", exc)

    def _restore_staking(self) -> None:
        r"""Restaura posições de staking e metadados."""
        try:
            positions_data = self.state.load_staking_positions()
            if positions_data:
                self.staking.positions = {
                    aid: _restore_stake_position(pd)
                    for aid, pd in positions_data.items()
                }

            meta = self.state.load_staking_meta()
            if meta:
                self.staking.total_staked = meta.get("total_staked", 0)
                self.staking.total_rewards_distributed = meta.get(
                    "total_rewards_distributed", 0
                )
                self.staking._reward_accumulator = meta.get("reward_accumulator", 0.0)

            if positions_data:
                logger.info(
                    "Staking restaurado: %d posições, %.1f BAIT",
                    len(self.staking.positions),
                    self.staking.total_staked_bait,
                )
        except Exception as exc:
            logger.warning("Falha ao restaurar staking: %s", exc)

    def _restore_lending(self) -> None:
        r"""Restaura ofertas, empréstimos e contadores de lending."""
        try:
            data = self.state.load_lending_state()
            if data is None:
                return

            offers_raw = data.get("offers", {})
            if offers_raw:
                self.lending.offers = {
                    oid: _restore_loan_offer(od)
                    for oid, od in offers_raw.items()
                }

            loans_raw = data.get("loans", {})
            if loans_raw:
                self.lending.loans = {
                    lid: _restore_active_loan(ld)
                    for lid, ld in loans_raw.items()
                }

            self.lending.liquidity_pool = data.get("liquidity_pool", 0)
            self.lending.total_lent = data.get("total_lent", 0)
            self.lending.total_repaid = data.get("total_repaid", 0)
            logger.info(
                "Lending restaurado: %d ofertas, %d empréstimos",
                len(self.lending.offers),
                len(self.lending.loans),
            )
        except Exception as exc:
            logger.warning("Falha ao restaurar lending: %s", exc)

    def _restore_vaults(self) -> None:
        r"""Restaura todos os vaults."""
        try:
            vaults_data = self.state.load_all_vaults()
            if not vaults_data:
                return
            for agent_id, vault_data in vaults_data.items():
                self.vaults[agent_id] = _restore_vault(vault_data)
            logger.info("Vaults restaurados: %d", len(self.vaults))
        except Exception as exc:
            logger.warning("Falha ao restaurar vaults: %s", exc)

    def _restore_marketplace(self) -> None:
        r"""Restaura listings e compras do marketplace."""
        try:
            data = self.state.load_marketplace()
            if data is None:
                return

            listings_raw = data.get("listings", {})
            if listings_raw:
                self.marketplace.listings = {
                    lid: _restore_service_listing(ld)
                    for lid, ld in listings_raw.items()
                }

            purchases_raw = data.get("purchases", {})
            if purchases_raw:
                self.marketplace.purchases = {
                    pid: _restore_purchase_record(pd)
                    for pid, pd in purchases_raw.items()
                }

            self.marketplace._total_volume = data.get("total_volume", 0)
            logger.info(
                "Marketplace restaurado: %d listings, %d compras",
                len(self.marketplace.listings),
                len(self.marketplace.purchases),
            )
        except Exception as exc:
            logger.warning("Falha ao restaurar marketplace: %s", exc)

    def _restore_oracle(self) -> None:
        r"""Restaura estado do oracle."""
        try:
            data = self.state.load_oracle_prices()
            if data is None:
                return

            self.oracle.oracles = data.get("oracles", {})

            feeds_raw = data.get("feeds", {})
            if feeds_raw:
                from collections import defaultdict
                self.oracle.feeds = defaultdict(list)
                for symbol, points in feeds_raw.items():
                    self.oracle.feeds[symbol] = [
                        _restore_price_point(p) for p in points
                    ]

            reports_raw = data.get("reports", [])
            if reports_raw:
                self.oracle.reports = [
                    _restore_oracle_report(r) for r in reports_raw
                ]

            logger.info(
                "Oracle restaurado: %d oracles, %d símbolos",
                len(self.oracle.oracles),
                len(self.oracle.feeds),
            )
        except Exception as exc:
            logger.warning("Falha ao restaurar oracle: %s", exc)

    def _restore_faucet(self) -> None:
        r"""Restaura estado do faucet."""
        try:
            data = self.state.load_faucet_state()
            if data is None:
                return

            claims_raw = data.get("claims", {})
            if claims_raw:
                self.faucet._claims = {
                    agent_id: [_restore_faucet_claim(c) for c in claim_list]
                    for agent_id, claim_list in claims_raw.items()
                }

            self.faucet.amount_sats = data.get("amount_sats", self.faucet.amount_sats)
            self.faucet.cooldown = data.get("cooldown", self.faucet.cooldown)
            self.faucet.max_total_sats = data.get("max_total_sats", self.faucet.max_total_sats)
            self.faucet._global_claims = data.get("global_claims", 0)
            self.faucet._total_distributed = data.get("total_distributed", 0)
            self.faucet._rate_limit_window = data.get("rate_limit_window", 60)
            self.faucet._rate_limit_count = data.get("rate_limit_count", 0)
            self.faucet._rate_limit_start = data.get("rate_limit_start", time.time())

            logger.info(
                "Faucet restaurado: %d agents, %d claims globais",
                len(self.faucet._claims),
                self.faucet._global_claims,
            )
        except Exception as exc:
            logger.warning("Falha ao restaurar faucet: %s", exc)

    def _restore_obscura(self) -> None:
        r"""Restaura sessões Obscura."""
        try:
            sessions_data = self.state.load_obscura_sessions()
            if sessions_data:
                from baitcoin_obscura.bridge import BrowserSession
                self.obscura_bridge._sessions = {
                    sid: BrowserSession(
                        session_id=d["session_id"],
                        cdp_url=d["cdp_url"],
                        created_at=d.get("created_at", time.time()),
                        page_count=d.get("page_count", 0),
                        total_cost_sats=d.get("total_cost_sats", 0),
                        is_active=d.get("is_active", False),
                    )
                    for sid, d in sessions_data.items()
                }

            obscura_stats = self.state.load_obscura_tasks()
            if obscura_stats:
                self.obscura_bridge._total_ops = obscura_stats.get("total_ops", 0)
                self.obscura_bridge._total_cost_sats = obscura_stats.get(
                    "total_cost_sats", 0
                )

            if sessions_data:
                logger.info("Obscura restaurado: %d sessões", len(sessions_data))
        except Exception as exc:
            logger.warning("Falha ao restaurar obscura: %s", exc)

    # ================================================================
    # SNAPSHOT + COMPACTAÇÃO
    # ================================================================

    def force_snapshot(self) -> None:
        r"""Força snapshot imediato de todos os namespaces.

        Útil antes de encerrar o processo para garantir durabilidade.
        """
        self.persist_all()
        self.state.force_snapshot_all()
        logger.info("Snapshot forçado de todos os namespaces.")

    def compact_all(self) -> Dict[str, int]:
        r"""Compacta WAL de todos os namespaces (snapshot + limpeza)."""
        self.persist_all()
        result = self.state.compact_all()
        total = sum(result.values())
        logger.info("Compactação concluída: %d segmentos WAL removidos.", total)
        return result

    # ================================================================
    # STATUS
    # ================================================================

    def to_dict(self) -> dict:
        r"""Retorna resumo completo do estado do ecossistema."""
        return {
            "blockchain": self.blockchain.to_dict(),
            "mempool": self.mempool.to_dict(),
            "token": self.token.to_dict(),
            "agents": self.registry.to_dict(),
            "staking": self.staking.to_dict(),
            "lending": self.lending.to_dict(),
            "marketplace": self.marketplace.to_dict(),
            "vaults": {
                aid: v.to_dict() for aid, v in self.vaults.items()
            },
            "oracle": self.oracle.to_dict(),
            "faucet": self.faucet.get_stats(),
            "obscura": self.obscura_bridge.get_stats(),
            "persistence": self.store.get_stats(),
        }

    def get_persistence_stats(self) -> dict:
        r"""Retorna estatísticas da camada de persistência."""
        return self.store.get_stats()
