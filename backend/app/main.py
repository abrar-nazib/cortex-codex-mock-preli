"""FastAPI app entrypoint."""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, init_db
from app.pipeline import classify
from app.schemas import HealthOut, TicketIn, TicketOut

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="Cortex Mock Preliminary — Backend",
    version="0.1.0",
    description="CRM ticket triage. Public HTTPS entrypoint for the Codex mock round.",
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    s = get_settings()
    return HealthOut(status="ok", normalizer_url=s.normalizer_url)


@app.post("/sort-ticket", response_model=TicketOut)
def sort_ticket(payload: TicketIn, db: Session = Depends(get_db)) -> TicketOut:
    try:
        return classify(db, payload)
    except RuntimeError as exc:
        # Safety-rule violation surfaces as 500 so the grader counts it as a fail.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
