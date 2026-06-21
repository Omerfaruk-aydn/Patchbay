"""Application configuration using Pydantic Settings.

All configuration is loaded from environment variables (with .env file
support for development). Sensitive values (API keys, JWT secrets)
MUST come from environment variables, not .env files in production.

Environment variable naming: UPPERCASE with underscores.
Example: DATABASE_URL, REDIS_URL, JWT_SECRET_KEY
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — loaded from environment variables."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "case_sensitive": False,
    }

    # ── Application ──────────────────────────────────────────────
    app_name: str = Field(default="Patchbay Gateway", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode (verbose logging, API docs)")

    # ── Database ─────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://patchbay:patchbay@localhost:5432/patchbay",
        description="Async PostgreSQL connection URL",
    )

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # ── JWT Authentication ───────────────────────────────────────
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-a-real-secret",
        description="JWT signing secret (MUST be changed in production)",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Access token expiration in minutes",
    )

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # ── Rate Limiting ────────────────────────────────────────────
    default_rate_limit_rpm: int = Field(
        default=1000,
        ge=1,
        description="Default rate limit (requests per minute)",
    )

    # ── Semantic Cache ───────────────────────────────────────────
    semantic_cache_similarity_threshold: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity for semantic cache hit",
    )
    embedding_model: str = Field(
        default="text-embedding-ada-002",
        description="Embedding model for semantic cache",
    )

    # ── Observability ────────────────────────────────────────────
    otel_service_name: str = Field(
        default="patchbay-gateway",
        description="OpenTelemetry service name",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP exporter endpoint",
    )

    # ── Circuit Breaker ──────────────────────────────────────────
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        ge=1,
        description="Consecutive failures to trip circuit breaker",
    )
    circuit_breaker_cooldown_seconds: int = Field(
        default=30,
        ge=5,
        description="Seconds to wait before testing a broken circuit",
    )

    # ── Provider Timeouts ────────────────────────────────────────
    provider_timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=300.0,
        description="Default timeout for provider API calls",
    )
    provider_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for transient provider errors",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Settings are loaded once and cached for the lifetime of the process.
    Environment variables take precedence over .env file values.
    """
    return Settings()
