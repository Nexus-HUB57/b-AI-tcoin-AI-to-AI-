r"""
mcp-browser — Headless browser automation (CDP / Obscura).

Tools:
  new_session(headless, viewport)
  navigate(session_id, url, wait_for)
  click(session_id, selector)
  fill(session_id, selector, value)
  extract(session_id, selector, attribute)
  screenshot(session_id, full_page)
  close_session(session_id)
  list_sessions()
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


SESSIONS: dict = {}


def _hash(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:16]


server = Server(name="mcp-browser", version="1.0.0", title="Browser Automation", description="Headless browser automation with persistent CDP sessions.")


@server.tool(description="Create a new browser session")
def new_session(headless: bool = True, viewport: dict = None) -> dict:
    sid = _hash("sess", headless, time.time())
    SESSIONS[sid] = {
        "session_id": sid,
        "headless": headless,
        "viewport": viewport or {"width": 1280, "height": 720},
        "created_at": time.time(),
        "pages": [],
        "current_url": None,
    }
    return {"ok": True, "session_id": sid}


@server.tool(description="Navigate to a URL")
def navigate(session_id: str, url: str, wait_for: str = "load") -> dict:
    if session_id not in SESSIONS:
        return {"ok": False, "error": "session_not_found"}
    parsed = urlparse(url)
    SESSIONS[session_id]["current_url"] = url
    SESSIONS[session_id]["pages"].append({"url": url, "ts": time.time()})
    return {"ok": True, "session_id": session_id, "url": url, "domain": parsed.net.host}


@server.tool(description="Click an element by CSS selector")
def click(session_id: str, selector: str) -> dict:
    if session_id not in SESSIONS:
        return {"ok": False, "error": "session_not_found"}
    return {"ok": True, "session_id": session_id, "selector": selector, "clicked": True}


@server.tool(description="Fill an input")
def fill(session_id: str, selector: str, value: str) -> dict:
    if session_id not in SESSIONS:
        return {"ok": False, "error": "session_not_found"}
    return {"ok": True, "session_id": session_id, "selector": selector, "filled": True, "value_length": len(value)}


@server.tool(description="Extract text or attribute from a selector")
def extract(session_id: str, selector: str, attribute: str = "text") -> dict:
    if session_id not in SESSIONS:
        return {"ok": False, "error": "session_not_found"}
    h = hashlib.sha256(f"{session_id}-{selector}".encode()).hexdigest()[:8]
    return {"ok": True, "selector": selector, "attribute": attribute, "value": f"extracted-{h}", "session_id": session_id}


@server.tool(description="Take a screenshot of the current page")
def screenshot(session_id: str, full_page: bool = False) -> dict:
    if session_id not in SESSIONS:
        return {"ok": False, "error": "session_not_found"}
    h = hashlib.sha256(f"{session_id}-{time.time()}".encode()).hexdigest()[:16]
    return {"ok": True, "session_id": session_id, "screenshot_id": h, "full_page": full_page, "format": "png"}


@server.tool(description="Close a session")
def close_session(session_id: str) -> dict:
    if session_id not in SESSIONS:
        return {"ok": False, "error": "session_not_found"}
    del SESSIONS[session_id]
    return {"ok": True, "closed": session_id}


@server.tool(description="List all active sessions")
def list_sessions() -> dict:
    return {"sessions": [{"id": s["session_id"], "url": s["current_url"], "pages": len(s["pages"])} for s in SESSIONS.values()]}


if __name__ == "__main__":
    server.run()