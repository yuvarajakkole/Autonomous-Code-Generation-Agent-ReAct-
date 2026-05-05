from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_provider": settings.LLM_PROVIDER,
        "model": settings.OPENAI_MODEL if settings.LLM_PROVIDER == "openai" else settings.LOCAL_LLM_MODEL,
        "max_iterations": settings.MAX_ITERATIONS,
        "quality_threshold": settings.QUALITY_THRESHOLD,
    }
