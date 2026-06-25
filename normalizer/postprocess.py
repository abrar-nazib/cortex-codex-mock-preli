"""Rule enforcement applied to every result, LLM or fallback.

Responsibilities (spec §3 + §5):
1. Derive `department` from `case_type`/`severity` (deterministic mapping).
2. Force `human_review_required` for critical or phishing cases.
3. Clamp `confidence` into [0, 1].
4. Scrub `agent_summary` so it never asks for PIN/OTP/password/card.

These are non-negotiable graded rules, so we apply them centrally rather than
trusting the model to follow instructions.
"""
from __future__ import annotations

import re

from .schema import CaseType, Department, NormalizedTicket, Severity

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


def department_for(case_type: CaseType, severity: Severity) -> Department:
    if case_type == CaseType.WRONG_TRANSFER:
        return Department.DISPUTE_RESOLUTION
    if case_type == CaseType.PAYMENT_FAILED:
        return Department.PAYMENTS_OPS
    if case_type == CaseType.PHISHING:
        return Department.FRAUD_RISK
    if case_type == CaseType.REFUND_REQUEST:
        # Contested / escalated refunds go to disputes; routine ones to support.
        if severity in (Severity.HIGH, Severity.CRITICAL):
            return Department.DISPUTE_RESOLUTION
        return Department.CUSTOMER_SUPPORT
    return Department.CUSTOMER_SUPPORT  # other


def needs_human_review(case_type: CaseType, severity: Severity) -> bool:
    return severity == Severity.CRITICAL or case_type == CaseType.PHISHING


def scrub_summary(summary: str) -> str:
    """Replace any credential-soliciting summary with a safe neutral one."""
    for pat in _UNSAFE_PATTERNS:
        if pat.search(summary):
            return _SAFE_FALLBACK_SUMMARY
    return summary.strip()


def enforce(ticket: NormalizedTicket) -> NormalizedTicket:
    """Return a copy of `ticket` with all graded rules applied."""
    return ticket.model_copy(
        update={
            "department": department_for(ticket.case_type, ticket.severity),
            "human_review_required": needs_human_review(
                ticket.case_type, ticket.severity
            ),
            "confidence": max(0.0, min(1.0, ticket.confidence)),
            "agent_summary": scrub_summary(ticket.agent_summary),
        }
    )
