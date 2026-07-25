from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "ai-finops-rag",
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
        "llm_model": (
            settings.ollama_model
            if settings.llm_provider == "ollama"
            else settings.openai_model
        ),
        "database_url_scheme": settings.database_url.split(":", 1)[0],
        "embedding_provider": settings.embedding_provider,
    }
