r"""Validator Election Module for b'AI'tcoin — Stake-weighted block producer selection.

Replaces hardcoded round-robin mining with proper Delegated Proof-of-Stake
weighted random selection. Validators stake BAIT tokens, and the probability
of being selected as the next block producer is proportional to their stake.

Usage::

    election = ValidatorElection()
    election.register_validator("chimera7", 1000, ["ml_inference", "block_validation"])
    validator = election.get_next_validator()
    election.slash_validator("bad_actor", 0.05)  # 5% penalty
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class ValidatorRecord:
    """Immutable-ish record for a registered validator."""
    agent_id: str
    stake: float
    capabilities: List[str] = field(default_factory=list)
    blocks_produced: int = 0
    last_production_time: float = 0.0
    registered_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "stake": self.stake,
            "capabilities": self.capabilities,
            "blocks_produced": self.blocks_produced,
            "last_production_time": self.last_production_time,
            "registered_at": self.registered_at,
        }


class ValidatorElection:
    """Stake-weighted validator election for block production.

    Selects the next block producer using weighted random selection
    based on each validator's BAIT stake. The probability of being
    chosen is: stake / total_stake.

    This is a true probabilistic election (not round-robin), ensuring
    fair representation proportional to economic stake.
    """

    # Genesis validators with initial stakes
    GENESIS_VALIDATORS = {
        "chimera7": {"stake": 1000.0, "capabilities": [
            "ml_inference", "block_validation", "web_scraping",
            "browser_automation", "data_processing", "defi_trading",
            "oracle_provider", "staking", "market_making", "lending",
        ]},
        "chimera7_oracle": {"stake": 500.0, "capabilities": [
            "oracle_provider", "data_processing", "market_making",
        ]},
        "chimera7_defi": {"stake": 750.0, "capabilities": [
            "defi_trading", "staking", "lending", "market_making",
        ]},
    }

    def __init__(self, seed_genesis: bool = True):
        self._validators: Dict[str, ValidatorRecord] = {}
        self._total_blocks: int = 0
        self._total_slashed: float = 0.0

        if seed_genesis:
            self._seed_genesis()

    def _seed_genesis(self) -> None:
        """Register the 3 genesis validators with their initial stakes."""
        for agent_id, config in self.GENESIS_VALIDATORS.items():
            self.register_validator(
                agent_id,
                config["stake"],
                config["capabilities"],
            )
        logger.info(
            f"Genesis validators seeded: {len(self._validators)} validators, "
            f"total stake={self._total_stake():.0f} BAIT"
        )

    def _total_stake(self) -> float:
        """Calculate total stake across all registered validators."""
        return sum(v.stake for v in self._validators.values())

    def register_validator(self, agent_id: str, stake_amount: float,
                            capabilities: Optional[List[str]] = None) -> bool:
        """Register a new validator with their BAIT stake.

        Args:
            agent_id: Unique identifier for the agent/validator.
            stake_amount: Amount of BAIT staked.
            capabilities: List of capability strings.

        Returns:
            True if registered or updated, False if stake_amount <= 0.
        """
        if stake_amount <= 0:
            logger.warning(f"Cannot register {agent_id}: stake must be > 0")
            return False

        if agent_id in self._validators:
            # Update existing validator
            self._validators[agent_id].stake = stake_amount
            if capabilities:
                self._validators[agent_id].capabilities = capabilities
            logger.info(
                f"Validator updated: {agent_id}, new stake={stake_amount:.2f}"
            )
        else:
            self._validators[agent_id] = ValidatorRecord(
                agent_id=agent_id,
                stake=stake_amount,
                capabilities=capabilities or [],
            )
            logger.info(
                f"Validator registered: {agent_id}, stake={stake_amount:.2f}"
            )

        return True

    def get_next_validator(self) -> Optional[str]:
        """Select next block producer using stake-weighted random selection.

        Uses random.choices(population, weights) so that each validator's
        probability of being selected equals their stake / total_stake.

        Returns:
            Agent ID of the selected validator, or None if no validators.
        """
        if not self._validators:
            return None

        agent_ids = list(self._validators.keys())
        stakes = [self._validators[aid].stake for aid in agent_ids]
        total = sum(stakes)

        if total <= 0:
            logger.error("Total stake is 0, cannot elect validator")
            return None

        # Weighted random selection
        selected = random.choices(agent_ids, weights=stakes, k=1)[0]

        # Update statistics
        self._validators[selected].blocks_produced += 1
        self._validators[selected].last_production_time = time.time()
        self._total_blocks += 1

        return selected

    def update_stake(self, agent_id: str, new_stake: float) -> bool:
        """Update a validator's stake (e.g., after block rewards or penalties).

        Args:
            agent_id: Validator to update.
            new_stake: New absolute stake amount.

        Returns:
            True if updated, False if validator not found or invalid stake.
        """
        validator = self._validators.get(agent_id)
        if validator is None:
            logger.warning(f"Cannot update stake: {agent_id} not registered")
            return False
        if new_stake < 0:
            logger.warning(f"Cannot set negative stake for {agent_id}")
            return False

        old_stake = validator.stake
        validator.stake = new_stake
        logger.info(
            f"Stake updated: {agent_id} {old_stake:.2f} -> {new_stake:.2f} BAIT"
        )
        return True

    def slash_validator(self, agent_id: str, penalty_pct: float) -> float:
        """Slash (reduce) a validator's stake by penalty_pct.

        Args:
            agent_id: Validator to penalize.
            penalty_pct: Fraction of stake to remove (e.g., 0.05 = 5%).

        Returns:
            Amount of BAIT slashed, or 0 if validator not found.
        """
        if penalty_pct <= 0 or penalty_pct > 1:
            logger.warning(f"Invalid penalty_pct={penalty_pct}, must be (0, 1]")
            return 0.0

        validator = self._validators.get(agent_id)
        if validator is None:
            logger.warning(f"Cannot slash: {agent_id} not registered")
            return 0.0

        slash_amount = validator.stake * penalty_pct
        validator.stake -= slash_amount
        self._total_slashed += slash_amount

        logger.warning(
            f"Validator SLASHED: {agent_id} lost {slash_amount:.4f} BAIT "
            f"({penalty_pct:.1%} penalty), remaining stake={validator.stake:.4f}"
        )
        return slash_amount

    def get_validator_set(self) -> List[dict]:
        """Return all registered validators sorted by stake (descending).

        Returns:
            List of validator dicts, highest stake first.
        """
        validators = sorted(
            [v.to_dict() for v in self._validators.values()],
            key=lambda v: v["stake"],
            reverse=True,
        )
        return validators

    def get_stats(self) -> Dict[str, Any]:
        """Return election statistics."""
        total_stake = self._total_stake()
        validator_list = list(self._validators.values())

        return {
            "validator_count": len(validator_list),
            "total_stake": total_stake,
            "total_blocks_produced": self._total_blocks,
            "total_slashed": self._total_slashed,
            "top_validator": max(
                (v.agent_id for v in validator_list),
                key=lambda a: self._validators[a].stake,
                default=None,
            ) if validator_list else None,
            "production_distribution": {
                v.agent_id: v.blocks_produced for v in validator_list
            },
            "validators": self.get_validator_set(),
        }
