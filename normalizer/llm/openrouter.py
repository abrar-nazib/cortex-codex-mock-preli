"""OpenRouter chat-completions provider (cloud, OpenAI-compatible API)."""
from __future__ import annotations

import httpx

from ..config import Settings
from .base import LLMError, LLMProvider


class OpenRouterProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise LLMError("OPENROUTER_API_KEY is not set")
        self._settings = settings

    def complete(self, messages: list[dict[str, str]]) -> str:
        s = self._settings
        headers = {
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
            # OpenRouter likes these for attribution; harmless if generic.
            "HTTP-Referer": "https://queuestorm.local",
            "X-Title": "QueueStorm Normalizer",
        }
        payload = {
            "model": s.openrouter_model,
            "messages": messages,
            "temperature": s.temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            # OpenRouter is strict about the URL path — no double slashes.
            base = s.openrouter_base_url.rstrip("/")
            resp = httpx.post(
                f"{base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=s.request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"OpenRouter request failed: {exc}") from exc
