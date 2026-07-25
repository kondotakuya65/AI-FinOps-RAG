from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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

    embedding_provider: str = "local"  # local | openai
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"

    chroma_persist_dir: str = "./.chroma"
    chroma_collection: str = "finops_chunks"

    upload_dir: str = "./uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
