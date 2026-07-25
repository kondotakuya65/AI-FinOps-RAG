"""Hybrid retrieval: SQL facts + BM25 + vector search (RRF merge)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.retrieve.bm25 import BM25Index, get_bm25_index
from app.retrieve.vector import VectorStore, get_vector_store


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    score: float
    channels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text[:500],
            "metadata": self.metadata,
            "score": self.score,
            "channels": self.channels,
        }


def _rrf_merge(
    ranked_lists: list[list[tuple[str, str, dict[str, Any], str]]],
    k: int = 60,
    top_n: int = 8,
) -> list[RetrievedChunk]:
    """
    ranked_lists entries: list of (chunk_id, text, metadata, channel)
    already sorted best-first.
    """
    scores: dict[str, float] = {}
    payloads: dict[str, tuple[str, dict[str, Any]]] = {}
    channels: dict[str, set[str]] = {}

    for ranked in ranked_lists:
        for rank, (chunk_id, text, meta, channel) in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            payloads[chunk_id] = (text, meta)
            channels.setdefault(chunk_id, set()).add(channel)

    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return [
        RetrievedChunk(
            chunk_id=cid,
            text=payloads[cid][0],
            metadata=payloads[cid][1],
            score=score,
            channels=sorted(channels[cid]),
        )
        for cid, score in ordered
    ]


def hybrid_retrieve(
    question: str,
    db: Session | None = None,  # reserved for future SQL-guided filters
    *,
    top_k: int = 8,
    where: dict[str, Any] | None = None,
    vector_store: VectorStore | None = None,
    bm25_index: BM25Index | None = None,
) -> list[RetrievedChunk]:
    store = vector_store or get_vector_store()
    bm25 = bm25_index or get_bm25_index()
    if bm25._bm25 is None:
        bm25.rebuild_from_vector_store(store)

    vector_ranked: list[tuple[str, str, dict[str, Any], str]] = []
    try:
        raw = store.query(question, n_results=top_k, where=where)
        ids = (raw.get("ids") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]
        # lower distance = better for cosine in chroma; keep order as returned
        for i, chunk_id in enumerate(ids):
            vector_ranked.append(
                (
                    chunk_id,
                    docs[i] if i < len(docs) else "",
                    dict(metas[i] or {}) if i < len(metas) else {},
                    "vector",
                )
            )
        _ = dists  # retained for future score calibration
    except Exception:
        vector_ranked = []

    bm25_ranked = [
        (hit.chunk_id, hit.text, hit.metadata, "bm25")
        for hit in bm25.search(question, top_k=top_k)
    ]
    return _rrf_merge([vector_ranked, bm25_ranked], top_n=top_k)
