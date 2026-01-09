"""
CodingAgent Configuration Module

Centralized configuration using Pydantic Settings.
All settings loaded from environment variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Application
    # ─────────────────────────────────────────────────────────────────────────
    app_name: str = "CodingAgent"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # ─────────────────────────────────────────────────────────────────────────
    # Server
    # ─────────────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8080
    workers: int = 1
    reload: bool = True

    # External URL for frontend to reach backend (used for chart data URLs)
    # In development: http://localhost:8080
    # In production: https://api.yourdomain.com
    api_base_url: str = "http://localhost:8080"

    # ─────────────────────────────────────────────────────────────────────────
    # PostgreSQL
    # ─────────────────────────────────────────────────────────────────────────
    postgres_user: str = "codeagent"
    postgres_password: str = "codeagent"
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "codeagent"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    db_command_timeout: int = 60

    @computed_field
    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """Sync PostgreSQL connection URL (for migrations)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Redis
    # ─────────────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6380
    redis_password: str | None = None
    redis_db: int = 0
    redis_default_ttl: int = 3600  # Default TTL in seconds (60 minutes)
    redis_max_connections: int = 10
    result_cache_ttl: int = 3600  # Result cache TTL in seconds (60 minutes)

    @computed_field
    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ─────────────────────────────────────────────────────────────────────────
    # MinIO (S3-compatible storage)
    # ─────────────────────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "codingagent"

    @field_validator("minio_endpoint")
    @classmethod
    def clean_minio_endpoint(cls, v: str) -> str:
        """Strip protocol and trailing slash from endpoint."""
        if v:
            v = v.replace("http://", "").replace("https://", "")
            if v.endswith("/"):
                v = v[:-1]
        return v

    # ─────────────────────────────────────────────────────────────────────────
    # JWT Authentication
    # ─────────────────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="Secret key for JWT encoding/decoding",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # ─────────────────────────────────────────────────────────────────────────
    # Admin User (created on first startup)
    # ─────────────────────────────────────────────────────────────────────────
    admin_email: str = "admin@example.com"
    admin_password: str = "Password@1234"
    admin_full_name: str = "System Administrator"
    admin_storage_limit_mb: int = 10000  # Default storage limit for admin
    admin_table_limit: int = 1000  # Default table limit for admin

    # ─────────────────────────────────────────────────────────────────────────
    # LLM Configuration
    # ─────────────────────────────────────────────────────────────────────────
    llm_model: str = "nvidia_nim/openai/gpt-oss-120b"
    small_llm_model: str = (
        "nvidia_nim/openai/gpt-oss-20b"  # Smaller/cheaper model for testing and simple tasks
    )
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_api_base: str = "https://openrouter.ai/api/v1"

    # ─────────────────────────────────────────────────────────────────────────
    # CORS
    # ─────────────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5170", "http://localhost:5173"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # ─────────────────────────────────────────────────────────────────────────
    # Code Execution
    # ─────────────────────────────────────────────────────────────────────────
    executor_type: str = "smolagents"  # "smolagents" or "daytona"
    executor_timeout_seconds: int = 30
    executor_max_retries: int = 3

    # ─────────────────────────────────────────────────────────────────────────
    # Database Operations
    # ─────────────────────────────────────────────────────────────────────────
    max_table_sample_size: int = 100


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience alias
settings = get_settings()
