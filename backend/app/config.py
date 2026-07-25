from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    # backend/app/config.py → repo root
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "sqlite:///./dev.db"

    llm_provider: str = "ollama"  # ollama | openai
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi3:mini"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 25.0

    # local | openai | hash (deterministic, for tests / offline CI)
    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dims: int = 384

    chroma_persist_dir: str = "./.chroma"
    chroma_collection: str = "finops_chunks"

    upload_dir: str = "./uploads"
    fixtures_dir: str = str(_repo_root() / "fixtures")
    chunk_row_size: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
