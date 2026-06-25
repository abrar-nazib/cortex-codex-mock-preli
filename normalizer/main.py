"""FastAPI service — exposes POST /normalize for the Backend to call.

Run from the project root (parent of this package):
    uvicorn normalizer.main:app --reload --port 8001
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import SETTINGS
from .normalizer import normalize
from .schema import NormalizedTicket

logging.basicConfig(
    level=SETTINGS.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("normalizer.api")


def _preview(text: str, width: int = 160) -> str:
    if not text:
        return ""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


app = FastAPI(title="QueueStorm Normalizer", version="1.0.0")


class NormalizeRequest(BaseModel):
    message: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/normalize", response_model=NormalizedTicket)
def normalize_ticket(req: NormalizeRequest) -> NormalizedTicket:
    log.info("POST /normalize msg=%r", _preview(req.message))
    if not req.message.strip():
        log.warning("normalize rejected: empty message")
        raise HTTPException(status_code=422, detail="message must not be empty")
    result = normalize(req.message)
    log.info("normalize OK case=%s severity=%s department=%s review=%s confidence=%.2f summary=%r",
             result.case_type.value, result.severity.value, result.department.value,
             result.human_review_required, result.confidence,
             _preview(result.agent_summary))
    return result
