#!/usr/bin/env python3
"""
MCP Self-Heal — Health checks, service restart, and configuration drift detection.

Tools:
  - health_check(mcpName): Run health check on an MCP server
  - restart_service(mcpName): Restart an MCP service
  - detect_drift(): Detect configuration drift across services
  - get_heal_history(): Get history of self-healing actions
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
# In-memory self-heal state
# ---------------------------------------------------------------------------

HEAL_HISTORY: list[dict] = []  # Log of healing actions
SERVICE_STATES: dict[str, dict] = {}  # mcpName → state

KNOWN_MCPS = [
    "mcp-oracle", "mcp-defi", "mcp-bridge", "mcp-faucet",
    "mcp-agent-registry", "mcp-marketplace", "mcp-telemetry",
    "mcp-rag-upgrader", "mcp-skill-evolver", "mcp-self-heal",
    "mcp-agentic-awareness",
]

# Baseline config for drift detection
BASELINE_CONFIG = {
    "timeoutMs": 30000,
    "memoryMb": 64,
    "cpuMillicores": 100,
    "retryCount": 3,
    "logLevel": "info",
}


def _now() -> int:
    return int(time.time())


def _seed_services() -> None:
    """Initialize service states."""
    for mcp in KNOWN_MCPS:
        SERVICE_STATES[mcp] = {
            "name": mcp,
            "status": "running",
            "healthScore": round(random.uniform(80, 100), 1),
            "lastHealthCheck": _now() - random.randint(60, 3600),
            "restartCount": 0,
            "uptimeSeconds": random.randint(3600, 864000),
            "config": dict(BASELINE_CONFIG),
        }


_seed_services()


# ---------------------------------------------------------------------------
# Self-Heal MCP Server
# ---------------------------------------------------------------------------

class SelfHealServer(BaseMCPServer):
    """MCP Self-Heal for health checks, restarts, and drift detection."""

    def __init__(self):
        super().__init__(
            name="mcp-self-heal",
            version="1.0.0",
            description="Health checks, service restarts, and configuration drift detection for the b'AI'tcoin MCP ecosystem",
        )

    def _register_tools(self) -> None:
        self._register_tool(
            "health_check",
            "Run health check on an MCP server",
            self._handle_health_check,
            input_schema={
                "type": "object",
                "properties": {"mcpName": {"type": "string", "description": "MCP server name to check"}},
                "required": ["mcpName"],
            },
            category="health",
        )
        self._register_tool(
            "restart_service",
            "Restart an MCP service (graceful shutdown + startup)",
            self._handle_restart_service,
            input_schema={
                "type": "object",
                "properties": {"mcpName": {"type": "string", "description": "MCP server name to restart"}},
                "required": ["mcpName"],
            },
            category="remediation",
        )
        self._register_tool(
            "detect_drift",
            "Detect configuration drift across all MCP services",
            self._handle_detect_drift,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="drift",
        )
        self._register_tool(
            "get_heal_history",
            "Get history of self-healing actions",
            self._handle_get_heal_history,
            input_schema={"type": "object", "properties": {}, "required": []},
            category="history",
        )

    def _handle_health_check(self, arguments: dict) -> dict:
        mcp_name = arguments.get("mcpName", "").strip()
        if not mcp_name:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'mcpName' is required")

        now = _now()

        # Ensure service exists in registry
        if mcp_name not in SERVICE_STATES:
            SERVICE_STATES[mcp_name] = {
                "name": mcp_name,
                "status": "unknown",
                "healthScore": 0.0,
                "lastHealthCheck": 0,
                "restartCount": 0,
                "uptimeSeconds": 0,
                "config": dict(BASELINE_CONFIG),
            }

        service = SERVICE_STATES[mcp_name]

        # Simulate health check
        rng = random.Random(hash(f"{mcp_name}:{now // 60}"))
        is_healthy = rng.random() > 0.05  # 95% chance healthy

        if is_healthy:
            health_score = round(rng.uniform(85, 100), 1)
            service["status"] = "running"
            service["healthScore"] = health_score
            status = "healthy"
        else:
            health_score = round(rng.uniform(20, 60), 1)
            service["status"] = "degraded"
            service["healthScore"] = health_score
            status = "unhealthy"

        service["lastHealthCheck"] = now

        check_result = {
            "mcpName": mcp_name,
            "status": status,
            "healthScore": health_score,
            "responseTimeMs": rng.randint(1, 50),
            "memoryUsageMb": round(rng.uniform(20, 60), 1),
            "cpuUsagePct": round(rng.uniform(1, 40), 1),
            "errorCount": rng.randint(0, 3),
            "lastRestart": service.get("lastRestart", None),
            "uptimeSeconds": service["uptimeSeconds"],
            "timestamp": now,
        }

        HEAL_HISTORY.append({
            "event": "health_check",
            "mcpName": mcp_name,
            "result": status,
            "timestamp": now,
        })

        return check_result

    def _handle_restart_service(self, arguments: dict) -> dict:
        mcp_name = arguments.get("mcpName", "").strip()
        if not mcp_name:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Parameter 'mcpName' is required")

        if mcp_name == "mcp-self-heal":
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Cannot restart self-heal service via itself (infinite loop)")

        now = _now()

        if mcp_name not in SERVICE_STATES:
            raise MCPError(MCPErrorCode.RESOURCE_NOT_FOUND, f"Service not found: {mcp_name}")

        service = SERVICE_STATES[mcp_name]

        # Simulate restart
        old_status = service["status"]
        service["status"] = "restarting"
        service["restartCount"] += 1
        service["lastRestart"] = now
        service["uptimeSeconds"] = 0

        # After restart, mark as running
        service["status"] = "running"
        service["healthScore"] = 100.0

        HEAL_HISTORY.append({
            "event": "restart",
            "mcpName": mcp_name,
            "previousStatus": old_status,
            "newStatus": "running",
            "restartCount": service["restartCount"],
            "timestamp": now,
        })

        return {
            "mcpName": mcp_name,
            "status": "restarted",
            "previousStatus": old_status,
            "restartCount": service["restartCount"],
            "healthScore": service["healthScore"],
            "timestamp": now,
        }

    def _handle_detect_drift(self, arguments: dict) -> dict:
        now = _now()
        drifts = []

        for mcp_name, service in SERVICE_STATES.items():
            config = service.get("config", {})
            for key, baseline_value in BASELINE_CONFIG.items():
                current_value = config.get(key, baseline_value)
                if current_value != baseline_value:
                    drifts.append({
                        "mcpName": mcp_name,
                        "key": key,
                        "expected": baseline_value,
                        "actual": current_value,
                        "severity": "high" if key in ("timeoutMs", "memoryMb") else "low",
                    })

        # Simulate a few random drifts for realism
        rng = random.Random(now // 300)
        for mcp_name in list(SERVICE_STATES.keys())[:3]:
            if rng.random() < 0.15:
                key = rng.choice(list(BASELINE_CONFIG.keys()))
                service = SERVICE_STATES[mcp_name]
                if service["config"].get(key) == BASELINE_CONFIG[key]:
                    # Only add simulated drift if not already drifted
                    if key == "logLevel":
                        service["config"][key] = "debug"
                    elif isinstance(BASELINE_CONFIG[key], int):
                        service["config"][key] = BASELINE_CONFIG[key] + rng.randint(1, 10) * 1000
                    drifts.append({
                        "mcpName": mcp_name,
                        "key": key,
                        "expected": BASELINE_CONFIG[key],
                        "actual": service["config"][key],
                        "severity": "high" if key in ("timeoutMs", "memoryMb") else "low",
                    })

        HEAL_HISTORY.append({
            "event": "drift_detection",
            "driftCount": len(drifts),
            "timestamp": now,
        })

        return {
            "driftCount": len(drifts),
            "drifts": drifts,
            "servicesChecked": len(SERVICE_STATES),
            "baseline": BASELINE_CONFIG,
            "timestamp": now,
        }

    def _handle_get_heal_history(self, arguments: dict) -> dict:
        now = _now()
        # Keep only last 1000 events
        recent = HEAL_HISTORY[-1000:] if len(HEAL_HISTORY) > 1000 else HEAL_HISTORY

        return {
            "totalEvents": len(HEAL_HISTORY),
            "recentEvents": len(recent),
            "history": recent,
            "serviceStates": {
                name: {"status": s["status"], "healthScore": s["healthScore"], "restartCount": s["restartCount"]}
                for name, s in SERVICE_STATES.items()
            },
            "timestamp": now,
        }


if __name__ == "__main__":
    SelfHealServer().run()
