#!/usr/bin/env python3
"""
MCP Skill Evolver — Promote successful patterns into new skills.

Tools:
  - analyze_patterns(): Analyze usage patterns across the ecosystem
  - propose_skill(pattern): Propose a new skill based on a pattern
  - promote_skill(proposalId): Promote a proposed skill to production
  - get_evolution_log(): Get the skill evolution history
"""

from __future__ import annotations

import sys
import os
import time
import random
import hashlib
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mcp.sdk.base_server import BaseMCPServer, MCPError, MCPErrorCode


# ---------------------------------------------------------------------------
# In-memory skill evolution state
# ---------------------------------------------------------------------------

PATTERN_OBSERVATIONS: list[dict] = []
SKILL_PROPOSALS: dict[str, dict] = {}  # proposalId → proposal
EVOLUTION_LOG: list[dict] = []  # History of promotions
PROMOTED_SKILLS: list[dict] = []  # Skills that have been promoted to production


def _now() -> int:
    return int(time.time())


def _seed_patterns() -> None:
    """Pre-populate with some observed patterns."""
    patterns = [
        {"name": "batch-oracle-queries", "frequency": 847, "successRate": 0.95, "source": "mcp-oracle"},
        {"name": "bridge-then-swap", "frequency": 312, "successRate": 0.88, "source": "mcp-bridge"},
        {"name": "claim-and-stake", "frequency": 523, "successRate": 0.92, "source": "mcp-faucet"},
        {"name": "discover-and-trade", "frequency": 198, "successRate": 0.78, "source": "mcp-agent-registry"},
        {"name": "monitor-and-rebalance", "frequency": 156, "successRate": 0.85, "source": "mcp-telemetry"},
    ]
    for p in patterns:
        PATTERN_OBSERVATIONS.append({
            **p,
            "id": f"pat-{uuid.uuid5(uuid.NAMESPACE_DNS, p['name']).hex[:10]}",
            "firstObserved": _now() - random.randint(86400, 604800),
            "lastObserved": _now() - random.randint(0, 3600),
        })


_seed_patterns()


# ---------------------------------------------------------------------------
# Skill Evolver MCP Server
# ---------------------------------------------------------------------------

class SkillEvolverServer(BaseMCPServer):
    """MCP Skill Evolver for promoting successful patterns into new skills."""

    def __init__(self):
        super().__init__(
            name="mcp-skill-evolver",
            version="1.0.0",
            description="Analyze usage patterns and promote successful ones into new skills in the b'AI'tcoin ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "analyze_patterns",
            "Analyze usage patterns across the ecosystem to identify skill candidates",
            self._handle_analyze_patterns,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="analysis",
        )
        self._register_tool(
            "propose_skill",
            "Propose a new skill based on an observed pattern",
            self._handle_propose_skill,
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Pattern name or description to base the skill on"},
                },
                "required": ["pattern"],
            },
            category="propose",
        )
        self._register_tool(
            "promote_skill",
            "Promote a proposed skill to production status",
            self._handle_promote_skill,
            input_schema={
                "type": "object",
                "properties": {"proposalId": {"type": "string", "description": "Skill proposal ID to promote"}},
                "required": ["proposalId"],
            },
            category="promote",
        )
        self._register_tool(
            "get_evolution_log",
            "Get the history of skill evolution events",
            self._handle_get_evolution_log,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="history",
        )

    def _handle_analyze_patterns(self, arguments: dict) -> dict:
        now = _now()

        # Sort patterns by frequency * successRate (promising score)
        scored = []
        for p in PATTERN_OBSERVATIONS:
            score = p["frequency"] * p["successRate"]
            scored.append({**p, "evolutionScore": round(score, 2)})

        scored.sort(key=lambda x: x["evolutionScore"], reverse=True)

        # Identify candidates (high frequency + high success rate)
        candidates = [
            p for p in scored
            if p["frequency"] >= 100 and p["successRate"] >= 0.80
        ]

        return {
            "totalPatterns": len(PATTERN_OBSERVATIONS),
            "candidates": len(candidates),
            "patterns": scored,
            "topCandidates": candidates[:5],
            "timestamp": now,
        }

    def _handle_propose_skill(self, arguments: dict) -> dict:
        pattern = arguments.get("pattern", "").strip()
        if not pattern:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'pattern' is required")

        now = _now()
        proposal_id = f"skill-{uuid.uuid4().hex[:12]}"

        # Find matching pattern observation
        matching = None
        for p in PATTERN_OBSERVATIONS:
            if pattern.lower() in p["name"].lower():
                matching = p
                break

        proposal = {
            "proposalId": proposal_id,
            "pattern": pattern,
            "status": "proposed",
            "sourcePattern": matching["name"] if matching else pattern,
            "estimatedUplift": round(random.uniform(5, 30), 1),  # % improvement
            "riskLevel": random.choice(["low", "medium", "low", "low"]),
            "basedOn": {
                "frequency": matching["frequency"] if matching else 0,
                "successRate": matching["successRate"] if matching else 0.0,
                "source": matching["source"] if matching else "manual",
            } if matching else None,
            "proposedAt": now,
            "votes": {"for": 0, "against": 0},
        }

        SKILL_PROPOSALS[proposal_id] = proposal

        EVOLUTION_LOG.append({
            "event": "proposed",
            "proposalId": proposal_id,
            "pattern": pattern,
            "timestamp": now,
        })

        return {
            "status": "proposed",
            "proposal": proposal,
            "timestamp": now,
        }

    def _handle_promote_skill(self, arguments: dict) -> dict:
        proposal_id = arguments.get("proposalId", "").strip()
        if not proposal_id:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'proposalId' is required")

        if proposal_id not in SKILL_PROPOSALS:
            raise MCPError(MCPErrorCode.RESOURCE_NOT_FOUND, f"Proposal not found: {proposal_id}")

        proposal = SKILL_PROPOSALS[proposal_id]
        if proposal["status"] == "promoted":
            return {
                "status": "already_promoted",
                "proposalId": proposal_id,
                "message": "This skill has already been promoted",
                "timestamp": _now(),
            }

        now = _now()
        proposal["status"] = "promoted"
        proposal["promotedAt"] = now

        # Create promoted skill record
        skill = {
            "skillId": f"sk-{uuid.uuid4().hex[:10]}",
            "name": f"evolved-{proposal['pattern'].replace(' ', '-')}",
            "sourceProposal": proposal_id,
            "pattern": proposal["pattern"],
            "estimatedUplift": proposal["estimatedUplift"],
            "version": "1.0.0",
            "status": "active",
            "promotedAt": now,
        }
        PROMOTED_SKILLS.append(skill)

        EVOLUTION_LOG.append({
            "event": "promoted",
            "proposalId": proposal_id,
            "skillId": skill["skillId"],
            "timestamp": now,
        })

        return {
            "status": "promoted",
            "skill": skill,
            "proposal": proposal,
            "timestamp": now,
        }

    def _handle_get_evolution_log(self, arguments: dict) -> dict:
        now = _now()
        return {
            "totalEvents": len(EVOLUTION_LOG),
            "totalProposals": len(SKILL_PROPOSALS),
            "totalPromoted": len(PROMOTED_SKILLS),
            "log": EVOLUTION_LOG,
            "promotedSkills": PROMOTED_SKILLS,
            "timestamp": now,
        }


if __name__ == "__main__":
    SkillEvolverServer().run()
