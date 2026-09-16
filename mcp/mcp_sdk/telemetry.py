"""
MCP Telemetry — feeds usage events into the autoevolution pipeline.

Every tools/call emits an event. Events are batched and flushed to:

  1. A local JSONL file (default: ./logs/mcp-telemetry.jsonl)
  2. The Pulsar SSE feed (if PULSAR_URL is set)
  3. The RAG upgrader inbox (if RAG_INBOX is set)

This module is intentionally framework-free so the SDK stays light.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional


class TelemetryRecorder:
    """Async-safe event sink with batching and multi-target flush."""

    def __init__(
        self,
        mcp_name: str,
        log_path: Optional[str] = None,
        pulsar_url: Optional[str] = None,
        rag_inbox: Optional[str] = None,
        batch_size: int = 50,
        flush_interval_s: float = 5.0,
        sample_rate: float = 1.0,
    ):
        self.mcp_name = mcp_name
        self.log_path = Path(log_path or os.environ.get("MCP_TELEMETRY_LOG", "./logs/mcp-telemetry.jsonl"))
        self.pulsar_url = pulsar_url or os.environ.get("PULSAR_URL")
        self.rag_inbox = rag_inbox or os.environ.get("RAG_INBOX")
        self.batch_size = batch_size
        self.flush_interval_s = flush_interval_s
        self.sample_rate = max(0.0, min(1.0, sample_rate))

        self._queue: Deque[Dict[str, Any]] = deque(maxlen=10_000)
        self._lock = asyncio.Lock()

    async def __call__(self, event: Dict[str, Any]) -> None:
        if self.sample_rate < 1.0:
            import random
            if random.random() > self.sample_rate:
                return
        event.setdefault("mcp", self.mcp_name)
        event.setdefault("ts", time.time())
        async with self._lock:
            self._queue.append(event)
            if len(self._queue) >= self.batch_size:
                await self._flush_unlocked()

    async def flush(self) -> None:
        async with self._lock:
            await self._flush_unlocked()

    async def _flush_unlocked(self) -> None:
        if not self._queue:
            return
        events = list(self._queue)
        self._queue.clear()

        # local file (always)
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                for e in events:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # pulsar SSE
        if self.pulsar_url:
            try:
                import urllib.request
                req = urllib.request.Request(
                    self.pulsar_url.rstrip("/") + "/ingest",
                    data=json.dumps({"events": events}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                await asyncio.to_thread(urllib.request.urlopen, req, timeout=2)
            except Exception:
                pass

        # RAG inbox
        if self.rag_inbox:
            try:
                with open(self.rag_inbox, "a", encoding="utf-8") as f:
                    for e in events:
                        f.write(json.dumps(e, ensure_ascii=False) + "\n")
            except Exception:
                pass


# Synchronous convenience sink — drop-in for simple servers
def sync_sink(path: str) -> Any:
    """Returns an async sink that appends JSONL to `path`."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    async def _sink(event: Dict[str, Any]) -> None:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return _sink