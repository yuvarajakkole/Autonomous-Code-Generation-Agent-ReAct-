from typing import List, Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ReAct Code Refinement Agent"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    LLM_PROVIDER: Literal["openai", "local"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"     # 100x cheaper than gpt-4o
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_LLM_MODEL: str = "codellama"

    # ReAct loop — 3 iterations max, 2 LLM calls each = 6 calls total max
    MAX_ITERATIONS: int = 3
    QUALITY_THRESHOLD: float = 0.80
    MIN_ACCEPTABLE_SCORE: float = 0.50

    # Token caps per call
    MAX_TOKENS_GENERATION: int = 4000   # generate/refine call — needs space for full HTML
    MAX_TOKENS_EVALUATION: int = 500    # eval call — just scores + feedback
    MAX_TOKENS_PLANNING:   int = 300
    MAX_TOKENS_TESTS:      int = 1500

    DOCKER_TIMEOUT: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
