"""Centralised settings, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    backend_host: str = Field(default="127.0.0.1")
    backend_port: int = Field(default=8000)

    normalizer_url: str = Field(default="http://127.0.0.1:9000")
    normalizer_timeout_s: float = Field(default=20.0)
    normalizer_max_retries: int = Field(default=2)
    normalizer_retry_backoff_s: float = Field(default=0.5)

    database_url: str = Field(default="sqlite:///./tickets.db")

    safety_fail_loud: bool = Field(default=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
