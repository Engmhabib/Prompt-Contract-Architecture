"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """PCA runtime settings.

    Loaded from environment variables with the ``PCA_`` prefix.
    """

    model_config = SettingsConfigDict(env_prefix="PCA_", env_file=".env", extra="ignore")

    contracts_dir: Path = Path("./contracts")
    database_url: str = "sqlite+aiosqlite:///./pca.db"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    allow_writes: bool = False
    dev_mode: bool = False  # enables /v1/dev/* convenience endpoints and serves frontend

    llm_provider: str = "mock"  # "litellm" or "mock"
    llm_model: str = "gpt-4o-mini"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached singleton ``Settings`` instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset cached settings (used in tests)."""
    global _settings
    _settings = None
