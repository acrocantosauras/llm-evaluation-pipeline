from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "LLM Evaluation Pipeline"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "info"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/llm_eval"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Worker
    WORKER_CONCURRENCY: int = 2
    WORKER_MAX_RETRIES: int = 3

    # LLM Judge
    JUDGE_PROVIDER: str = "openai"
    JUDGE_MODEL: str = "gpt-4o-mini"
    JUDGE_TEMPERATURE: float = 0.0
    JUDGE_MAX_RETRIES: int = 3
    JUDGE_TIMEOUT: float = 30.0

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: float = 60.0
    # Fail behavior when Redis is unavailable during a rate-limit check.
    # False = fail open (allow request, log warning) — availability over strictness.
    # True = fail closed (503) — set this if abuse protection must never degrade.
    RATE_LIMIT_FAIL_CLOSED: bool = False

    # Evaluation concurrency & limits
    # Max concurrent blocking evaluations per process (bounded thread usage).
    EVAL_MAX_CONCURRENCY: int = 4
    # Seconds to wait for an evaluation slot before returning 503.
    EVAL_SLOT_TIMEOUT: float = 30.0
    # Max items accepted per async batch submission.
    MAX_BATCH_ITEMS: int = 100

    # Authentication
    # Explicit opt-in for the development-only "first project" auth fallback.
    # Never honored when APP_ENV is production or ci.
    ALLOW_DEV_AUTH_FALLBACK: bool = False

    # CORS (production should NOT use ["*"])
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Observability
    PROMETHEUS_ENABLED: bool = True
    OPENTELEMETRY_ENABLED: bool = False
    OPENTELEMETRY_ENDPOINT: str = "http://localhost:4317"

    # Dashboard
    DASHBOARD_URL: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
