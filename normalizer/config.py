"""Env-driven settings. No secrets in the repo — everything comes from env.

Switch providers with a single variable:
    NORMALIZER_PROVIDER=openrouter   (cloud, needs OPENROUTER_API_KEY)
    NORMALIZER_PROVIDER=ollama       (local, GPU-free)
    NORMALIZER_PROVIDER=rules        (no LLM, deterministic fallback only)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    provider: str

    # OpenRouter
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_model: str

    # OLLAMA
    ollama_base_url: str
    ollama_model: str

    # Shared
    request_timeout: float
    temperature: float
    log_level: str


def load_settings() -> Settings:
    return Settings(
        provider=os.getenv("NORMALIZER_PROVIDER", "rules").strip().lower(),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_base_url=os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ),
        openrouter_model=os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"
        ),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
        request_timeout=float(os.getenv("NORMALIZER_TIMEOUT", "25")),
        temperature=float(os.getenv("NORMALIZER_TEMPERATURE", "0")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )


SETTINGS = load_settings()
