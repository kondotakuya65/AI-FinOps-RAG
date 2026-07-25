"""Postgres vector backend (pgvector-ready) as an alternative to Chroma."""

from __future__ import annotations

import json
import math
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import Settings, get_settings
from app.db.session import get_engine
from app.embeddings import get_embedder, safe_chunk_id, sanitize_metadata
from app.ingest.chunking import Chunk


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class PostgresVectorStore:
    """
    Stores chunk embeddings in Postgres JSONB.

    Schema is intentionally simple for demos. For production HNSW, enable:
      CREATE EXTENSION IF NOT EXISTS vector;
    and migrate embedding_json → vector(N).
    """

    def __init__(self, settings: Settings | None = None, engine: Engine | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.database_url.startswith("postgresql"):
            raise RuntimeError(
                "VECTOR_BACKEND=postgres requires a PostgreSQL DATABASE_URL"
            )
        self.engine = engine or get_engine()
        self._embedder = get_embedder()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS vector_chunks (
                        id TEXT PRIMARY KEY,
                        source_file TEXT NOT NULL,
                        document TEXT NOT NULL,
                        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                        embedding_json JSONB NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_vector_chunks_source "
                    "ON vector_chunks (source_file)"
                )
            )

    def delete_by_source(self, source_file: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM vector_chunks WHERE source_file = :src"),
                {"src": source_file},
            )

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        embeddings = self._embedder.embed_documents([c.text for c in chunks])
        with self.engine.begin() as conn:
            for chunk, emb in zip(chunks, embeddings):
                conn.execute(
                    text(
                        """
                        INSERT INTO vector_chunks (id, source_file, document, metadata_json, embedding_json)
                        VALUES (:id, :src, :doc, CAST(:meta AS jsonb), CAST(:emb AS jsonb))
                        ON CONFLICT (id) DO UPDATE SET
                          source_file = EXCLUDED.source_file,
                          document = EXCLUDED.document,
                          metadata_json = EXCLUDED.metadata_json,
                          embedding_json = EXCLUDED.embedding_json
                        """
                    ),
                    {
                        "id": safe_chunk_id(chunk.chunk_id),
                        "src": str(chunk.metadata.get("source_file") or ""),
                        "doc": chunk.text,
                        "meta": json.dumps(sanitize_metadata(chunk.metadata)),
                        "emb": json.dumps(emb),
                    },
                )
        return len(chunks)

    def count(self) -> int:
        with self.engine.connect() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM vector_chunks")).scalar() or 0)

    def query(
        self,
        text: str,
        n_results: int = 8,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        q_emb = self._embedder.embed_query(text)
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, document, metadata_json, embedding_json FROM vector_chunks")
            ).mappings().all()

        scored: list[tuple[float, Any]] = []
        for row in rows:
            meta = row["metadata_json"] or {}
            if isinstance(meta, str):
                meta = json.loads(meta)
            if where:
                ok = True
                for key, value in where.items():
                    if meta.get(key) != value:
                        ok = False
                        break
                if not ok:
                    continue
            emb = row["embedding_json"]
            if isinstance(emb, str):
                emb = json.loads(emb)
            score = _cosine(q_emb, list(emb))
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:n_results]
        return {
            "ids": [[row["id"] for _, row in top]],
            "documents": [[row["document"] for _, row in top]],
            "metadatas": [
                [
                    row["metadata_json"]
                    if isinstance(row["metadata_json"], dict)
                    else json.loads(row["metadata_json"] or "{}")
                    for _, row in top
                ]
            ],
            "distances": [[1.0 - score for score, _ in top]],
        }

    @property
    def collection(self):
        """Duck-typed for BM25 rebuild (get ids/documents/metadatas)."""
        store = self

        class _Coll:
            def get(self, include=None):  # type: ignore[no-untyped-def]
                with store.engine.connect() as conn:
                    rows = conn.execute(
                        text("SELECT id, document, metadata_json FROM vector_chunks")
                    ).mappings().all()
                return {
                    "ids": [r["id"] for r in rows],
                    "documents": [r["document"] for r in rows],
                    "metadatas": [
                        r["metadata_json"]
                        if isinstance(r["metadata_json"], dict)
                        else json.loads(r["metadata_json"] or "{}")
                        for r in rows
                    ],
                }

        return _Coll()
