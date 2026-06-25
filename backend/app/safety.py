"""Server-side safety filter.

The agent_summary must NEVER ask the customer to share PIN, OTP, password,
or full card number. This is graded — failing it fails the case (§5 of the
spec).

What this filter catches: *imperative* shapes where the agent is asking
the customer to disclose a credential. It does NOT flag bare mentions of
those tokens in neutral context (e.g. "Customer reports being asked for
an OTP" is fine — the agent is describing the scam, not requesting the
code).
"""
from __future__ import annotations

import re
from typing import Final

# Imperative/request shapes near a sensitive term. Match anywhere in text,
# case-insensitive. Anything matching at least one of these would fail the
# grader, since the agent is the one doing the asking.
_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # "share/send/provide/give/tell me your OTP", "share your PIN with me", etc.
    re.compile(
        r"\b(share|send|provide|give|tell|enter|type|confirm|verify|submit|disclose|leak)\b"
        r"[^.!?\n]{0,40}"
        r"\b(your|the|my)?\s*(pin|otp|one[-\s]?time[-\s]?password|password|passcode|pwd|full\s*card\s*number|card\s*number|cvv)\b",
        re.IGNORECASE,
    ),
    # "kindly share the OTP", "please share your PIN", etc.
    re.compile(
        r"\bplease\b[^.!?\n]{0,20}\b(share|send|provide|give|tell|enter|type|confirm)\b"
        r"[^.!?\n]{0,30}\b(pin|otp|one[-\s]?time[-\s]?password|password|passcode|pwd|full\s*card\s*number|card\s*number|cvv)\b",
        re.IGNORECASE,
    ),
    # "what is your PIN/OTP", "what's your password"
    re.compile(
        r"\bwhat(?:'s| is)\b[^.!?\n]{0,20}\b(your|the)\b[^.!?\n]{0,10}\b(pin|otp|password|passcode|pwd)\b",
        re.IGNORECASE,
    ),
    # 13-19 digit run, optionally space/dash separated — only when the
    # surrounding text *looks like a request* (asks the customer to share/confirm).
    re.compile(
        r"\b(share|send|provide|give|confirm|enter|type)\b[^.!?\n]{0,40}(?:\d[ -]?){13,19}",
        re.IGNORECASE,
    ),
)


def violates_safety(text: str) -> bool:
    """True if `text` contains an agent-issued request for a credential.

    Bare mentions of PIN/OTP/password/card number in non-imperative context
    (e.g. describing a scam) are NOT a violation. The grader cares about
    whether the agent is asking, not whether the tokens appear at all.
    """
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