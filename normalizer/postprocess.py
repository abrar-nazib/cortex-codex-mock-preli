"""Rule enforcement applied to every result, LLM or fallback.

Responsibilities (spec §3 + §5 + operational rules):
1. Derive `department` from `case_type`/`severity` (deterministic mapping).
2. Force `human_review_required` whenever money is at stake or the case is
   contested. This is the central escalation policy — never trust the LLM.
3. Clamp `confidence` into [0, 1].
4. Scrub `agent_summary` so it never asks for PIN/OTP/password/card.

These are non-negotiable graded rules, so we apply them centrally rather than
trusting the model to follow instructions.
"""
from __future__ import annotations

import re

from .schema import CaseType, Department, NormalizedTicket, Severity

# --- Department mapping -----------------------------------------------------

def department_for(case_type: CaseType, severity: Severity) -> Department:
    if case_type == CaseType.WRONG_TRANSFER:
        return Department.DISPUTE_RESOLUTION
    if case_type == CaseType.PAYMENT_FAILED:
        return Department.PAYMENTS_OPS
    if case_type == CaseType.PHISHING:
        return Department.FRAUD_RISK
    if case_type == CaseType.REFUND_REQUEST:
        # Contested / escalated refunds go to disputes; routine ones to support.
        if severity in (Severity.HIGH, Severity.MEDIUM):
            return Department.DISPUTE_RESOLUTION
        return Department.CUSTOMER_SUPPORT
    return Department.CUSTOMER_SUPPORT  # other


# --- Human-review escalation policy ----------------------------------------

# Words / phrases that signal the customer is angry, escalating, or has been
# waiting. Any of these means a human agent must look at the ticket.
_ESCALATION_TERMS = (
    "urgent", "urgently", "immediately", "asap", "now", "nowww",
    "complaint", "complain", "dispute", "police", "lawyer", "legal",
    "5 din", "5 days", "3 din", "3 days", "refund paise ni", "no refund",
    "eskalate", "escalating", "escalate", "compensation", "fix it",
    "this is ridiculous", "this is not the first time", "help needed",
    "dhamka", "fix", "please help", "please look",
)

# Words / phrases that signal money was already moved (so even a "low" severity
# refund or "other" ticket needs human review).
_MONEY_AT_RISK_TERMS = (
    "taka keteche", "taka kete", "taka gone", "deducted", "katteche",
    "balance deducted", "money deducted", "balance gone", "sent money",
    "bKash korchi", "bKash korechi", "send korechi", "paisa pathiyechi",
    "paisa pathiye", "paid", "payment", "transfer",
)


def _looks_contested(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in _ESCALATION_TERMS)


def _money_already_moved(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in _MONEY_AT_RISK_TERMS)


def needs_human_review(case_type: CaseType, severity: Severity, message: str = "") -> bool:
    """Escalation policy. Centralized here so the LLM cannot weaken it."""
    # Always escalate critical + phishing.
    if severity == Severity.CRITICAL:
        return True
    if case_type == CaseType.PHISHING:
        return True
    # Money-already-moved cases need human sign-off on recovery.
    if case_type in (CaseType.WRONG_TRANSFER, CaseType.PAYMENT_FAILED):
        return True
    # Contested refunds (escalation language in the message).
    if case_type == CaseType.REFUND_REQUEST and _looks_contested(message):
        return True
    # Generic safety net: any case where the message itself shows money gone
    # or escalation language, regardless of LLM classification.
    if message and (_looks_contested(message) and _money_already_moved(message)):
        return True
    return False


# --- Summary safety scrub ---------------------------------------------------

# Phrases that would FAIL the safety grader if they appeared in agent_summary.
# We match an *imperative/request* shape near a sensitive term, then redact.
_SENSITIVE = r"(pin|otp|password|passcode|cvv|full card number|card number)"
_UNSAFE_PATTERNS = [
    re.compile(rf"\b(share|send|provide|give|tell|enter|type|confirm)\b[^.]*\b{_SENSITIVE}\b", re.I),
    re.compile(rf"\bwhat(?:'s| is)\b[^.]*\b{_SENSITIVE}\b", re.I),
    re.compile(rf"\byour\b[^.]*\b{_SENSITIVE}\b[^.]*\?", re.I),
]

_SAFE_FALLBACK_SUMMARY = (
    "Customer reports a sensitive security concern; details withheld for safety."
)


def scrub_summary(summary: str) -> str:
    """Replace any credential-soliciting summary with a safe neutral one."""
    for pat in _UNSAFE_PATTERNS:
        if pat.search(summary):
            return _SAFE_FALLBACK_SUMMARY
    return summary.strip()


def enforce(ticket: NormalizedTicket, message: str = "") -> NormalizedTicket:
    """Return a copy of `ticket` with all graded rules applied.

    `message` is the original customer message — used to detect escalation
    language that the LLM may have missed when setting human_review_required.
    """
    return ticket.model_copy(
        update={
            "department": department_for(ticket.case_type, ticket.severity),
            "human_review_required": needs_human_review(
                ticket.case_type, ticket.severity, message=message
            ),
            "confidence": max(0.0, min(1.0, ticket.confidence)),
            "agent_summary": scrub_summary(ticket.agent_summary),
        }
    )
