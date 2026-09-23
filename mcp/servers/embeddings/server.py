r"""
mcp-embeddings — Vector embeddings + semantic search (Qdrant/Pinecone/local).

Tools:
  embed(texts)                       — list of texts → list of float vectors
  embed_query(text)
  upsert(collection, id, vector, payload)
  search(collection, vector, top_k)
  delete(collection, id)
  collection_stats()
  hybrid_search(collection, query, alpha)
"""

from __future__ import annotations

import hashlib
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server

DIM = 384  # mock embedding dim

COLLECTIONS: dict = defaultdict(lambda: {"vectors": {}, "payloads": {}})


def _hash_vec(text: str) -> list:
    """Deterministic mock embedding (replace with real model in prod)."""
    h = hashlib.sha512(text.encode()).digest()
    raw = [b for b in h] * (DIM // len(h) + 1)
    vec = [float(v) / 255.0 for v in raw[:DIM]]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) + 1e-9)


server = Server(name="mcp-embeddings", version="1.0.0", title="Embeddings & Semantic Search", description="Vector embeddings + semantic search across collections.")


@server.tool(description="Embed one or more texts into normalized vectors")
def embed(texts: list) -> dict:
    return {"embeddings": [_hash_vec(t) for t in texts], "dim": DIM, "count": len(texts)}


@server.tool(description="Embed a single query string")
def embed_query(text: str) -> dict:
    return {"embedding": _hash_vec(text), "dim": DIM}


@server.tool(description="Upsert a vector into a collection")
def upsert(collection: str, id: str, vector: list, payload: dict = None) -> dict:
    payload = payload or {}
    COLLECTIONS[collection]["vectors"][id] = vector
    COLLECTIONS[collection]["payloads"][id] = payload
    return {"ok": True, "collection": collection, "id": id}


@server.tool(description="Search a collection by cosine similarity")
def search(collection: str, vector: list, top_k: int = 5) -> dict:
    if collection not in COLLECTIONS:
        return {"ok": False, "error": f"collection_not_found: {collection}"}
    vectors = COLLECTIONS[collection]["vectors"]
    payloads = COLLECTIONS[collection]["payloads"]
    scored = sorted(((id_, _cosine(vector, v), payloads.get(id_, {})) for id_, v in vectors.items()), key=lambda x: -x[1])
    return {"ok": True, "results": [{"id": i, "score": round(s, 4), "payload": p} for i, s, p in scored[:top_k]]}


@server.tool(description="Delete a vector from a collection")
def delete(collection: str, id: str) -> dict:
    if id in COLLECTIONS[collection]["vectors"]:
        del COLLECTIONS[collection]["vectors"][id]
        COLLECTIONS[collection]["payloads"].pop(id, None)
        return {"ok": True, "deleted": id}
    return {"ok": False, "error": "not_found"}


@server.tool(description="Stats for a collection")
def collection_stats(collection: str) -> dict:
    if collection not in COLLECTIONS:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "collection": collection, "vectors": len(COLLECTIONS[collection]["vectors"])}


@server.tool(description="Hybrid search: blend keyword + vector similarity")
def hybrid_search(collection: str, query: str, alpha: float = 0.7, top_k: int = 5) -> dict:
    if collection not in COLLECTIONS:
        return {"ok": False, "error": f"collection_not_found: {collection}"}
    q_vec = _hash_vec(query)
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored = []
    for id_, vec in COLLECTIONS[collection]["vectors"].items():
        payload = COLLECTIONS[collection]["payloads"].get(id_, {})
        text = payload.get("text", "")
        terms = set(re.findall(r"\w+", text.lower()))
        kw_score = len(query_terms & terms) / max(1, len(query_terms))
        vec_score = _cosine(q_vec, vec)
        combined = alpha * vec_score + (1 - alpha) * kw_score
        scored.append((id_, combined, vec_score, kw_score))
    scored.sort(key=lambda x: -x[1])
    return {"ok": True, "results": [{"id": i, "combined": round(c, 4), "vector": round(v, 4), "keyword": round(k, 4)} for i, c, v, k in scored[:top_k]]}


if __name__ == "__main__":
    server.run()