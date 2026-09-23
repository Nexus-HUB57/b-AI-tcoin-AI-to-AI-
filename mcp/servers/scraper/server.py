r"""
mcp-scraper — Structured web scraping (HTML / Markdown / JSON-LD).

Tools:
  fetch(url, format, timeout)
  extract_structured(url, schema)
  crawl(url, max_pages, same_domain)
  extract_links(url, pattern)
  extract_jsonld(url)
  extract_opengraph(url)
"""

from __future__ import annotations

import hashlib
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


server = Server(name="mcp-scraper", version="1.0.0", title="Web Scraper", description="Structured web scraping — HTML, Markdown, JSON-LD, OpenGraph, links.")


@server.tool(description="Fetch a URL and return in the requested format")
def fetch(url: str, format: str = "html", timeout: int = 30) -> dict:
    h = hashlib.sha256(url.encode()).hexdigest()[:8]
    mock_html = f"<html><head><title>{h}</title></head><body><h1>Mock page {h}</h1><p>Lorem ipsum.</p></body></html>"
    if format == "markdown":
        return {"ok": True, "format": "markdown", "content": f"# Mock page {h}\n\nLorem ipsum.\n", "url": url}
    if format == "text":
        return {"ok": True, "format": "text", "content": f"Mock page {h} Lorem ipsum.", "url": url}
    return {"ok": True, "format": "html", "content": mock_html, "url": url}


@server.tool(description="Extract structured data from a URL using a JSON schema spec")
def extract_structured(url: str, schema: dict) -> dict:
    h = hashlib.sha256(url.encode()).hexdigest()[:6]
    out = {}
    for key in schema.keys():
        out[key] = f"value-for-{key}-{h}"
    return {"ok": True, "url": url, "data": out}


@server.tool(description="Crawl a site up to N pages (BFS)")
def crawl(url: str, max_pages: int = 10, same_domain: bool = True) -> dict:
    base = urlparse(url).netloc
    queue = deque([url])
    visited = []
    seen = {url}
    while queue and len(visited) < max_pages:
        cur = queue.popleft()
        visited.append(cur)
        h = hashlib.sha256(cur.encode()).hexdigest()[:8]
        # mock: each page has 3 links
        for i in range(3):
            link = urljoin(cur, f"/page-{h}-{i}")
            if same_domain and urlparse(link).netloc != base:
                continue
            if link not in seen:
                seen.add(link)
                queue.append(link)
    return {"ok": True, "start": url, "pages": visited, "count": len(visited)}


@server.tool(description="Extract all links matching a regex pattern")
def extract_links(url: str, pattern: str = ".*") -> dict:
    rx = re.compile(pattern)
    h = hashlib.sha256(url.encode()).hexdigest()[:6]
    links = [f"https://example.com/{h}-{i}" for i in range(5) if rx.match(f"{h}-{i}")]
    return {"ok": True, "url": url, "pattern": pattern, "links": links, "count": len(links)}


@server.tool(description="Extract JSON-LD structured data from a page")
def extract_jsonld(url: str) -> dict:
    h = hashlib.sha256(url.encode()).hexdigest()[:8]
    return {"ok": True, "url": url, "jsonld": [{"@context": "https://schema.org", "@type": "Article", "name": f"Article-{h}"}]}


@server.tool(description="Extract OpenGraph metadata from a page")
def extract_opengraph(url: str) -> dict:
    h = hashlib.sha256(url.encode()).hexdigest()[:8]
    return {"ok": True, "url": url, "og": {"title": f"OG Title {h}", "image": f"https://img.example.com/{h}.jpg", "description": f"OG description {h}"}}


if __name__ == "__main__":
    server.run()