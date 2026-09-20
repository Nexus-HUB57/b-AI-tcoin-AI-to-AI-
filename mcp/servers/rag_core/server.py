r"""
mcp-rag-core — Generic RAG: ingest, chunk, embed, retrieve, rerank.

Tools:
  ingest_document(doc_id, text, metadata)
  chunk(doc_id, max_chunk_size, overlap)
  retrieve(query, top_k, rerank)
  rerank(query, candidates)
  list_documents()
  document_summary(doc_id)
"""

from __future__ import annotations

import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


STORE: dict = defaultdict(dict)  # doc_id -> {"text": ..., "chunks": [...], "metadata": ..., "tf": ...}


def _tfidf_vector(text: str, vocab: dict) -> dict:
    tf = defaultdict(int)
    for tok in re.findall(r"\w+", text.lower()):
        tf[tok] += 1
    n = sum(tf.values()) or 1
    return {tok: (cnt / n) * (1.0 / (1 + vocab.get(tok, 1))) for tok, cnt in tf.items()}


def _cosine_dict(a: dict, b: dict) -> float:
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    norm_a = sum(v * v for v in a.values()) ** 0.5
    norm_b = sum(v * v for v in b.values()) ** 0.5
    return dot / (norm_a * norm_b + 1e-9)


def _build_vocab():
    vocab = {}
    for doc in STORE.values():
        for tok in re.findall(r"\w+", doc["text"].lower()):
            vocab[tok] = vocab.get(tok, 0) + 1
    return vocab


server = Server(name="mcp-rag-core", version="1.0.0", title="RAG Core", description="Ingest, chunk, retrieve, and rerank documents for retrieval-augmented generation.")


@server.tool(description="Ingest a document")
def ingest_document(doc_id: str, text: str, metadata: dict = None) -> dict:
    STORE[doc_id] = {
        "text": text,
        "metadata": metadata or {},
        "chunks": [],
        "tf": {},
    }
    return {"ok": True, "doc_id": doc_id, "length": len(text)}


@server.tool(description="Chunk a document by sliding window")
def chunk(doc_id: str, max_chunk_size: int = 512, overlap: int = 64) -> dict:
    if doc_id not in STORE:
        return {"ok": False, "error": "not_found"}
    text = STORE[doc_id]["text"]
    chunks = []
    i = 0
    while i < len(text):
        end = min(i + max_chunk_size, len(text))
        chunks.append({"id": f"{doc_id}-{len(chunks)}", "text": text[i:end], "offset": i})
        if end == len(text):
            break
        i += max_chunk_size - overlap
    STORE[doc_id]["chunks"] = chunks
    return {"ok": True, "doc_id": doc_id, "count": len(chunks)}


@server.tool(description="Retrieve top-K chunks for a query (TF-IDF)")
def retrieve(query: str, top_k: int = 5, rerank: int = 0) -> dict:
    vocab = _build_vocab()
    q_vec = _tfidf_vector(query, vocab)
    scored = []
    for doc_id, doc in STORE.items():
        if not doc["chunks"]:
            continue
        for c in doc["chunks"]:
            v = _tfidf_vector(c["text"], vocab)
            scored.append((doc_id, c["id"], c["text"], _cosine_dict(q_vec, v)))
    scored.sort(key=lambda x: -x[3])
    if rerank:
        scored = scored[:rerank]
        scored.sort(key=lambda x: -_rerank_score(query, x[2]))
    return {"results": [{"doc_id": d, "chunk_id": ci, "text": t[:200], "score": round(s, 4)} for d, ci, t, s in scored[:top_k]]}


def _rerank_score(query: str, text: str) -> float:
    q_terms = set(re.findall(r"\w+", query.lower()))
    t_terms = set(re.findall(r"\w+", text.lower()))
    return len(q_terms & t_terms) / max(1, len(q_terms))


@server.tool(description="Rerank candidate chunks by query overlap")
def rerank(query: str, candidates: list) -> dict:
    scored = [(c, _rerank_score(query, c)) for c in candidates]
    scored.sort(key=lambda x: -x[1])
    return {"ranked": [{"text": c, "score": round(s, 4)} for c, s in scored]}


@server.tool(description="List all ingested documents")
def list_documents() -> dict:
    return {"documents": [{"id": k, "chunks": len(v["chunks"]), "length": len(v["text"])} for k, v in STORE.items()]}


@server.tool(description="Summary stats for a document")
def document_summary(doc_id: str) -> dict:
    if doc_id not in STORE:
        return {"ok": False, "error": "not_found"}
    d = STORE[doc_id]
    return {"ok": True, "doc_id": doc_id, "chunks": len(d["chunks"]), "length": len(d["text"]), "metadata": d["metadata"]}


if __name__ == "__main__":
    server.run()