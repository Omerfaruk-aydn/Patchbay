from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Application
    app_name: str = "Patchbay Gateway"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://patchbay:patchbay@localhost:5432/patchbay"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Rate Limiting
    default_rate_limit_rpm: int = 1000

    # Semantic Cache
    semantic_cache_similarity_threshold: float = 0.95
    embedding_model: str = "text-embedding-ada-002"

    # Observability
    otel_service_name: str = "patchbay-gateway"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"


@lru_cache
def get_settings() -> Settings:
    return Settings()
