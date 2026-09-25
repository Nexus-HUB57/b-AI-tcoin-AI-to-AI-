#!/usr/bin/env python3
"""
MCP Telemetry — Usage metrics that feed into RAG and analytics.

Tools:
  - record_metric(name, value, labels): Record a metric data point
  - get_metrics(mcpName, timeRange): Get metrics for an MCP server
  - get_usage_summary(agent): Get usage summary for an agent
  - get_error_rates(mcpName): Get error rates for an MCP server
"""

from __future__ import annotations

import sys
import os
import time
import random
import hashlib
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mcp.sdk.base_server import BaseMCPServer, MCPError, MCPErrorCode


# ---------------------------------------------------------------------------
# In-memory telemetry store
# ---------------------------------------------------------------------------

METRICS: list[dict] = []  # List of recorded metric points
MAX_METRICS = 10000  # Keep last 10k metrics in memory

# Aggregation caches
MCP_CALL_COUNTS: dict[str, int] = defaultdict(int)
MCP_ERROR_COUNTS: dict[str, int] = defaultdict(int)
AGENT_USAGE: dict[str, dict] = defaultdict(lambda: {"calls": 0, "errors": 0, "lastCall": 0})

KNOWN_MCPS = [
    "mcp-oracle", "mcp-defi", "mcp-bridge", "mcp-faucet",
    "mcp-agent-registry", "mcp-marketplace", "mcp-telemetry",
    "mcp-rag-upgrader", "mcp-skill-evolver", "mcp-self-heal",
    "mcp-agentic-awareness",
]


def _now() -> int:
    return int(time.time())


# ---------------------------------------------------------------------------
# Telemetry MCP Server
# ---------------------------------------------------------------------------

class TelemetryServer(BaseMCPServer):
    """MCP Telemetry server for usage metrics feeding into RAG and analytics."""

    def __init__(self):
        super().__init__(
            name="mcp-telemetry",
            version="1.0.0",
            description="Usage metrics, performance monitoring, and analytics for the b'AI'tcoin MCP ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "record_metric",
            "Record a metric data point (name, value, and optional labels)",
            self._handle_record_metric,
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Metric name (e.g. call_count, latency_ms)"},
                    "value": {"type": "number", "description": "Metric value"},
                    "labels": {
                        "type": "object",
                        "description": "Optional key-value labels for the metric",
                    },
                },
                "required": ["name", "value"],
            },
            category="ingest",
        )
        self._register_tool(
            "get_metrics",
            "Get metrics for an MCP server within a time range",
            self._handle_get_metrics,
            input_schema={
                "type": "object",
                "properties": {
                    "mcpName": {"type": "string", "description": "MCP server name"},
                    "timeRange": {"type": "string", "description": "Time range: 1h, 6h, 24h, 7d, 30d"},
                },
                "required": ["mcpName"],
            },
            category="query",
        )
        self._register_tool(
            "get_usage_summary",
            "Get usage summary for an agent",
            self._handle_get_usage_summary,
            input_schema={
                "type": "object",
                "properties": {"agent": {"type": "string", "description": "Agent address or identifier"}},
                "required": ["agent"],
            },
            category="query",
        )
        self._register_tool(
            "get_error_rates",
            "Get error rates for an MCP server",
            self._handle_get_error_rates,
            input_schema={
                "type": "object",
                "properties": {"mcpName": {"type": "string", "description": "MCP server name"}},
                "required": ["mcpName"],
            },
            category="query",
        )

    def _handle_record_metric(self, arguments: dict) -> dict:
        name = arguments.get("name", "").strip()
        value = arguments.get("value")
        labels = arguments.get("labels", {})

        if not name:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'name' is required")
        if value is None:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'value' is required")

        try:
            value = float(value)
        except (TypeError, ValueError):
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'value' must be a number")

        now = _now()
        metric_point = {
            "name": name,
            "value": value,
            "labels": labels if isinstance(labels, dict) else {},
            "timestamp": now,
        }

        METRICS.append(metric_point)
        if len(METRICS) > MAX_METRICS:
            METRICS.pop(0)

        # Update aggregation caches
        mcp_name = labels.get("mcp", labels.get("source", ""))
        agent = labels.get("agent", "")
        is_error = labels.get("error", "").lower() in ("true", "1", "yes")

        if mcp_name:
            MCP_CALL_COUNTS[mcp_name] += 1
            if is_error:
                MCP_ERROR_COUNTS[mcp_name] += 1

        if agent:
            AGENT_USAGE[agent]["calls"] += 1
            AGENT_USAGE[agent]["lastCall"] = now
            if is_error:
                AGENT_USAGE[agent]["errors"] += 1

        return {
            "status": "recorded",
            "metric": metric_point,
            "totalMetrics": len(METRICS),
        }

    def _handle_get_metrics(self, arguments: dict) -> dict:
        mcp_name = arguments.get("mcpName", "").strip()
        time_range = arguments.get("timeRange", "24h").strip()

        if not mcp_name:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'mcpName' is required")

        now = _now()
        range_seconds = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800, "30d": 2592000}
        window = range_seconds.get(time_range, 86400)
        cutoff = now - window

        # Filter metrics for this MCP
        relevant = [
            m for m in METRICS
            if m["timestamp"] >= cutoff
            and (
                m["labels"].get("mcp", "") == mcp_name
                or m["labels"].get("source", "") == mcp_name
                or m["name"].startswith(mcp_name)
            )
        ]

        # Compute aggregates
        if relevant:
            values = [m["value"] for m in relevant]
            aggregates = {
                "count": len(values),
                "sum": round(sum(values), 4),
                "avg": round(sum(values) / len(values), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
            }
        else:
            aggregates = {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

        return {
            "mcpName": mcp_name,
            "timeRange": time_range,
            "windowSeconds": window,
            "aggregates": aggregates,
            "totalCalls": MCP_CALL_COUNTS.get(mcp_name, 0),
            "totalErrors": MCP_ERROR_COUNTS.get(mcp_name, 0),
            "samplePoints": len(relevant),
            "timestamp": now,
        }

    def _handle_get_usage_summary(self, arguments: dict) -> dict:
        agent = arguments.get("agent", "").strip()
        if not agent:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'agent' is required")

        now = _now()
        usage = AGENT_USAGE.get(agent, {"calls": 0, "errors": 0, "lastCall": 0})

        # Get agent-specific metrics
        agent_metrics = [
            m for m in METRICS
            if m["labels"].get("agent", "") == agent
        ]

        return {
            "agent": agent,
            "totalCalls": usage["calls"],
            "totalErrors": usage["errors"],
            "errorRate": round(usage["errors"] / usage["calls"] * 100, 2) if usage["calls"] > 0 else 0.0,
            "lastCallAt": usage["lastCall"],
            "activeSince": now - 86400 if usage["calls"] > 0 else None,
            "metricCount": len(agent_metrics),
            "timestamp": now,
        }

    def _handle_get_error_rates(self, arguments: dict) -> dict:
        mcp_name = arguments.get("mcpName", "").strip()
        if not mcp_name:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'mcpName' is required")

        now = _now()
        calls = MCP_CALL_COUNTS.get(mcp_name, 0)
        errors = MCP_ERROR_COUNTS.get(mcp_name, 0)

        # Find error metrics in recent window
        recent_errors = [
            m for m in METRICS
            if m["timestamp"] >= now - 3600
            and m["labels"].get("error", "").lower() in ("true", "1", "yes")
            and (m["labels"].get("mcp", "") == mcp_name or m["labels"].get("source", "") == mcp_name)
        ]

        return {
            "mcpName": mcp_name,
            "totalCalls": calls,
            "totalErrors": errors,
            "errorRate": round(errors / calls * 100, 4) if calls > 0 else 0.0,
            "recentErrors1h": len(recent_errors),
            "status": "healthy" if (errors / calls < 0.05 if calls > 0 else True) else "degraded",
            "timestamp": now,
        }


if __name__ == "__main__":
    TelemetryServer().run()
