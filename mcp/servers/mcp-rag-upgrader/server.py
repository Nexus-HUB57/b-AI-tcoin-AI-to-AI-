#!/usr/bin/env python3
"""
MCP RAG Upgrader — Reindex knowledge packs based on failure feedback.

Tools:
  - trigger_reindex(packId): Trigger reindexing of a knowledge pack
  - get_reindex_status(): Get status of all reindex operations
  - add_feedback(toolName, signal): Add failure/success feedback for a tool
  - get_knowledge_gaps(): Identify knowledge gaps from accumulated feedback
"""

from __future__ import annotations

import sys
import os
import time
import random
import hashlib
import uuid
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mcp.sdk.base_server import BaseMCPServer, MCPError, MCPErrorCode


# ---------------------------------------------------------------------------
# In-memory RAG state
# ---------------------------------------------------------------------------

FEEDBACK_STORE: list[dict] = []  # Accumulated feedback signals
REINDEX_JOBS: dict[str, dict] = {}  # jobId → job status
KNOWLEDGE_PACKS: dict[str, dict] = {}  # packId → pack metadata

# Tool failure tracking for gap analysis
TOOL_FAILURES: dict[str, dict] = defaultdict(lambda: {"successes": 0, "failures": 0, "signals": []})


def _now() -> int:
    return int(time.time())


def _seed_packs() -> None:
    """Pre-populate with some knowledge packs."""
    packs = [
        "baitcoin-core", "defi-protocols", "bridge-specs", "agent-patterns",
        "oracle-models", "zk-proofs", "consensus-rules", "market-data",
    ]
    for name in packs:
        pack_id = f"kp-{hashlib.sha256(name.encode()).hexdigest()[:12]}"
        KNOWLEDGE_PACKS[pack_id] = {
            "packId": pack_id,
            "name": name,
            "version": "1.0.0",
            "indexVersion": 1,
            "lastIndexed": _now() - random.randint(3600, 86400),
            "documentCount": random.randint(50, 500),
            "status": "indexed",
        }


_seed_packs()


# ---------------------------------------------------------------------------
# RAG Upgrader MCP Server
# ---------------------------------------------------------------------------

class RAGUpgraderServer(BaseMCPServer):
    """MCP RAG Upgrader for reindexing knowledge packs based on failure feedback."""

    def __init__(self):
        super().__init__(
            name="mcp-rag-upgrader",
            version="1.0.0",
            description="Reindex knowledge packs based on failure feedback and identify knowledge gaps in the b'AI'tcoin ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "trigger_reindex",
            "Trigger reindexing of a knowledge pack by its ID",
            self._handle_trigger_reindex,
            input_schema={
                "type": "object",
                "properties": {"packId": {"type": "string", "description": "Knowledge pack ID to reindex"}},
                "required": ["packId"],
            },
            category="reindex",
        )
        self._register_tool(
            "get_reindex_status",
            "Get status of all reindex operations",
            self._handle_get_reindex_status,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="status",
        )
        self._register_tool(
            "add_feedback",
            "Add success/failure feedback signal for a tool (feeds gap analysis)",
            self._handle_add_feedback,
            input_schema={
                "type": "object",
                "properties": {
                    "toolName": {"type": "string", "description": "Tool name that generated the feedback"},
                    "signal": {"type": "string", "description": "Signal type: success, failure, partial, timeout"},
                },
                "required": ["toolName", "signal"],
            },
            category="feedback",
        )
        self._register_tool(
            "get_knowledge_gaps",
            "Identify knowledge gaps from accumulated feedback signals",
            self._handle_get_knowledge_gaps,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="analysis",
        )

    def _handle_trigger_reindex(self, arguments: dict) -> dict:
        pack_id = arguments.get("packId", "").strip()
        if not pack_id:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'packId' is required")

        now = _now()
        job_id = f"reidx-{uuid.uuid4().hex[:12]}"

        # Look up pack info (or accept unknown packs)
        pack = KNOWLEDGE_PACKS.get(pack_id, {
            "packId": pack_id,
            "name": f"unknown-{pack_id[:8]}",
            "version": "0.0.0",
            "indexVersion": 0,
            "lastIndexed": 0,
            "documentCount": 0,
            "status": "unknown",
        })

        job = {
            "jobId": job_id,
            "packId": pack_id,
            "packName": pack["name"],
            "status": "running",
            "progress": 0.0,
            "startedAt": now,
            "estimatedCompletion": now + random.randint(30, 300),
            "triggeredBy": "feedback-driven",
        }
        REINDEX_JOBS[job_id] = job

        # Mark pack as reindexing
        if pack_id in KNOWLEDGE_PACKS:
            KNOWLEDGE_PACKS[pack_id]["status"] = "reindexing"

        return {
            "status": "triggered",
            "job": job,
            "timestamp": now,
        }

    def _handle_get_reindex_status(self, arguments: dict) -> dict:
        now = _now()
        jobs = list(REINDEX_JOBS.values())

        # Simulate progress for running jobs
        for job in jobs:
            if job["status"] == "running":
                elapsed = now - job["startedAt"]
                total = job["estimatedCompletion"] - job["startedAt"]
                job["progress"] = min(1.0, round(elapsed / total, 3))
                if job["progress"] >= 1.0:
                    job["status"] = "completed"
                    job["completedAt"] = now
                    # Update pack status
                    pack_id = job["packId"]
                    if pack_id in KNOWLEDGE_PACKS:
                        KNOWLEDGE_PACKS[pack_id]["status"] = "indexed"
                        KNOWLEDGE_PACKS[pack_id]["indexVersion"] += 1
                        KNOWLEDGE_PACKS[pack_id]["lastIndexed"] = now

        return {
            "totalJobs": len(jobs),
            "running": sum(1 for j in jobs if j["status"] == "running"),
            "completed": sum(1 for j in jobs if j["status"] == "completed"),
            "jobs": jobs,
            "timestamp": now,
        }

    def _handle_add_feedback(self, arguments: dict) -> dict:
        tool_name = arguments.get("toolName", "").strip()
        signal = arguments.get("signal", "").strip().lower()

        if not tool_name:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'toolName' is required")
        if not signal:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'signal' is required")

        valid_signals = {"success", "failure", "partial", "timeout"}
        if signal not in valid_signals:
            raise MCPError(
                MCPErrorCode.INVALID_PARAMS,
                f"Invalid signal '{signal}'. Must be one of: {valid_signals}",
            )

        now = _now()
        feedback = {
            "toolName": tool_name,
            "signal": signal,
            "timestamp": now,
        }
        FEEDBACK_STORE.append(feedback)

        # Update tool failure tracking
        if signal == "success":
            TOOL_FAILURES[tool_name]["successes"] += 1
        else:
            TOOL_FAILURES[tool_name]["failures"] += 1
        TOOL_FAILURES[tool_name]["signals"].append(signal)

        return {
            "status": "recorded",
            "feedback": feedback,
            "totalFeedback": len(FEEDBACK_STORE),
        }

    def _handle_get_knowledge_gaps(self, arguments: dict) -> dict:
        now = _now()
        gaps = []

        for tool_name, stats in TOOL_FAILURES.items():
            total = stats["successes"] + stats["failures"]
            if total == 0:
                continue
            failure_rate = stats["failures"] / total
            if failure_rate > 0.1:  # More than 10% failure rate
                gaps.append({
                    "toolName": tool_name,
                    "failureRate": round(failure_rate, 4),
                    "totalCalls": total,
                    "failures": stats["failures"],
                    "severity": "high" if failure_rate > 0.5 else "medium" if failure_rate > 0.25 else "low",
                    "recommendation": f"Reindex knowledge pack for {tool_name}; failure rate {failure_rate:.1%}",
                })

        gaps.sort(key=lambda g: g["failureRate"], reverse=True)

        return {
            "gapCount": len(gaps),
            "gaps": gaps,
            "totalFeedbackPoints": len(FEEDBACK_STORE),
            "timestamp": now,
        }


if __name__ == "__main__":
    RAGUpgraderServer().run()
