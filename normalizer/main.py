"""FastAPI service — exposes POST /normalize for the Backend to call.

Run from the project root (parent of this package):
    uvicorn normalizer.main:app --reload --port 8001
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .normalizer import normalize
from .schema import NormalizedTicket

app = FastAPI(title="QueueStorm Normalizer", version="1.0.0")


class NormalizeRequest(BaseModel):
    message: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/normalize", response_model=NormalizedTicket)
def normalize_ticket(req: NormalizeRequest) -> NormalizedTicket:
    if not req.message.strip():
        raise HTTPException(status_code=422, detail="message must not be empty")
    return normalize(req.message)
