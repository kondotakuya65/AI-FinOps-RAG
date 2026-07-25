"""Chroma vector store with per-source delete for re-ingest."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from app.config import Settings, get_settings
from app.embeddings import get_embedder, safe_chunk_id, sanitize_metadata
from app.ingest.chunking import Chunk


class VectorStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        Path(self.settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.settings.chroma_persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=self.settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = get_embedder()

    @property
    def collection(self):
        return self._collection

    def delete_by_source(self, source_file: str) -> None:
        try:
            self._collection.delete(where={"source_file": source_file})
        except Exception:
            # empty collection / no matches
            pass

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        ids = [safe_chunk_id(c.chunk_id) for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [sanitize_metadata(c.metadata) for c in chunks]
        embeddings = self._embedder.embed_documents(documents)
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(chunks)

    def count(self) -> int:
        return self._collection.count()

    def query(
        self,
        text: str,
        n_results: int = 8,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        embedding = self._embedder.embed_query(text)
        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return self._collection.query(**kwargs)


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()


def clear_vector_store_cache() -> None:
    get_vector_store.cache_clear()
