"""
MCP type definitions.

Follows the Model Context Protocol specification (2024-11-05).
Reference: https://modelcontextprotocol.io/specification/2024-11-05
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Dict, List, Literal, Optional, Union


# ---------------------------------------------------------------------------
# Content blocks
# ---------------------------------------------------------------------------

@dataclass
class TextContent:
    type: Literal["text"] = "text"
    text: str = ""
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class ImageContent:
    type: Literal["image"] = "image"
    data: str = ""           # base64
    mimeType: str = "image/png"
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddedResource:
    type: Literal["resource"] = "resource"
    resource: Dict[str, Any] = field(default_factory=dict)


Content = Union[TextContent, ImageContent, EmbeddedResource]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str = ""
    inputSchema: Dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class CallToolResult:
    content: List[Content] = field(default_factory=list)
    isError: bool = False
    structuredContent: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Resource definitions
# ---------------------------------------------------------------------------

@dataclass
class Resource:
    uri: str
    name: str
    description: str = ""
    mimeType: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class ReadResourceResult:
    contents: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Prompt definitions
# ---------------------------------------------------------------------------

@dataclass
class PromptArgument:
    name: str
    description: str = ""
    required: bool = False


@dataclass
class Prompt:
    name: str
    description: str = ""
    arguments: List[PromptArgument] = field(default_factory=list)


@dataclass
class GetPromptResult:
    description: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Capabilities & identity
# ---------------------------------------------------------------------------

@dataclass
class ServerCapabilities:
    tools: Dict[str, Any] = field(default_factory=lambda: {"listChanged": False})
    resources: Dict[str, Any] = field(default_factory=lambda: {"subscribe": False, "listChanged": False})
    prompts: Dict[str, Any] = field(default_factory=lambda: {"listChanged": False})
    logging: Dict[str, Any] = field(default_factory=dict)
    sampling: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Implementation:
    name: str
    version: str
    title: Optional[str] = None


# ---------------------------------------------------------------------------
# Handlers (typed aliases for the user's async callables)
# ---------------------------------------------------------------------------

ToolHandler = Callable[..., Awaitable[Union[Dict[str, Any], List[Any], str, CallToolResult]]]
ResourceHandler = Callable[..., Awaitable[Union[str, bytes, ReadResourceResult, Dict[str, Any]]]]
PromptHandler = Callable[..., Awaitable[GetPromptResult]]