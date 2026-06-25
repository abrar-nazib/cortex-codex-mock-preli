"""Public entry point: `normalize(message) -> NormalizedTicket`.

Flow:
    1. Try the configured LLM provider (if any).
    2. Parse + validate its JSON into NormalizedTicket.
    3. On ANY failure, fall back to the deterministic rule classifier.
    4. Apply graded post-processing rules to the result either way.

The function is total: it always returns a valid NormalizedTicket and never
raises, so the Backend can call it without guarding every request.
"""
from __future__ import annotations

import json
import logging

from . import fallback, postprocess
from .config import SETTINGS, Settings
from .llm import get_provider
from .prompts.classification_prompt import build_messages
from .schema import NormalizedTicket, TicketInput

logger = logging.getLogger("normalizer")


def _extract_json(raw: str) -> dict:
    """Best-effort parse — tolerate markdown fences / stray prose."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") :]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model output")
    return json.loads(raw[start : end + 1])


def _classify_with_llm(message: str, settings: Settings) -> NormalizedTicket | None:
    provider = get_provider(settings)
    if provider is None:
        return None
    try:
        raw = provider.complete(build_messages(message))
        data = _extract_json(raw)
        return NormalizedTicket.model_validate(data)
    except Exception as exc:  # noqa: BLE001 — any failure must degrade to fallback
        logger.warning("LLM classification failed, using fallback: %s", exc)
        return None


def normalize(message: str, settings: Settings = SETTINGS) -> NormalizedTicket:
    """Classify a single customer message into the structured schema."""
    # Validate/normalize input up front (raises on empty message).
    TicketInput(message=message)

    ticket = _classify_with_llm(message, settings)
    if ticket is None:
        ticket = fallback.classify(message)

    return postprocess.enforce(ticket, message=message)
