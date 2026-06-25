"""LLM provider package + factory."""
from __future__ import annotations

from ..config import Settings
from .base import LLMError, LLMProvider


def get_provider(settings: Settings) -> LLMProvider | None:
    """Build the configured provider, or None for the rules-only mode."""
    provider = settings.provider
    if provider == "openrouter":
        from .openrouter import OpenRouterProvider

        return OpenRouterProvider(settings)
    if provider == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider(settings)
    # "rules" or anything unknown -> no LLM, deterministic fallback only.
    return None


__all__ = ["LLMError", "LLMProvider", "get_provider"]
