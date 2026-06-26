"""Generic FastAPI service skeleton.

Two endpoints:
  GET  /health     -> {"status":"ok"}
  POST /normalize  -> accepts an API request JSON, returns a placeholder
                      structured response.

This is a placeholder for the SUST CSE Carnival 2026 — Codex Community
Hackathon preliminary. The real classification/reasoning contract gets wired
in here once the official Problem Statement is published. Until then the
service stays up, answers /health, and acknowledges any request body on
/normalize so the rest of the stack has something to talk to.

Run from the project root (parent of this package):
    uvicorn normalizer.main:app --reload --port 9000
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("normalizer.api")

app = FastAPI(title="Cortex Normalizer", version="0.1.0")


class NormalizeRequest(BaseModel):
    """Permissive request envelope.

    `message` is the one field the previous mock-preliminary contract used; we
    keep it as the only named field and allow any extras so the skeleton can
    accept whatever shape the next problem statement defines without a redeploy.
    """

    model_config = ConfigDict(extra="allow")

    message: str | None = None


class NormalizeResponse(BaseModel):
    """Placeholder response. Replaced by the real contract post-problem-statement."""

    status: str = "placeholder"
    note: str = "normalizer skeleton — problem statement pending"
    echoed: dict[str, Any] | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/normalize", response_model=NormalizeResponse)
def normalize(req: NormalizeRequest) -> NormalizeResponse:
    # Reject empty messages explicitly; everything else is accepted as-is.
    if req.message is not None and not str(req.message).strip():
        log.warning("normalize rejected: empty message")
        raise HTTPException(status_code=422, detail="message must not be empty")

    log.info("POST /normalize message=%r fields=%s",
             (req.message or "")[:160], list(req.model_dump(exclude={"message"}).keys()))
    return NormalizeResponse(echoed=req.model_dump())