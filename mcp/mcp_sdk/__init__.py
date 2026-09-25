"""
b'AI'tcoin MCP SDK (Python)
============================

Reference implementation of the Model Context Protocol (MCP) for the
b'AI'tcoin / Nexus AI-OS ecosystem. Implements:

  * JSON-RPC 2.0 over stdio (with Content-Length framing)
  * Server-side: tools, resources, prompts
  * Sampling / elicitation requests to the host agent
  * Structured logging notifications
  * Self-evolution hooks (telemetry → RAG → skill upgrade)

The SDK follows the MCP specification (2024-11-05). Any host that
implements the same spec (Claude Desktop, Cursor, custom agent boxes)
can connect to servers built with this SDK.

Usage:

    from mcp_sdk import Server, tool, resource, prompt

    server = Server(name="mcp-oracle", version="1.0.0")

    @server.tool(name="get_price", description="Latest price for a symbol")
    async def get_price(symbol: str) -> dict:
        return {"symbol": symbol, "price": 0.42}

    if __name__ == "__main__":
        server.run()
"""

from .types import (
    Tool,
    Resource,
    Prompt,
    TextContent,
    ImageContent,
    EmbeddedResource,
    CallToolResult,
    ReadResourceResult,
    GetPromptResult,
    ServerCapabilities,
    Implementation,
)
from .server import Server
from .errors import McpError, ErrorCode
from .manifest import Manifest, build_manifest
from .telemetry import TelemetryRecorder

__version__ = "1.0.0"
__all__ = [
    "Server",
    "Tool",
    "Resource",
    "Prompt",
    "TextContent",
    "ImageContent",
    "EmbeddedResource",
    "CallToolResult",
    "ReadResourceResult",
    "GetPromptResult",
    "ServerCapabilities",
    "Implementation",
    "McpError",
    "ErrorCode",
    "Manifest",
    "build_manifest",
    "TelemetryRecorder",
    "__version__",
]