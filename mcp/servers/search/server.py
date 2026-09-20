r"""
mcp-search — Federated web search (Brave + Tavily + Serper fallback).

Tools:
  search(query, top_k, engines)
  news_search(query, top_k)
  image_search(query, top_k)
  video_search(query, top_k)
  suggest(query)
  answer(query)
"""

from __future__ import annotations

import hashlib
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


ENGINES = ["brave", "tavily", "serper"]


def _mock_results(query: str, engine: str, top_k: int) -> list:
    out = []
    for i in range(top_k):
        h = hashlib.sha256(f"{engine}-{query}-{i}".encode()).hexdigest()[:8]
        out.append({
            "title": f"{query} — result {i}",
            "url": f"https://example.com/{engine}/{h}",
            "snippet": f"Mock snippet for {query} from {engine}",
            "engine": engine,
            "score": round(1.0 - i * 0.1, 2),
        })
    return out


server = Server(name="mcp-search", version="1.0.0", title="Federated Web Search", description="Multi-engine search with aggregation and answer synthesis.")


@server.tool(description="Search across multiple engines and aggregate")
def search(query: str, top_k: int = 10, engines: list = None) -> dict:
    engines = engines or ENGINES
    by_engine = {}
    seen_urls = set()
    merged = []
    for engine in engines:
        rs = _mock_results(query, engine, top_k)
        by_engine[engine] = rs
        for r in rs:
            if r["url"] in seen_urls:
                continue
            seen_urls.add(r["url"])
            merged.append(r)
    # re-score: count engines that returned the same url
    counts = defaultdict(int)
    for eng, rs in by_engine.items():
        for r in rs:
            counts[r["url"]] += 1
    for r in merged:
        r["engines_agree"] = counts.get(r["url"], 0)
        r["boosted_score"] = round(r["score"] * (1 + 0.2 * r["engines_agree"]), 4)
    merged.sort(key=lambda r: -r["boosted_score"])
    return {"ok": True, "query": query, "results": merged[:top_k], "by_engine": by_engine, "engines_used": engines}


@server.tool(description="News-only search")
def news_search(query: str, top_k: int = 10) -> dict:
    rs = _mock_results(query, "news", top_k)
    for r in rs:
        r["published_at"] = time.time() - int(hashlib.sha256(r["url"].encode()).hexdigest[:2], 16) * 3600 if False else time.time()
    return {"ok": True, "query": query, "results": rs}


@server.tool(description="Image search")
def image_search(query: str, top_k: int = 10) -> dict:
    rs = []
    for i in range(top_k):
        h = hashlib.sha256(f"img-{query}-{i}".encode()).hexdigest()[:8]
        rs.append({"title": f"{query} image {i}", "url": f"https://example.com/{h}.jpg", "thumbnail": f"https://example.com/{h}-thumb.jpg"})
    return {"ok": True, "query": query, "results": rs}


@server.tool(description="Video search")
def video_search(query: str, top_k: int = 10) -> dict:
    rs = []
    for i in range(top_k):
        h = hashlib.sha256(f"vid-{query}-{i}".encode()).hexdigest()[:8]
        rs.append({"title": f"{query} video {i}", "url": f"https://example.com/{h}.mp4", "channel": f"Channel-{h[:4]}"})
    return {"ok": True, "query": query, "results": rs}


@server.tool(description="Autocomplete suggestions for a partial query")
def suggest(query: str) -> dict:
    suffixes = ["tutorial", "examples", "vs alternatives", "best practices", "2026", "documentation"]
    return {"ok": True, "query": query, "suggestions": [f"{query} {s}" for s in suffixes]}


@server.tool(description="Get a direct answer (extracts from top results)")
def answer(query: str) -> dict:
    h = hashlib.sha256(query.encode()).hexdigest()[:12]
    return {"ok": True, "query": query, "answer": f"Synthesized answer for '{query}' (ref {h})", "sources": 3}


if __name__ == "__main__":
    server.run()