"""Abstract LLM provider interface.

A provider takes a chat message list and returns the raw model text.
JSON parsing/validation happens upstream in `normalizer.py`, so providers
stay thin and swappable (OpenRouter <-> OLLAMA).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Raised when a provider cannot return a usable completion."""


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Return the raw text content of the model's reply.

        Raises:
            LLMError: on timeout, transport, or auth failure.
        """
        raise NotImplementedError
