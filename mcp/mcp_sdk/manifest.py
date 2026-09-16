"""
.aipkg manifest builder.

Produces the canonical manifest.json that ships inside every MCP .aipkg.
The schema lives at /docs/aipkg-mcp.schema.json.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Manifest:
    aipkg: str = "1.0"
    kind: str = "mcp"
    name: str = ""
    version: str = "1.0.0"
    displayName: str = ""
    description: str = ""
    author: Dict[str, Any] = field(default_factory=lambda: {"agentId": "@nexus-genesis", "displayName": "Nexus Genesis", "verified": True})
    category: str = "agentic-awareness"
    tags: List[str] = field(default_factory=list)
    iconEmoji: str = ""
    license: str = "MIT"
    repository: str = ""
    homepage: str = ""
    mcp: Dict[str, Any] = field(default_factory=lambda: {
        "transport": "stdio",
        "command": "python -m servers.<name>.server",
        "args": [],
        "env": {},
        "capabilities": {"tools": True, "resources": True, "prompts": False, "logging": True, "sampling": False},
        "minProtocolVersion": "2024-11-05",
    })
    runtime: Dict[str, Any] = field(default_factory=lambda: {"memoryMb": 256, "cpuMillicores": 500, "timeoutMs": 30000, "sandbox": "process"})
    tools: List[Dict[str, Any]] = field(default_factory=list)
    pricing: Dict[str, Any] = field(default_factory=lambda: {"model": "free", "priceSats": 0, "pricePerCallSats": 0})
    telemetry: Dict[str, Any] = field(default_factory=lambda: {"emitTo": "pulsar", "includeCallPayload": False, "sampleRate": 1.0})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def write(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return p

    def sha256(self) -> str:
        import hashlib
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def build_manifest(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    category: str = "agentic-awareness",
    tools: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> Manifest:
    m = Manifest(
        name=name,
        version=version,
        displayName=kwargs.pop("displayName", name),
        description=description,
        category=category,
        **kwargs,
    )
    m.tools = tools or []
    # auto-derive command if not overridden
    if m.mcp.get("command", "").endswith("<name>.server"):
        m.mcp["command"] = f"python -m servers.{name}.server"
    return m