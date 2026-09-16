"""MCP error codes (JSON-RPC 2.0 + MCP-specific)."""

from enum import IntEnum
from typing import Optional


class ErrorCode(IntEnum):
    # JSON-RPC standard errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32602
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific
    RESOURCE_NOT_FOUND = -32002
    TOOL_NOT_FOUND = -32003
    PROMPT_NOT_FOUND = -32004
    REQUEST_TIMEOUT = -32005
    CAPABILITY_NOT_SUPPORTED = -32006


class McpError(Exception):
    """Raised by user handlers to signal a structured MCP error."""

    def __init__(self, code: ErrorCode, message: str, data: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}

    def to_jsonrpc(self) -> dict:
        out: dict = {"code": int(self.code), "message": self.message}
        if self.data:
            out["data"] = self.data
        return out