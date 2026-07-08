"""Configuration management module for GateFlow settings.

Uses pydantic-settings to load configuration from environment variables.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str | None = Field(
        default=None,
        validation_alias="GEMINI_API_KEY",
        description="Optional API key for live Gemini phrasing.",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias="GEMINI_MODEL",
        description="Gemini model to use for phrasing.",
    )
    redis_url: str | None = Field(
        default=None,
        validation_alias="REDIS_URL",
        description="Optional Redis connection URL for rate limiting.",
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:5173",
        ],
        validation_alias="ALLOWED_ORIGINS",
        description="Allowed CORS origins list.",
    )
    rate_limit_requests_per_minute: int = Field(
        default=20,
        validation_alias="RATE_LIMIT_REQUESTS_PER_MINUTE",
        description="Requests limit per IP per minute.",
    )


# Global settings singleton
settings = Settings()
