"""Application configuration via Pydantic settings."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def current_year() -> int:
    """Tahun berjalan (untuk default tahun harga/pricing)."""
    from datetime import datetime

    return datetime.now().year


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

    @property
    def seed_data_path(self) -> Path:
        """Folder data seed bawaan (di-bundle dalam image)."""
        return Path(__file__).resolve().parents[1] / "seed_data"

    # Seeding
    auto_seed: bool = Field(
        default=True,
        description="Saat startup, isi DB dari seed bawaan bila tabel AHSP kosong.",
    )

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

    # Set False untuk MATIKAN verifikasi LLM saat matching → murni rule-based
    # (cepat, tanpa API key). Sistem tetap jalan penuh: parse → match → harga → export.
    matching_use_llm: bool = Field(
        default=True,
        description="Pakai LLM untuk verifikasi match. False = murni rule-based (tanpa AI).",
    )

    # Auth / security (multi-user)
    secret_key: str = Field(
        default="CHANGE_ME_dev_only_secret_do_not_use_in_production",
        description="Kunci HMAC untuk sign JWT. WAJIB di-set acak di production.",
    )
    access_token_expire_minutes: int = 60 * 24  # 1 hari
    allow_open_registration: bool = Field(
        default=True,
        description="Bila False, hanya superuser yang bisa buat user baru.",
    )

    @property
    def secret_is_default(self) -> bool:
        return self.secret_key.startswith("CHANGE_ME")

    # CORS — cukup daftar domain dipisah koma, mis:
    #   CORS_ORIGINS=https://rabmax.cvbintang.com,https://domain-lain.com
    # Atau "*" untuk mengizinkan semua (aman di sini karena auth pakai Bearer token,
    # bukan cookie). Default "*" supaya langsung jalan; persempit kapan saja.
    cors_origins: Annotated[list[str], NoDecode] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> object:
        """Terima daftar dipisah koma, JSON array, atau '*'."""
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return ["*"]
            if s.startswith("["):  # format JSON tetap didukung
                import json

                return json.loads(s)
            return [o.strip() for o in s.split(",") if o.strip()]
        return v

    @property
    def cors_allow_all(self) -> bool:
        return "*" in self.cors_origins

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
