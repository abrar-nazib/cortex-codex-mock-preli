"""OLLAMA local chat provider (GPU-free, runs on CPU)."""
from __future__ import annotations

import httpx

from ..config import Settings
from .base import LLMError, LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def complete(self, messages: list[dict[str, str]]) -> str:
        s = self._settings
        payload = {
            "model": s.ollama_model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": s.temperature},
        }
        try:
            resp = httpx.post(
                f"{s.ollama_base_url}/api/chat",
                json=payload,
                timeout=s.request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"OLLAMA request failed: {exc}") from exc
