"""Server-side safety filter.

The agent_summary must NEVER ask the customer for PIN, OTP, password, or full card number.
This is graded — failing it fails the case.
"""
from __future__ import annotations

import re
from typing import Final

# Patterns chosen to match common request phrasings, not just bare keywords.
# Case-insensitive. Match anywhere in the text.
_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\b(pin|otp|one[-\s]?time[-\s]?password)\b", re.IGNORECASE),
    re.compile(r"\b(password|passcode|pwd)\b", re.IGNORECASE),
    re.compile(
        r"\b(full\s+)?(card|credit\s+card|debit\s+card)\s*(number|no\.?|num)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(share|send|provide|give|tell)\b.{0,40}\b(pin|otp|password|card\s*number)\b", re.IGNORECASE),
    # 13-19 digit run, optionally space/dash separated, treated as a card number.
    re.compile(r"(?:\d[ -]?){13,19}"),
)


def violates_safety(text: str) -> bool:
    """True if `text` would cause the grader to fail this case."""
    if not text:
        return False
    return any(p.search(text) for p in _PATTERNS)


def safe_fallback_summary(ticket_id: str) -> str:
    """Used when the normalizer (or our merge) produced an unsafe summary."""
    return (
        f"Ticket {ticket_id} flagged for human review. "
        "An agent will respond shortly and will never ask for PIN, OTP, password, "
        "or full card number."
    )
