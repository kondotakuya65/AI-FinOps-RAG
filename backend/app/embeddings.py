"""Embedding providers: local sentence-transformers, OpenAI, or hash (tests)."""

from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

import httpx

from app.config import Settings, get_settings


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Deterministic pseudo-embeddings for offline tests (no model download)."""

    def __init__(self, dims: int = 384) -> None:
        self.dims = dims

    def _one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        seed = digest
        while len(values) < self.dims:
            seed = hashlib.sha256(seed).digest()
            for i in range(0, len(seed), 4):
                if len(values) >= self.dims:
                    break
                chunk = int.from_bytes(seed[i : i + 4], "big")
                values.append((chunk / 0xFFFFFFFF) * 2.0 - 1.0)
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._one(text)


class LocalEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": texts}
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()["data"]
        data_sorted = sorted(data, key=lambda row: row["index"])
        return [row["embedding"] for row in data_sorted]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache
def get_embedder(provider: str | None = None) -> Embedder:
    settings = get_settings()
    name = (provider or settings.embedding_provider).lower()
    if name == "hash":
        return HashEmbedder(settings.embedding_dims)
    if name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY required when EMBEDDING_PROVIDER=openai")
        return OpenAIEmbedder(settings.openai_api_key, settings.openai_embedding_model)
    if name == "local":
        return LocalEmbedder(settings.embedding_model)
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {name}")


def clear_embedder_cache() -> None:
    get_embedder.cache_clear()


def sanitize_metadata(meta: dict) -> dict:
    """Chroma metadata values must be str|int|float|bool."""
    clean: dict = {}
    for key, value in meta.items():
        if value is None:
            clean[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = str(value)
    # Chroma ids / where filters dislike some chars in keys only; values OK
    return clean


_SAFE_ID = re.compile(r"[^a-zA-Z0-9._-]+")


def safe_chunk_id(chunk_id: str) -> str:
    return _SAFE_ID.sub("_", chunk_id)
