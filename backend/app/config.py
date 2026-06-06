"""Application configuration via Pydantic settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All env-driven config. Set via .env or environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_env: Literal["development", "production"] = "development"
    app_name: str = "BOQ Generator"
    log_level: str = "INFO"

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://boq_user:boq_pass@localhost:5432/boq",
        description="PostgreSQL connection URL",
    )

    # Storage
    storage_path: Path = Path("/app/storage")

    @property
    def upload_path(self) -> Path:
        return self.storage_path / "uploads"

    @property
    def output_path(self) -> Path:
        return self.storage_path / "outputs"

    @property
    def master_data_path(self) -> Path:
        return self.storage_path / "master_data"

    # AI providers
    anthropic_api_key: str | None = None
    mistral_api_key: str | None = None
    openai_api_key: str | None = None

    default_ai_provider: Literal["claude", "mistral", "openai"] = "claude"
    default_ai_model_parser: str = "claude-sonnet-4-5"
    default_ai_model_matcher: str = "claude-sonnet-4-5"
    default_ai_model_validator: str = "claude-haiku-4-5"
    default_ai_model_profit: str = "claude-sonnet-4-5"

    # Fallback chain when primary provider fails
    ai_fallback_order: list[Literal["claude", "mistral", "openai"]] = [
        "claude",
        "mistral",
        "openai",
    ]

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # File upload limits
    max_upload_size_mb: int = 50

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    settings = Settings()
    # Ensure storage dirs exist
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.output_path.mkdir(parents=True, exist_ok=True)
    settings.master_data_path.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
