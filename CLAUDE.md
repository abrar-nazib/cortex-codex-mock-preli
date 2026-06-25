# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SUST CSE Carnival 2026 — Codex Community Hackathon (Mock Preliminary Round).
Build a small HTTPS web service that classifies one customer CRM ticket at a time and returns
`case_type`, `severity`, `department`, `agent_summary`, `human_review_required`, `confidence`.

Two required endpoints (publicly reachable, HTTPS, no auth):

- `GET /health` — must respond within 10s
- `POST /sort-ticket` — accept one ticket JSON, return structured JSON within 30s

Submission is a public GitHub repo (with deployment docs) plus a live HTTPS API base URL.
Grader also re-runs the repo locally if no live URL is provided. Form:
`https://forms.gle/eqVNc5dzhrwaPipJ8`.

## Architecture (3 services, 3 teammates, 1 repo)

```
frontend  ──HTTPS──▶  backend  ──HTTP──▶  normalizer
                       (FastAPI)         (separate teammate)
                       SQLite
```

- `frontend/` — teammate-owned. Talks to backend only.
- `backend/` — **this team owns it**. FastAPI service. Public HTTPS entrypoint.
- `normalizer/` — teammate-owned. Separate process, exposes HTTP.

### Backend responsibilities (us)

1. Accept the public CRM payload on `POST /sort-ticket`.
2. Persist the ticket by `ticket_id` (SQLite, primary key).
3. Forward the **full** ticket schema to normalizer over HTTP and wait for normalized JSON.
4. Merge normalized fields into our base model (which already carries every field needed to
   answer the grader). Backend should be answerable even if normalizer returns a partial payload.
5. Apply server-side **safety filter** on `agent_summary` — must never request PIN, OTP,
   password, or full card number. If hit, fail that case.
6. Return the final response JSON within 30s.

### Inter-service contract

Backend → Normalizer: `POST <NORMALIZER_URL>/normalize` with the same full CRM schema.

Normalizer → Backend: JSON with at least the grader fields. Backend treats the normalizer's
response as untrusted input (JSON parse + schema validate + retry on 5xx/timeout).

Default ports for local dev:

| Service     | Host:port       |
|-------------|-----------------|
| backend     | `127.0.0.1:8000` |
| normalizer  | `127.0.0.1:9000` |
| frontend    | `127.0.0.1:5173` (Vite default) |

Override via env vars `BACKEND_HOST`, `BACKEND_PORT`, `NORMALIZER_URL`.

## Required JSON shapes

Request (`POST /sort-ticket`):
```json
{
  "ticket_id": "T-001",
  "channel": "app",
  "locale": "en",
  "message": "..."
}
```

Response:
```json
{
  "ticket_id": "T-001",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "...",
  "human_review_required": true,
  "confidence": 0.85
}
```

Enums are locked:

- `case_type`: `wrong_transfer`, `payment_failed`, `refund_request`,
  `phishing_or_social_engineering`, `other`
- `severity`: `low`, `medium`, `high`, `critical`
- `department`: `customer_support`, `dispute_resolution`, `payments_ops`, `fraud_risk`

`human_review_required = true` is mandatory for `severity == critical` and for
`case_type == phishing_or_social_engineering`.

## Safety rule (hard fail)

`agent_summary` must NOT contain any pattern asking for PIN, OTP, password, or full card number.
Enforced server-side after merging normalizer output, before returning to caller.

## Runtime constraints (graded)

| Constraint              | Value                            |
|-------------------------|----------------------------------|
| Public HTTPS endpoint   | required                         |
| `/health` SLA           | < 10s                            |
| `/sort-ticket` SLA      | < 30s                            |
| GPU                     | not allowed                      |
| Secrets in repo         | not allowed — use env vars       |
| LLM usage               | allowed but optional (rules OK)  |

## Local dev commands

Setup (one time):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # set NORMALIZER_URL=http://127.0.0.1:9000
```

Run backend (dev, auto-reload):
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Run a single test:
```bash
cd backend
pytest tests/test_<file>.py::test_<name> -q
```

Smoke test against running backend:
```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/sort-ticket \
  -H 'content-type: application/json' \
  -d '{"ticket_id":"T-001","channel":"app","locale":"en","message":"I sent 5000 taka to a wrong number this morning, please help me get it back"}'
```

## Coordination rules for this repo

- Work on `main` only. No long-lived branches (this is the round's training exercise for
  shared-repo collaboration).
- Each teammate owns one directory: `frontend/`, `backend/`, `normalizer/`.
- Cross-directory changes: announce in chat before committing, so the owner can review.
- Service-to-service calls are over HTTP only — no shared Python imports across service dirs.
- Schemas live with the backend (it is the public contract surface). If you change a field
  name in the request/response, update `backend/app/schemas.py` and tell the other two
  teammates before merging.

## Files I created for backend

```
backend/
├── pyproject.toml
├── .env.example
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, route wiring
│   ├── config.py            # env loading (NORMALIZER_URL, timeouts)
│   ├── db.py                # SQLAlchemy engine + session
│   ├── models.py            # Ticket ORM model (ticket_id = PK)
│   ├── schemas.py           # Pydantic request/response + enums
│   ├── normalizer_client.py # httpx client with retry + JSON parse
│   ├── safety.py            # PIN/OTP/password/card regex block
│   └── pipeline.py          # receive -> persist -> normalize -> merge -> safety -> respond
└── tests/
    ├── __init__.py
    ├── test_health.py
    ├── test_sort_ticket.py
    ├── test_safety.py
    └── conftest.py
```

## Sample cases (from the spec, for tests)

| # | message                                                | case_type                              | severity  |
|---|--------------------------------------------------------|----------------------------------------|-----------|
| 1 | "I sent 3000 to wrong number"                          | wrong_transfer                         | high      |
| 2 | "Payment failed but balance deducted?"                 | payment_failed                         | high      |
| 3 | "Someone called asking my OTP, is that bKash?"         | phishing_or_social_engineering         | critical  |
| 4 | "Please refund my last transaction, I changed my mind" | refund_request                         | low       |
| 5 | "App crashed when I opened it"                         | other                                  | low       |
