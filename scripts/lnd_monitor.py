#!/usr/bin/env python3
"""Read-only LND health monitor with durable events and optional polling loop."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Protocol


class MonitorError(RuntimeError):
    pass


class MonitorLightningStub(Protocol):
    def GetInfo(self, request: Any, timeout: float | None = None) -> Any: ...


@dataclass(frozen=True)
class LndSnapshot:
    observed_at: float
    reachable: bool
    network: str
    alias: str
    identity_pubkey: str
    block_height: int
    num_active_channels: int
    num_pending_channels: int
    num_inactive_channels: int
    error: str | None = None


class LndMonitor:
    """Perform read-only GetInfo checks; never calls payment or wallet RPCs."""

    def __init__(self, lightning_stub: MonitorLightningStub, message_module: Any, state_db: str | Path, *, now: Callable[[], float] = time.time):
        self.lightning = lightning_stub
        self.message_module = message_module
        self.now = now
        self._lock = threading.RLock()
        self.db = sqlite3.connect(str(state_db), check_same_thread=False, timeout=30.0)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        with self.db:
            self.db.execute("""CREATE TABLE IF NOT EXISTS lnd_monitor_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at REAL NOT NULL,
                reachable INTEGER NOT NULL,
                network TEXT NOT NULL,
                alias TEXT NOT NULL,
                identity_pubkey TEXT NOT NULL,
                block_height INTEGER NOT NULL,
                active_channels INTEGER NOT NULL,
                pending_channels INTEGER NOT NULL,
                inactive_channels INTEGER NOT NULL,
                error TEXT
            )""")

    def close(self) -> None:
        with self._lock:
            self.db.close()

    @staticmethod
    def _field(obj: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            if hasattr(obj, name):
                return getattr(obj, name)
        return default

    def check_once(self) -> LndSnapshot:
        observed_at = self.now()
        try:
            response = self.lightning.GetInfo(self.message_module.GetInfoRequest(), timeout=10)
            chains = self._field(response, "chains", default=[])
            networks = [str(self._field(chain, "network", default="")).lower() for chain in chains]
            network = networks[0] if networks else "unknown"
            snapshot = LndSnapshot(
                observed_at=observed_at,
                reachable=True,
                network=network,
                alias=str(self._field(response, "alias", default="")),
                identity_pubkey=str(self._field(response, "identity_pubkey", default="")),
                block_height=int(self._field(response, "block_height", default=0) or 0),
                num_active_channels=int(self._field(response, "num_active_channels", default=0) or 0),
                num_pending_channels=int(self._field(response, "num_pending_channels", default=0) or 0),
                num_inactive_channels=int(self._field(response, "num_inactive_channels", default=0) or 0),
            )
        except Exception as exc:
            snapshot = LndSnapshot(observed_at, False, "unknown", "", "", 0, 0, 0, 0, type(exc).__name__)
        with self._lock, self.db:
            self.db.execute("INSERT INTO lnd_monitor_events(observed_at,reachable,network,alias,identity_pubkey,block_height,active_channels,pending_channels,inactive_channels,error) VALUES(?,?,?,?,?,?,?,?,?,?)", (snapshot.observed_at, int(snapshot.reachable), snapshot.network, snapshot.alias, snapshot.identity_pubkey, snapshot.block_height, snapshot.num_active_channels, snapshot.num_pending_channels, snapshot.num_inactive_channels, snapshot.error))
        return snapshot

    def run_forever(self, interval_seconds: float, *, stop_event: threading.Event | None = None, emit: Callable[[dict[str, Any]], None] | None = None) -> None:
        if interval_seconds <= 0:
            raise MonitorError("interval_seconds must be positive")
        stop_event = stop_event or threading.Event()
        emit = emit or (lambda event: print(json.dumps(event, sort_keys=True)))
        while not stop_event.is_set():
            emit(asdict(self.check_once()))
            stop_event.wait(interval_seconds)

    def latest(self) -> LndSnapshot | None:
        row = self.db.execute("SELECT observed_at,reachable,network,alias,identity_pubkey,block_height,active_channels,pending_channels,inactive_channels,error FROM lnd_monitor_events ORDER BY event_id DESC LIMIT 1").fetchone()
        if not row:
            return None
        return LndSnapshot(row[0], bool(row[1]), row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9])

    def prometheus_text(self) -> str:
        """Render the latest snapshot using Prometheus text exposition format."""
        snapshot = self.latest()
        if snapshot is None:
            snapshot = LndSnapshot(self.now(), False, "unknown", "", "", 0, 0, 0, 0, "no_observation")
        labels = {"network": snapshot.network}
        label_text = ",".join(f'{key}="{str(value).replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"' for key, value in labels.items())
        lines = [
            "# HELP lnd_monitor_up Whether the latest LND healthcheck succeeded.",
            "# TYPE lnd_monitor_up gauge",
            f"lnd_monitor_up{{{label_text}}} {int(snapshot.reachable)}",
            "# HELP lnd_monitor_observation_timestamp_seconds Unix timestamp of the latest observation.",
            "# TYPE lnd_monitor_observation_timestamp_seconds gauge",
            f"lnd_monitor_observation_timestamp_seconds{{{label_text}}} {snapshot.observed_at}",
            "# HELP lnd_block_height Latest reported Bitcoin block height.",
            "# TYPE lnd_block_height gauge",
            f"lnd_block_height{{{label_text}}} {snapshot.block_height}",
            "# HELP lnd_channels Number of LND channels by state.",
            "# TYPE lnd_channels gauge",
            f'lnd_channels{{{label_text},state="active"}} {snapshot.num_active_channels}',
            f'lnd_channels{{{label_text},state="pending"}} {snapshot.num_pending_channels}',
            f'lnd_channels{{{label_text},state="inactive"}} {snapshot.num_inactive_channels}',
        ]
        if snapshot.error:
            lines.extend([
                "# HELP lnd_monitor_last_error_info Information about the latest monitor error.",
                "# TYPE lnd_monitor_last_error_info gauge",
                f'lnd_monitor_last_error_info{{{label_text},error="{snapshot.error}"}} 1',
            ])
        return "\n".join(lines) + "\n"

    def serve_metrics(self, host: str = "127.0.0.1", port: int = 9899) -> ThreadingHTTPServer:
        """Start a local Prometheus endpoint; caller owns server lifecycle."""
        monitor = self

        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path != "/metrics":
                    self.send_response(404)
                    self.end_headers()
                    return
                payload = monitor.prometheus_text().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):  # noqa: A003
                return

        if not 0 <= int(port) <= 65535:
            raise MonitorError("metrics port must be between 0 and 65535")
        server = ThreadingHTTPServer((host, int(port)), MetricsHandler)
        return server


__all__ = ["LndMonitor", "LndSnapshot", "MonitorError"]
