"""
MCP Server — asyncio + JSON-RPC 2.0 over stdio.

This is the reference server implementation for the b'AI'tcoin MCP ecosystem.
It implements the full MCP spec surface that a host agent needs:

  initialize / notifications/initialized
  tools/list, tools/call
  resources/list, resources/read, resources/templates/list
  prompts/list, prompts/get
  logging/setLevel, notifications/message
  ping
  completion/complete
  sampling/createMessage (server → host)
  elicitation/create (server → host)
  notifications/tools/list_changed, notifications/resources/list_changed

The framing follows the LSP-style Content-Length header (MCP 2024-11-05).
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .types import (
    CallToolResult,
    Content,
    EmbeddedResource,
    GetPromptResult,
    ImageContent,
    Implementation,
    Prompt,
    ReadResourceResult,
    Resource,
    ServerCapabilities,
    TextContent,
    Tool,
)
from .errors import ErrorCode, McpError

log = logging.getLogger("mcp.server")


PROTOCOL_VERSION = "2024-11-05"


def _json_default(o: Any) -> Any:
    if is_dataclass(o):
        return asdict(o)
    if isinstance(o, Content):
        return asdict(o)
    if isinstance(o, (TextContent, ImageContent, EmbeddedResource)):
        return asdict(o)
    if isinstance(o, bytes):
        return {"__bytes_b64__": __import__("base64").b64encode(o).decode("ascii")}
    if isinstance(o, Exception):
        return {"__exc__": f"{type(o).__name__}: {o}"}
    raise TypeError(f"not JSON serializable: {type(o)}")


def _content_from_value(v: Any) -> List[Content]:
    """Normalize a tool handler's return into a list of Content blocks."""
    if v is None:
        return [TextContent(text="null")]
    if isinstance(v, Content):
        return [v]
    if isinstance(v, list):
        return [TextContent(text=json.dumps(v, default=_json_default, ensure_ascii=False))]
    if isinstance(v, CallToolResult):
        return v.content
    if isinstance(v, dict):
        return [TextContent(text=json.dumps(v, default=_json_default, ensure_ascii=False))]
    return [TextContent(text=str(v))]


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class Server:
    """An MCP server. Register tools/resources/prompts and call `.run()`."""

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        title: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        capabilities: Optional[ServerCapabilities] = None,
    ):
        self.description = description
        # Some MCP clients surface serverInfo.description — encode it into the
        # title when no explicit title was provided so the info stays useful.
        effective_title = title or (description[:48] + "..." if description and len(description) > 48 else description)
        self.implementation = Implementation(name=name, version=version, title=effective_title)
        self.instructions = instructions or description
        self.capabilities = capabilities or ServerCapabilities(
            tools={"listChanged": True},
            resources={"subscribe": False, "listChanged": False},
            prompts={"listChanged": False},
            logging={},
        )

        # Handler registries
        self._tools: Dict[str, Dict[str, Any]] = {}        # name -> {tool, handler}
        self._resources: Dict[str, Dict[str, Any]] = {}    # uri -> {resource, handler}
        self._resource_templates: Dict[str, Dict[str, Any]] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}

        # Runtime state
        self._initialized = False
        self._client_info: Optional[Dict[str, Any]] = None
        self._log_level = "info"
        self._telemetry_sink: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self._sampling_handler: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None
        self._elicitation_handler: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None

    # ------------------------------------------------------------------ API
    def tool(
        self,
        name: Optional[str] = None,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ):
        """Decorator to register a tool."""
        def deco(fn):
            tool_name = name or fn.__name__
            schema = input_schema or _infer_schema(fn)
            self._tools[tool_name] = {
                "tool": Tool(
                    name=tool_name,
                    description=description or (fn.__doc__ or "").strip(),
                    inputSchema=schema,
                ),
                "handler": fn,
            }
            return fn
        return deco

    def resource(self, uri: str, name: str = "", description: str = "", mime_type: Optional[str] = None):
        def deco(fn):
            self._resources[uri] = {
                "resource": Resource(uri=uri, name=name or fn.__name__, description=description or (fn.__doc__ or "").strip(), mimeType=mime_type),
                "handler": fn,
            }
            return fn
        return deco

    def prompt(self, name: Optional[str] = None, description: str = ""):
        def deco(fn):
            pname = name or fn.__name__
            self._prompts[pname] = {
                "prompt": Prompt(name=pname, description=description or (fn.__doc__ or "").strip()),
                "handler": fn,
            }
            return fn
        return deco

    def telemetry(self, sink: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Attach a telemetry sink. Called for every tools/call."""
        self._telemetry_sink = sink

    def on_sampling(self, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        self._sampling_handler = handler

    def on_elicitation(self, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        self._elicitation_handler = handler

    # ------------------------------------------------------------- Runners
    def run(self, transport: str = "stdio") -> None:
        if transport == "stdio":
            asyncio.run(self._run_stdio())
        else:
            raise NotImplementedError(f"transport {transport} not yet implemented")

    async def _run_stdio(self) -> None:
        log.info("starting MCP server %s v%s", self.implementation.name, self.implementation.version)
        loop = asyncio.get_running_loop()
        # stdin reader
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, loop)

        # set stdin to non-blocking-ish — already a pipe
        try:
            await self._serve(reader, writer)
        finally:
            writer.close()

    # ------------------------------------------------------ Internal serve
    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Read framed JSON-RPC messages and dispatch them."""
        while True:
            try:
                msg = await self._read_message(reader)
            except asyncio.IncompleteReadError:
                log.info("stdin closed — exiting")
                return
            except Exception as e:
                log.exception("read error: %s", e)
                return
            if msg is None:
                continue
            asyncio.create_task(self._dispatch(msg, writer))

    async def _read_message(self, reader: asyncio.StreamReader) -> Optional[Dict[str, Any]]:
        # LSP-style Content-Length framing
        headers: Dict[str, str] = {}
        while True:
            line = await reader.readline()
            if not line:
                raise asyncio.IncompleteReadError(b"", 0)
            line = line.rstrip(b"\r\n")
            if not line:
                break
            k, _, v = line.partition(b":")
            headers[k.decode("ascii").strip().lower()] = v.decode("ascii").strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        body = await reader.readexactly(length)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            await self._send(writer=None, error={
                "jsonrpc": "2.0", "id": None,
                "error": {"code": int(ErrorCode.PARSE_ERROR), "message": str(e)}
            }) if False else None
            return None

    async def _send(self, writer: Optional[asyncio.StreamWriter], message: Dict[str, Any]) -> None:
        if writer is None:
            return
        body = json.dumps(message, default=_json_default, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        writer.write(header + body)
        await writer.drain()

    async def _dispatch(self, msg: Dict[str, Any], writer: asyncio.StreamWriter) -> None:
        method = msg.get("method")
        params = msg.get("params") or {}
        msg_id = msg.get("id")
        is_notification = msg_id is None

        log.debug("<- %s id=%s", method, msg_id)

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "notifications/initialized":
                self._initialized = True
                return
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = await self._handle_tools_list(params)
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            elif method == "resources/list":
                result = await self._handle_resources_list(params)
            elif method == "resources/read":
                result = await self._handle_resources_read(params)
            elif method == "resources/templates/list":
                result = await self._handle_resource_templates_list(params)
            elif method == "prompts/list":
                result = await self._handle_prompts_list(params)
            elif method == "prompts/get":
                result = await self._handle_prompts_get(params)
            elif method == "logging/setLevel":
                self._log_level = params.get("level", "info")
                result = {}
            elif method == "completion/complete":
                result = {"completion": {"values": [], "total": 0, "hasMore": False}}
            elif method == "sampling/createMessage":
                result = await self._sampling_handler(params) if self._sampling_handler else {}
            elif method == "elicitation/create":
                result = await self._elicitation_handler(params) if self._elicitation_handler else {}
            else:
                if not is_notification:
                    await self._send(writer, {"jsonrpc": "2.0", "id": msg_id, "error": {"code": int(ErrorCode.METHOD_NOT_FOUND), "message": f"unknown method: {method}"}})
                return

            if is_notification:
                return

            response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
            await self._send(writer, response)

        except McpError as e:
            if not is_notification:
                await self._send(writer, {"jsonrpc": "2.0", "id": msg_id, "error": e.to_jsonrpc()})
        except Exception as e:
            log.exception("handler error for %s", method)
            if not is_notification:
                await self._send(writer, {"jsonrpc": "2.0", "id": msg_id, "error": {"code": int(ErrorCode.INTERNAL_ERROR), "message": f"{type(e).__name__}: {e}"}})

    # ----------------------------------------------------- Method handlers
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self._client_info = params.get("clientInfo") or {}
        proto = params.get("protocolVersion") or PROTOCOL_VERSION
        return {
            "protocolVersion": proto,
            "capabilities": asdict(self.capabilities),
            "serverInfo": asdict(self.implementation),
            "instructions": self.instructions,
        }

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"tools": [asdict(t["tool"]) for t in self._tools.values()]}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in self._tools:
            raise McpError(ErrorCode.TOOL_NOT_FOUND, f"tool not found: {name}")

        entry = self._tools[name]
        handler = entry["handler"]
        tool_def = entry["tool"]

        start = time.time()
        error_msg: Optional[str] = None
        is_error = False
        try:
            if inspect.iscoroutinefunction(handler):
                out = await handler(**arguments)
            else:
                out = handler(**arguments)
            contents = _content_from_value(out)
            result: Dict[str, Any] = {"content": [asdict(c) if is_dataclass(c) else c for c in contents]}
            if isinstance(out, CallToolResult):
                if out.structuredContent:
                    result["structuredContent"] = out.structuredContent
                is_error = out.isError
        except McpError as e:
            raise
        except Exception as e:
            is_error = True
            error_msg = f"{type(e).__name__}: {e}"
            result = {"content": [{"type": "text", "text": error_msg}], "isError": True}

        result["isError"] = is_error

        # Telemetry
        if self._telemetry_sink:
            try:
                await self._telemetry_sink({
                    "event": "tools/call",
                    "mcp": self.implementation.name,
                    "tool": name,
                    "duration_ms": int((time.time() - start) * 1000),
                    "ok": not is_error,
                    "error": error_msg,
                    "ts": time.time(),
                    "client": self._client_info,
                })
            except Exception:
                pass

        return result

    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"resources": [asdict(r["resource"]) for r in self._resources.values()]}

    async def _handle_resource_templates_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"resourceTemplates": list(self._resource_templates.values())}

    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("uri")
        if uri not in self._resources:
            raise McpError(ErrorCode.RESOURCE_NOT_FOUND, f"resource not found: {uri}")
        handler = self._resources[uri]["handler"]
        out = handler(uri) if not inspect.iscoroutinefunction(handler) else await handler(uri)
        if isinstance(out, ReadResourceResult):
            return {"contents": out.contents}
        if isinstance(out, bytes):
            return {"contents": [{"uri": uri, "blob": __import__("base64").b64encode(out).decode("ascii")}]}
        if isinstance(out, str):
            return {"contents": [{"uri": uri, "text": out}]}
        return {"contents": [{"uri": uri, "text": json.dumps(out, default=_json_default)}]}

    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"prompts": [asdict(p["prompt"]) for p in self._prompts.values()]}

    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if name not in self._prompts:
            raise McpError(ErrorCode.PROMPT_NOT_FOUND, f"prompt not found: {name}")
        handler = self._prompts[name]["handler"]
        out = handler(**(params.get("arguments") or {}))
        if inspect.iscoroutinefunction(handler):
            out = await out
        if isinstance(out, GetPromptResult):
            return {"description": out.description, "messages": out.messages}
        return out


# ---------------------------------------------------------------------------
# Schema inference
# ---------------------------------------------------------------------------

def _infer_schema(fn: Callable) -> Dict[str, Any]:
    """Best-effort JSON schema from a function signature.

    Each parameter becomes a property. Defaults determine `default`.
    Annotations determine `type` when possible. We keep it simple on purpose —
    callers can always pass `input_schema=...` explicitly for richer schemas.
    """
    sig = inspect.signature(fn)
    props: Dict[str, Any] = {}
    required: List[str] = []
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        ann = param.annotation if param.annotation is not inspect.Parameter.empty else str
        t = _ann_to_json_type(ann)
        prop: Dict[str, Any] = {"type": t}
        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(pname)
        props[pname] = prop
    schema: Dict[str, Any] = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def _ann_to_json_type(ann: Any) -> str:
    if ann in (int,):
        return "integer"
    if ann in (float,):
        return "number"
    if ann in (bool,):
        return "boolean"
    if ann in (str,):
        return "string"
    if ann in (list, List):
        return "array"
    if ann in (dict, Dict):
        return "object"
    name = getattr(ann, "__name__", str(ann))
    return {"int": "integer", "float": "number", "bool": "boolean",
            "str": "string", "list": "array", "dict": "object"}.get(name, "string")