"""Pydantic schemas. The backend is the public contract surface for this round."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ---- Enums (locked by the spec) --------------------------------------------

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


class Channel(str, Enum):
    APP = "app"
    SMS = "sms"
    CALL_CENTER = "call_center"
    MERCHANT_PORTAL = "merchant_portal"


class Locale(str, Enum):
    BN = "bn"
    EN = "en"
    MIXED = "mixed"


# ---- Wire models ------------------------------------------------------------

class TicketIn(BaseModel):
    """Inbound CRM ticket from frontend / public API."""
    model_config = ConfigDict(extra="ignore")

    ticket_id: str = Field(min_length=1, max_length=128)
    channel: Optional[Channel] = None
    locale: Optional[Locale] = None
    message: str = Field(min_length=1)


class TicketOut(BaseModel):
    """Final response sent back to caller."""
    ticket_id: str
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    human_review_required: bool
    confidence: float = Field(ge=0.0, le=1.0)


class HealthOut(BaseModel):
    status: str = "ok"
    normalizer_url: str


# ---- Internal: what we forward to the normalizer ----------------------------

class NormalizeRequest(BaseModel):
    """Full schema forwarded to normalizer so it has the same view as us."""
    model_config = ConfigDict(extra="ignore")

    ticket_id: str
    channel: Optional[str] = None
    locale: Optional[str] = None
    message: str
