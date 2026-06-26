# CLAUDE.md — backend

Django + DRF backend for the Cortex mock preliminary. Public HTTPS entrypoint.
PostgreSQL-backed (the `db` service in the root compose).

## Commands

```bash
# Install
pip install -r requirements.txt

# Dev server
python manage.py migrate
python manage.py runserver 127.0.0.1:8000

# Tests (Django test runner — no pytest)
python manage.py test
python manage.py test tickets.tests.test_sort_ticket

# Shell / DB
python manage.py shell
python manage.py dbshell

# Docker
docker compose up -d --build          # from repo root
docker compose exec backend python manage.py test
docker compose logs -f backend
```

## Architecture

Single Django app `tickets`. Request flow in `POST /sort-ticket`:

```
TicketInSerializer (validate)
  → pipeline.classify()
      1. Ticket.objects.update_or_create(ticket_id, raw fields)   [persist]
      2. normalizer_client.call_normalize(payload)  [httpx + tenacity]
      3. merge: coerce enums, fill conservative defaults on failure
      4. _enforce_human_review (critical + phishing → True)
      5. safety.violates_safety(agent_summary) → RuntimeError (→ HTTP 500)
         or safe_fallback_summary
      6. Ticket.objects.update(...) [persist merged]
  → TicketOutSerializer (render)
```

### Files

| File | Responsibility |
|---|---|
| `cortex/settings.py` | env-driven settings; DRF + drf_spectacular; logging config |
| `cortex/urls.py` | root: tickets.urls + `/docs/` + `/api/schema/` |
| `tickets/choices.py` | locked spec enums (case_type, severity, department, channel, locale) |
| `tickets/models.py` | `Ticket` model (PK = `ticket_id`) |
| `tickets/serializers.py` | DRF `TicketInSerializer` / `TicketOutSerializer` / `HealthOutSerializer` |
| `tickets/views.py` | `HealthView`, `SortTicketView` |
| `tickets/pipeline.py` | orchestration (persist → normalize → merge → safety → save) |
| `tickets/normalizer_client.py` | httpx + tenacity retry to `POST {NORMALIZER_URL}/normalize` |
| `tickets/safety.py` | regex block: imperative credential requests are unsafe |
| `tickets/exceptions.py` | validation errors → 422 (matches old FastAPI contract) |
| `tickets/tests/` | Django test runner: `APITestCase` + `SimpleTestCase`, normalizer mocked with `mock.patch` |

## Hard rules (must never break)

1. `agent_summary` must never ask for PIN/OTP/password/card — `tickets/safety.py`.
2. `human_review_required = true` when `severity == critical` OR `case_type == phishing` — enforced in `pipeline._enforce_human_review`.
3. `confidence` clamped to `[0, 1]`.
4. Backend stays answerable even if normalizer is down — `_conservative_defaults` fallback.
5. No Django admin wired (blast-surface reduction). No auth/session middleware.

## Contract

Request `POST /sort-ticket`: `{ticket_id, channel?, locale?, message}`.
Response: `{ticket_id, case_type, severity, department, agent_summary, human_review_required, confidence}`.

The normalizer is a separate FastAPI service at `NORMALIZER_URL` (compose:
`http://normalizer:9000`). Contract: `POST /normalize` with the full ticket
schema, returns the structured fields. Backend treats it as untrusted
(JSON parse + enum coerce + retry on 5xx/timeout).