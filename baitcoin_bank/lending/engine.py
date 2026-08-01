r"""
Motor de Empréstimos P2P - Lending descentralizado AI-to-AI.

Agentes AI podem:
- Oferecer liquidez (fornecer BAIT para empréstimos)
- Tomar empréstimos (collateralized)
- Definir taxas de juros personalizadas

Segurança:
- Colateral obrigatório (over-collateralization)
- Liquidação automática se collateral cai abaixo do mínimo
- Taxa de juros determinada pelo mercado
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class LoanState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REPAID = "repaid"
    LIQUIDATED = "liquidated"
    DEFAULTED = "defaulted"


@dataclass
class LoanOffer:
    """Oferta de empréstimo."""
    offer_id: str
    lender_agent: str
    amount_sats: int
    interest_rate: float  # APY em %
    duration_seconds: float
    min_collateral_ratio: float = 1.5  # 150% colateral
    created_at: float = field(default_factory=time.time)


@dataclass
class ActiveLoan:
    """Empréstimo ativo."""
    loan_id: str
    borrower_agent: str
    lender_agent: str
    principal_sats: int
    collateral_sats: int
    interest_rate: float
    created_at: float
    due_at: float
    state: LoanState = LoanState.ACTIVE

    @property
    def collateral_ratio(self) -> float:
        return self.collateral_sats / max(self.principal_sats, 1)

    @property
    def interest_owed(self) -> int:
        elapsed = time.time() - self.created_at
        return int(self.principal_sats * (self.interest_rate / 100) * (elapsed / 31536000))

    @property
    def total_owed(self) -> int:
        return self.principal_sats + self.interest_owed

    @property
    def is_overdue(self) -> bool:
        return time.time() > self.due_at and self.state == LoanState.ACTIVE


class LendingEngine:
    """Motor de empréstimos P2P do b'AI'tcoin.

    Implementa o lado "Be Your Bank":
    - Cada agente pode ser lender ou borrower
    - Sem KYC - identidade criptográfica
    - Taxas determinadas pelo mercado livre
    - Liquidação automática de posições undercollateralized
    """

    LIQUIDATION_THRESHOLD = 1.2  # Liquidar se ratio < 120%
    DEFAULT_LOAN_DURATION = 2592000  # 30 dias

    def __init__(self):
        self.offers: Dict[str, LoanOffer] = {}
        self.loans: Dict[str, ActiveLoan] = {}
        self.liquidity_pool: int = 0
        self.total_lent: int = 0
        self.total_repaid: int = 0

    def create_offer(self, lender_agent: str, amount_sats: int,
                      interest_rate: float,
                      duration: Optional[float] = None) -> str:
        """Cria oferta de empréstimo."""
        offer_id = f"loan_{hashlib.sha256(f'{lender_agent}:{time.time()}'.encode()).hexdigest()[:12]}"
        self.offers[offer_id] = LoanOffer(
            offer_id=offer_id,
            lender_agent=lender_agent,
            amount_sats=amount_sats,
            interest_rate=interest_rate,
            duration_seconds=duration or self.DEFAULT_LOAN_DURATION,
        )
        return offer_id

    def borrow(self, borrower_agent: str, offer_id: str,
                collateral_sats: int) -> Optional[str]:
        """Toma empréstimo contra colateral."""
        import hashlib
        offer = self.offers.get(offer_id)
        if offer is None:
            return None

        ratio = collateral_sats / max(offer.amount_sats, 1)
        if ratio < offer.min_collateral_ratio:
            return None

        loan_id = f"active_{hashlib.sha256(f'{borrower_agent}:{offer_id}:{time.time()}'.encode()).hexdigest()[:12]}"
        self.loans[loan_id] = ActiveLoan(
            loan_id=loan_id,
            borrower_agent=borrower_agent,
            lender_agent=offer.lender_agent,
            principal_sats=offer.amount_sats,
            collateral_sats=collateral_sats,
            interest_rate=offer.interest_rate,
            created_at=time.time(),
            due_at=time.time() + offer.duration_seconds,
        )
        self.liquidity_pool -= offer.amount_sats
        self.total_lent += offer.amount_sats
        del self.offers[offer_id]
        return loan_id

    def repay(self, loan_id: str, amount_sats: int) -> bool:
        """Paga (parcialmente) um empréstimo."""
        loan = self.loans.get(loan_id)
        if loan is None or loan.state != LoanState.ACTIVE:
            return False

        loan.principal_sats = max(loan.principal_sats - amount_sats, 0)
        self.total_repaid += amount_sats
        if loan.principal_sats <= 0:
            loan.state = LoanState.REPAID
        return True

    def check_liquidations(self) -> List[str]:
        """Verifica e liquida empréstimos undercollateralized."""
        liquidated = []
        for loan_id, loan in self.loans.items():
            if loan.state == LoanState.ACTIVE and loan.collateral_ratio < self.LIQUIDATION_THRESHOLD:
                loan.state = LoanState.LIQUIDATED
                liquidated.append(loan_id)
        return liquidated

    def get_market_rate(self) -> float:
        """Retorna taxa de juros média do mercado."""
        if not self.offers:
            return 0.0
        rates = [o.interest_rate for o in self.offers.values()]
        return sum(rates) / len(rates)

    def to_dict(self) -> dict:
        return {
            "open_offers": len(self.offers),
            "active_loans": sum(1 for l in self.loans.values() if l.state == LoanState.ACTIVE),
            "total_lent_bait": self.total_lent / 100_000_000,
            "total_repaid_bait": self.total_repaid / 100_000_000,
            "market_rate_apy": self.get_market_rate(),
        }