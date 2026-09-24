"""
Base MCP Server — JSON-RPC over stdio transport.

Implements the Model Context Protocol specification:
  - Reads JSON-RPC 2.0 requests from stdin (one per line)
  - Dispatches to registered handler methods
  - Writes JSON-RPC 2.0 responses to stdout
  - Logs to stderr only (stdout is reserved for the protocol channel)

Usage:
    class MyServer(BaseMCPServer):
        def __init__(self):
            super().__init__("my-server", "1.0.0")

        def _register_tools(self):
            self._register_tool("my_tool", "Does something", self._handle_my_tool)

        def _handle_my_tool(self, arguments: dict) -> dict:
            return {"result": "hello"}

    MyServer().run()
"""

from __future__ import annotations

import json
import sys
import traceback
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# MCP Error Codes (JSON-RPC 2.0 + MCP-specific)
# ---------------------------------------------------------------------------

class MCPErrorCode(IntEnum):
    """Standard JSON-RPC 2.0 error codes plus MCP extensions."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # MCP-specific
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    RESOURCE_NOT_FOUND = -32003
    CAPABILITY_NOT_SUPPORTED = -32004
    RATE_LIMITED = -32005
    QUOTA_EXCEEDED = -32006


# ---------------------------------------------------------------------------
# MCP Error Exception
# ---------------------------------------------------------------------------

class MCPError(Exception):
    """Raised inside tool/resource handlers to return a structured MCP error."""

    def __init__(
        self,
        code: MCPErrorCode | int,
        message: str,
        data: Any | None = None,
    ):
        self.code = int(code)
        self.message = message
        self.data = data
        super().__init__(message)

    def to_dict(self) -> dict:
        d: dict = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d


# ---------------------------------------------------------------------------
# Tool / Resource descriptors
# ---------------------------------------------------------------------------

@dataclass
class ToolDescriptor:
    """Describes a tool exposed by this MCP server."""

    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    category: str = "general"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class ResourceDescriptor:
    """Describes a resource exposed by this MCP server."""

    uri: str
    name: str
    description: str
    mime_type: str = "application/json"

    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


# ---------------------------------------------------------------------------
# BaseMCPServer
# ---------------------------------------------------------------------------

class BaseMCPServer:
    """
    Base class for all b'AI'tcoin MCP servers.

    Subclasses should:
      1. Call super().__init__(name, version) with their identity
      2. Override _register_tools() and optionally _register_resources()
      3. Call self._register_tool(name, desc, handler) for each tool
      4. Call self._register_resource(uri, name, desc, handler) for each resource
      5. Call .run() to start the stdio JSON-RPC loop
    """

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(
        self,
        name: str,
        version: str,
        description: str = "",
        capabilities: dict | None = None,
    ):
        self.name = name
        self.version = version
        self.description = description

        # Default capabilities — subclasses can override
        self.capabilities = capabilities or {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
            "logging": {},
        }

        # Internal registries
        self._tools: dict[str, ToolDescriptor] = {}
        self._tool_handlers: dict[str, Callable[[dict], Any]] = {}
        self._resources: dict[str, ResourceDescriptor] = {}
        self._resource_handlers: dict[str, Callable[[dict], Any]] = {}

        # Server state
        self._initialized = False

        # Register tools/resources
        self._register_tools()
        self._register_resources()

    # ------------------------------------------------------------------
    # Registration helpers (called by subclasses)
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Override in subclass to register tools."""
        pass

    def _register_resources(self) -> None:
        """Override in subclass to register resources."""
        pass

    def _register_tool(
        self,
        name: str,
        description: str,
        handler: Callable[[dict], Any],
        input_schema: dict | None = None,
        category: str = "general",
    ) -> None:
        """Register a tool with its handler."""
        if name in self._tools:
            self._log("warning", f"Tool '{name}' re-registered; replacing handler")
        self._tools[name] = ToolDescriptor(
            name=name,
            description=description,
            input_schema=input_schema or {"type": "object", "properties": {}, "required": []},
            category=category,
        )
        self._tool_handlers[name] = handler

    def _register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        handler: Callable[[dict], Any],
        mime_type: str = "application/json",
    ) -> None:
        """Register a resource with its handler."""
        if uri in self._resources:
            self._log("warning", f"Resource '{uri}' re-registered; replacing handler")
        self._resources[uri] = ResourceDescriptor(
            uri=uri, name=name, description=description, mime_type=mime_type,
        )
        self._resource_handlers[uri] = handler

    # ------------------------------------------------------------------
    # Logging (stderr only — stdout is the protocol channel)
    # ------------------------------------------------------------------

    def _log(self, level: str, message: str) -> None:
        """Write a structured log line to stderr."""
        entry = {
            "jsonrpc": "2.0",
            "method": "notifications/message",
            "params": {
                "level": level,
                "logger": self.name,
                "data": message,
            },
        }
        try:
            sys.stderr.write(json.dumps(entry) + "\n")
            sys.stderr.flush()
        except Exception:
            pass  # Never let logging break the server

    # ------------------------------------------------------------------
    # JSON-RPC I/O
    # ------------------------------------------------------------------

    def _read_request(self) -> Optional[dict]:
        """Read one JSON-RPC request from stdin. Returns None on EOF."""
        try:
            line = sys.stdin.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                return None
            return json.loads(line)
        except json.JSONDecodeError as exc:
            self._log("error", f"JSON parse error: {exc}")
            self._write_error(None, MCPErrorCode.PARSE_ERROR, f"Parse error: {exc}")
            return None
        except Exception as exc:
            self._log("error", f"Stdin read error: {exc}")
            return None

    def _write_response(self, id: Any, result: Any) -> None:
        """Write a successful JSON-RPC response to stdout."""
        response = {"jsonrpc": "2.0", "id": id, "result": result}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    def _write_error(self, id: Any, code: MCPErrorCode | int, message: str, data: Any = None) -> None:
        """Write a JSON-RPC error response to stdout."""
        error: dict = {"code": int(code), "message": message}
        if data is not None:
            error["data"] = data
        response = {"jsonrpc": "2.0", "id": id, "error": error}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Method dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, request: dict) -> None:
        """Route a JSON-RPC request to the appropriate handler."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        self._log("debug", f"Dispatching method={method} id={req_id}")

        # Notifications (no id → no response expected)
        if req_id is None:
            self._log("debug", f"Notification received: {method}")
            return

        try:
            handler = getattr(self, f"_handle_{method.replace('/', '_')}", None)
            if handler is None:
                self._write_error(
                    req_id, MCPErrorCode.METHOD_NOT_FOUND,
                    f"Method not found: {method}",
                )
                return
            result = handler(params)
            self._write_response(req_id, result)
        except MCPError as exc:
            self._write_error(req_id, exc.code, exc.message, exc.data)
        except Exception as exc:
            self._log("error", f"Unhandled exception in {method}: {traceback.format_exc()}")
            self._write_error(
                req_id, MCPErrorCode.INTERNAL_ERROR,
                f"Internal error: {exc}",
            )

    # ------------------------------------------------------------------
    # Core MCP method handlers
    # ------------------------------------------------------------------

    def _handle_initialize(self, params: dict) -> dict:
        """Handle the 'initialize' method."""
        self._initialized = True
        self._log("info", "Client initialized")
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": self.name,
                "version": self.version,
                "description": self.description,
            },
        }

    def _handle_tools_list(self, params: dict) -> dict:
        """Handle the 'tools/list' method."""
        return {
            "tools": [t.to_dict() for t in self._tools.values()],
        }

    def _handle_tools_call(self, params: dict) -> dict:
        """Handle the 'tools/call' method."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            raise MCPError(
                MCPErrorCode.TOOL_NOT_FOUND,
                f"Tool not found: {tool_name}",
                {"availableTools": list(self._tools.keys())},
            )

        handler = self._tool_handlers[tool_name]

        try:
            result = handler(arguments)
            # If the handler already returns MCP content-type format, pass through
            if isinstance(result, dict) and "content" in result:
                return result
            # Otherwise wrap in the standard MCP tool-result envelope
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, default=str),
                    }
                ],
            }
        except MCPError:
            raise
        except Exception as exc:
            self._log("error", f"Tool '{tool_name}' execution error: {traceback.format_exc()}")
            raise MCPError(
                MCPErrorCode.TOOL_EXECUTION_ERROR,
                f"Tool execution error: {exc}",
                {"tool": tool_name},
            )

    def _handle_resources_list(self, params: dict) -> dict:
        """Handle the 'resources/list' method."""
        return {
            "resources": [r.to_dict() for r in self._resources.values()],
        }

    def _handle_resources_read(self, params: dict) -> dict:
        """Handle the 'resources/read' method."""
        uri = params.get("uri", "")
        if uri not in self._resources:
            raise MCPError(
                MCPErrorCode.RESOURCE_NOT_FOUND,
                f"Resource not found: {uri}",
                {"availableResources": list(self._resources.keys())},
            )
        handler = self._resource_handlers[uri]
        try:
            result = handler(params)
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": self._resources[uri].mime_type,
                        "text": json.dumps(result, default=str),
                    }
                ],
            }
        except Exception as exc:
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Resource read error: {exc}",
            )

    def _handle_ping(self, params: dict) -> dict:
        """Handle the 'ping' method."""
        return {}

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Start the MCP server: read JSON-RPC from stdin, dispatch, respond.

        Runs until stdin is closed (EOF) or an unrecoverable error occurs.
        """
        self._log("info", f"MCP server '{self.name}' v{self.version} starting")

        while True:
            try:
                request = self._read_request()
                if request is None:
                    # EOF — client closed stdin
                    self._log("info", "Stdin closed; shutting down")
                    break

                # Validate JSON-RPC envelope
                if request.get("jsonrpc") != "2.0":
                    self._write_error(
                        request.get("id"),
                        MCPErrorCode.INVALID_REQUEST,
                        "Invalid JSON-RPC version; expected '2.0'",
                    )
                    continue

                if "method" not in request:
                    self._write_error(
                        request.get("id"),
                        MCPErrorCode.INVALID_REQUEST,
                        "Missing 'method' field in request",
                    )
                    continue

                self._dispatch(request)

            except KeyboardInterrupt:
                self._log("info", "Interrupted; shutting down")
                break
            except Exception as exc:
                self._log("error", f"Fatal error in main loop: {traceback.format_exc()}")
                break

        self._log("info", f"MCP server '{self.name}' stopped")
