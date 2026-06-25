"""Enums and Pydantic models — the single source of truth for the contract.

Everything the Normalizer produces must validate against `NormalizedTicket`,
so the Backend can serve it from `POST /sort-ticket` without extra checks.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CaseType(str, Enum):
    WRONG_TRANSFER = "wrong_transfer"
    PAYMENT_FAILED = "payment_failed"
    REFUND_REQUEST = "refund_request"
    PHISHING = "phishing_or_social_engineering"
    OTHER = "other"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Department(str, Enum):
    CUSTOMER_SUPPORT = "customer_support"
    DISPUTE_RESOLUTION = "dispute_resolution"
    PAYMENTS_OPS = "payments_ops"
    FRAUD_RISK = "fraud_risk"


class TicketInput(BaseModel):
    """Incoming request. Only `message` is required by the Normalizer."""

    message: str = Field(..., min_length=1)
    ticket_id: str | None = None
    channel: str | None = None
    locale: str | None = None


class NormalizedTicket(BaseModel):
    """The structured classification result (spec §3 response fields)."""

    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str = Field(..., min_length=1)
    human_review_required: bool
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        # Defensive clamp; the LLM occasionally returns 1.05 / -0.1.
        return max(0.0, min(1.0, v))
