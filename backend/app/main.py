"""FastAPI app entrypoint."""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, init_db
from app.pipeline import classify
from app.schemas import HealthOut, TicketIn, TicketOut

logging.basicConfig(
    level=get_settings().log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("backend")


def _preview(text: str, width: int = 160) -> str:
    """One-line, length-capped view of a customer message for log lines."""
    if not text:
        return ""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


app = FastAPI(
    title="Cortex Mock Preliminary — Backend",
    version="0.1.0",
    description="CRM ticket triage. Public HTTPS entrypoint for the Codex mock round.",
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    s = get_settings()
    log.info("backend ready normalizer_url=%s db=%s safety_fail_loud=%s",
             s.normalizer_url, s.database_url, s.safety_fail_loud)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    s = get_settings()
    return HealthOut(status="ok", normalizer_url=s.normalizer_url)


@app.post("/sort-ticket", response_model=TicketOut)
def sort_ticket(payload: TicketIn, db: Session = Depends(get_db)) -> TicketOut:
    log.info("POST /sort-ticket ticket_id=%s channel=%s locale=%s msg=%r",
             payload.ticket_id,
             payload.channel.value if payload.channel else None,
             payload.locale.value if payload.locale else None,
             _preview(payload.message))
    try:
        result = classify(db, payload)
    except RuntimeError as exc:
        # Safety-rule violation surfaces as 500 so the grader counts it as a fail.
        log.warning("sort-ticket FAILED ticket_id=%s reason=%s", payload.ticket_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    log.info("sort-ticket OK ticket_id=%s -> case=%s severity=%s department=%s review=%s confidence=%.2f",
             result.ticket_id, result.case_type.value, result.severity.value,
             result.department.value, result.human_review_required, result.confidence)
    return result
