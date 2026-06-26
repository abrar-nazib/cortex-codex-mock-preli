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

## Architecture (2 services + db, 1 repo)

```
              nginx (HTTPS)
                 │  127.0.0.1:38181
                 ▼
   backend (Django + DRF) ──HTTP──▶ normalizer (FastAPI, teammate-owned)
            │
            ▼
        postgres (compose-internal)
```

- `backend/` — **this team owns it**. Django + DRF + drf_spectacular, backed by PostgreSQL.
  Public HTTPS entrypoint. Frontend was removed (no grading value).
- `normalizer/` — teammate-owned. Separate FastAPI process, exposes HTTP internally.
- `db` — postgres image in `docker-compose.yml`. **Not published** (internal only).

### Blast surface (intentionally small)

- Only the backend is internet-reachable, via one nginx vhost.
- Backend host port binds **`127.0.0.1:38181`** (loopback) — only nginx on the VPS reaches it.
- normalizer + postgres publish **no host ports** — compose DNS only (`http://normalizer:9000`, `db:5432`).
- No Django admin wired. No auth/session/CSRF middleware (stateless JSON, no cookies).

### Backend responsibilities (us)

1. Accept the public CRM payload on `POST /sort-ticket`.
2. Persist the ticket by `ticket_id` (PostgreSQL, primary key — `tickets.Ticket`).
3. Forward the **full** ticket schema to normalizer over HTTP and wait for normalized JSON.
4. Merge normalized fields into our base model (which already carries every field needed to
   answer the grader). Backend should be answerable even if normalizer returns a partial payload.
5. Apply server-side **safety filter** on `agent_summary` — must never request PIN, OTP,
   password, or full card number. If hit, fail that case (HTTP 500).
6. Return the final response JSON within 30s.

### Inter-service contract

Backend → Normalizer: `POST <NORMALIZER_URL>/normalize` with the same full CRM schema.

Normalizer → Backend: JSON with at least the grader fields. Backend treats the normalizer's
response as untrusted input (JSON parse + enum coerce + retry on 5xx/timeout).

Default endpoints for local dev (docker compose):

| Service     | How backend reaches it        |
|-------------|------------------------------|
| backend     | `http://127.0.0.1:38181` (host loopback) |
| normalizer  | `http://normalizer:9000` (compose DNS)  |
| db          | `postgres://cortex:cortex_pw@db:5432/cortex` |

Override via env vars `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `NORMALIZER_URL`, `NORMALIZER_TIMEOUT_S`, etc.

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
Logic in `backend/tickets/safety.py` — matches *imperative* request shapes only; bare mentions
in non-imperative context (describing a scam) are allowed.

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

Docker (db + backend + normalizer, no frontend):
```bash
docker compose up -d --build
curl -s http://localhost:38181/health
```

Backend dev (host, needs a DB — set `DATABASE_URL=sqlite:///./db.sqlite3` for local-without-docker):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL + NORMALIZER_URL
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Tests — **Django test runner, not pytest**. Against the compose postgres:
```bash
docker compose exec backend python manage.py test
# single file:
docker compose exec backend python manage.py test tickets.tests.test_sort_ticket
```
Tests stub the normalizer with `unittest.mock.patch` — network-free.

Smoke test against running backend:
```bash
curl -s http://127.0.0.1:38181/health
curl -s -X POST http://127.0.0.1:38181/sort-ticket \
  -H 'content-type: application/json' \
  -d '{"ticket_id":"T-001","channel":"app","locale":"en","message":"I sent 5000 taka to a wrong number this morning, please help me get it back"}'
```
Swagger UI: `http://localhost:38181/docs/`

## Coordination rules for this repo

- Work on `main` only. No long-lived branches (this is the round's training exercise for
  shared-repo collaboration).
- Each teammate owns one service directory: `backend/`, `normalizer/`. (Frontend removed.)
- Cross-directory changes: announce in chat before committing, so the owner can review.
- Service-to-service calls are over HTTP only — no shared Python imports across service dirs.
- Schemas live with the backend (it is the public contract surface). If you change a field
  name in the request/response, update `backend/tickets/serializers.py` (and `choices.py` for
  enums) and tell the normalizer teammate before merging.

## Backend layout (Django)

```
backend/
├── manage.py
├── requirements.txt
├── Dockerfile
├── cortex/                  # Django project
│   ├── settings.py          # env-driven: DATABASE_URL, ALLOWED_HOSTS, normalizer config, LOGGING
│   ├── urls.py              # tickets.urls + /docs/ (drf_spectacular) + /api/schema/
│   ├── wsgi.py / asgi.py
└── tickets/                 # the one app
    ├── choices.py           # locked spec enums
    ├── models.py            # Ticket ORM model (ticket_id = PK)
    ├── serializers.py       # DRF TicketIn / TicketOut / HealthOut
    ├── views.py             # HealthView, SortTicketView
    ├── pipeline.py          # persist -> normalize -> merge -> safety -> save
    ├── normalizer_client.py # httpx + tenacity retry
    ├── safety.py            # PIN/OTP/password/card regex block
    ├── exceptions.py        # validation errors -> 422
    ├── migrations/
    └── tests/               # Django test runner: APITestCase + SimpleTestCase
```

## Sample cases (from the spec, for tests)

| # | message                                                | case_type                              | severity  |
|---|--------------------------------------------------------|----------------------------------------|-----------|
| 1 | "I sent 3000 to wrong number"                          | wrong_transfer                         | high      |
| 2 | "Payment failed but balance deducted?"                 | payment_failed                         | high      |
| 3 | "Someone called asking my OTP, is that bKash?"         | phishing_or_social_engineering         | critical  |
| 4 | "Please refund my last transaction, I changed my mind" | refund_request                         | low       |
| 5 | "App crashed when I opened it"                         | other                                  | low       |