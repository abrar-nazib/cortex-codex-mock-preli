"""Deterministic, keyword-based classifier.

This is the reliability net: if the LLM is disabled, times out, or returns
garbage, this still produces a valid `NormalizedTicket`. It also passes all
5 public sample cases on its own, so the service never depends on the network.

Ordering matters: phishing is checked first because it is the highest-risk
class and its keywords (otp, pin) can co-occur with money language.
"""
from __future__ import annotations

import re

from .schema import CaseType, NormalizedTicket, Severity

# --- keyword banks -----------------------------------------------------------
_PHISHING = [
    "otp", "pin", "password", "passcode", "cvv", "card number",
    "asking my", "asked for my", "scam", "fraud", "suspicious",
    "verify my account", "share my", "won a prize", "click this link",
]
_WRONG_TRANSFER = [
    "wrong number", "wrong recipient", "wrong account", "wrong person",
    "sent to wrong", "sent to the wrong", "mistakenly sent", "by mistake",
    "wrong nagad", "wrong bkash", "get it back", "recover",
]
_PAYMENT_FAILED = [
    "payment failed", "transaction failed", "failed but", "balance deducted",
    "money deducted", "deducted but", "cash out failed", "didn't go through",
    "did not go through", "transfer failed",
]
_REFUND = [
    "refund", "money back", "return my", "changed my mind", "cancel my order",
    "reverse the", "want my money returned",
]


def _contains(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _truncate(message: str, limit: int = 160) -> str:
    msg = " ".join(message.split())
    return msg if len(msg) <= limit else msg[: limit - 1] + "…"


def classify(message: str) -> NormalizedTicket:
    text = message.lower()

    if _contains(text, _PHISHING):
        case_type, severity, conf = CaseType.PHISHING, Severity.CRITICAL, 0.7
        summary = (
            "Customer reports a suspicious request for sensitive credentials "
            "and is checking whether it is legitimate."
        )
    elif _contains(text, _PAYMENT_FAILED):
        case_type, severity, conf = CaseType.PAYMENT_FAILED, Severity.HIGH, 0.7
        summary = "Customer reports a failed payment that may have deducted their balance."
    elif _contains(text, _WRONG_TRANSFER):
        case_type, severity, conf = CaseType.WRONG_TRANSFER, Severity.HIGH, 0.7
        summary = "Customer reports sending money to the wrong recipient and requests recovery."
    elif _contains(text, _REFUND):
        case_type, severity, conf = CaseType.REFUND_REQUEST, Severity.LOW, 0.65
        summary = "Customer requests a refund for a recent transaction."
    else:
        case_type, severity, conf = CaseType.OTHER, Severity.LOW, 0.5
        summary = f"Customer reports an issue: {_truncate(message)}"

    # department + review flag are applied centrally in postprocess; we set
    # provisional values here so the object is independently valid.
    from .postprocess import department_for, needs_human_review

    return NormalizedTicket(
        case_type=case_type,
        severity=severity,
        department=department_for(case_type, severity),
        agent_summary=summary,
        human_review_required=needs_human_review(case_type, severity),
        confidence=conf,
    )
