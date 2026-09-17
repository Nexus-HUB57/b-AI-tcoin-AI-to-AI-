r"""
Governador - Sistema de Governança On-Chain.

Stakers de BAIT podem:
- Criar propostas
- Votar (1 token = 1 voto)
- Executar propostas aprovadas

Parâmetros:
- Quorum: 4% do supply total
- Votação: 7 dias
- Execução: 2 dias após aprovação
- Threshold: maioria simples (>50%)
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class ProposalState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUCCEEDED = "succeeded"
    DEFEATED = "defeated"
    QUEUED = "queued"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass
class Vote:
    """Voto individual."""
    voter: str
    support: bool  # True = a favor
    weight: int  # poder de voto (baseado em stake)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Proposal:
    """Proposta de governança."""
    proposal_id: str
    proposer: str
    title: str
    description: str
    created_at: float = field(default_factory=time.time)
    voting_ends: float = 0.0
    state: ProposalState = ProposalState.PENDING
    votes_for: int = 0
    votes_against: int = 0
    voters: List[str] = field(default_factory=list)
    execution_data: dict = field(default_factory=dict)

    @property
    def total_votes(self) -> int:
        return self.votes_for + self.votes_against

    @property
    def support_pct(self) -> float:
        if self.total_votes == 0:
            return 0.0
        return (self.votes_for / self.total_votes) * 100

    def is_active(self) -> bool:
        return (self.state == ProposalState.ACTIVE
                and time.time() < self.voting_ends)


class Governor:
    """Governador do protocolo b'AI'tcoin.

    Gerencia o ciclo de vida de propostas e votações.
    """

    QUORUM_PCT = 4.0  # 4% do supply
    VOTING_PERIOD = 604800  # 7 dias
    EXECUTION_DELAY = 172800  # 2 dias
    PASS_THRESHOLD = 50.0  # 50% dos votos

    def __init__(self, total_supply_sats: int):
        self.total_supply = total_supply_sats
        self.quorum_sats = int(self.total_supply * (self.QUORUM_PCT / 100))
        self.proposals: Dict[str, Proposal] = {}
        self.proposal_count = 0

    def create_proposal(self, proposer: str, title: str,
                          description: str, execution_data: dict = None) -> str:
        """Cria nova proposta."""
        self.proposal_count += 1
        pid = f"PROPOSAL_{self.proposal_count:04d}"
        self.proposals[pid] = Proposal(
            proposal_id=pid,
            proposer=proposer,
            title=title,
            description=description,
            voting_ends=time.time() + self.VOTING_PERIOD,
            execution_data=execution_data or {},
            state=ProposalState.ACTIVE,
        )
        return pid

    def vote(self, proposal_id: str, voter: str,
              support: bool, stake_weight: int) -> bool:
        """Registra voto."""
        prop = self.proposals.get(proposal_id)
        if prop is None or not prop.is_active():
            return False
        if voter in prop.voters:
            return False

        prop.voters.append(voter)
        if support:
            prop.votes_for += stake_weight
        else:
            prop.votes_against += stake_weight
        return True

    def finalize_proposal(self, proposal_id: str) -> ProposalState:
        """Finaliza proposta após período de votação."""
        prop = self.proposals.get(proposal_id)
        if prop is None or prop.state != ProposalState.ACTIVE:
            return prop.state if prop else ProposalState.PENDING

        if prop.total_votes < self.quorum_sats:
            prop.state = ProposalState.DEFEATED
        elif prop.support_pct >= self.PASS_THRESHOLD:
            prop.state = ProposalState.SUCCEEDED
        else:
            prop.state = ProposalState.DEFEATED

        return prop.state

    def execute_proposal(self, proposal_id: str) -> bool:
        """Executa proposta aprovada."""
        prop = self.proposals.get(proposal_id)
        if prop is None or prop.state != ProposalState.SUCCEEDED:
            return False
        prop.state = ProposalState.EXECUTED
        return True

    def to_dict(self) -> dict:
        active = sum(1 for p in self.proposals.values() if p.is_active())
        return {
            "total_proposals": len(self.proposals),
            "active": active,
            "quorum_required_bait": self.quorum_sats / 100_000_000,
        }
