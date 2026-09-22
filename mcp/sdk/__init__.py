"""
b'AI'tcoin MCP SDK — Reusable base classes and utilities for building
Model Context Protocol servers that communicate over JSON-RPC via stdio.
"""

from .base_server import BaseMCPServer, MCPError

__all__ = ["BaseMCPServer", "MCPError"]
