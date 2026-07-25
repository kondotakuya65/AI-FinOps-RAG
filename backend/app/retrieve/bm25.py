"""BM25 keyword index over ingested chunks (IDs, SKUs, amounts)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from rank_bm25 import BM25Okapi

from app.retrieve.vector import VectorStore, get_vector_store

_TOKEN = re.compile(r"[a-z0-9$._%-]+", re.I)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


@dataclass
class BM25Hit:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    score: float


class BM25Index:
    def __init__(self) -> None:
        self._ids: list[str] = []
        self._texts: list[str] = []
        self._metas: list[dict[str, Any]] = []
        self._bm25: BM25Okapi | None = None

    def rebuild(self, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]) -> None:
        self._ids = ids
        self._texts = documents
        self._metas = metadatas
        corpus = [tokenize(doc) for doc in documents]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def rebuild_from_vector_store(self, store: VectorStore | None = None) -> int:
        store = store or get_vector_store()
        count = store.count()
        if count == 0:
            self._ids, self._texts, self._metas, self._bm25 = [], [], [], None
            return 0
        raw = store.collection.get(include=["documents", "metadatas"])
        ids = list(raw.get("ids") or [])
        docs = list(raw.get("documents") or [])
        metas = list(raw.get("metadatas") or [])
        self.rebuild(ids, docs, metas)
        return len(ids)

    def search(self, query: str, top_k: int = 8) -> list[BM25Hit]:
        if not self._bm25 or not self._ids:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        hits: list[BM25Hit] = []
        for i in ranked:
            if scores[i] <= 0:
                continue
            hits.append(
                BM25Hit(
                    chunk_id=self._ids[i],
                    text=self._texts[i],
                    metadata=dict(self._metas[i] or {}),
                    score=float(scores[i]),
                )
            )
        return hits


@lru_cache
def get_bm25_index() -> BM25Index:
    index = BM25Index()
    try:
        index.rebuild_from_vector_store()
    except Exception:
        pass
    return index


def clear_bm25_cache() -> None:
    get_bm25_index.cache_clear()


def refresh_bm25(store: VectorStore | None = None) -> int:
    clear_bm25_cache()
    return get_bm25_index().rebuild_from_vector_store(store)
