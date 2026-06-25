"""ORM models. Ticket is keyed by ticket_id (the spec's primary identifier)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    # Primary key: the ticket_id from the CRM. Same value the caller echoes back.
    ticket_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Base model fields — populated when normalizer returns, or by our own
    # fallback if normalizer is unavailable.
    case_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    department: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_review_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Operational
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
