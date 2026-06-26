# CORTEX — QueueStorm Warmup

**Team CORTEX** submission for the SUST CSE Carnival 2026 — Codex Community
Hackathon, Mock Preliminary Round. A small public HTTPS service that classifies
one customer support ticket at a time into a structured JSON triage record.

- Submission form: <https://forms.gle/eqVNc5dzhrwaPipJ8>
- Repo: <https://github.com/abrar-nazib/cortex-codex-mock-preli>
- Live API base URL: `https://hackathonapi.cortextechnologies.net`

The original task spec is in [`docs/Submission-Warmup_Mock_Preliminary.pdf`](docs/Submission-Warmup_Mock_Preliminary.pdf).

> Frontend was removed — the grader only hits the backend's two endpoints, so a
> client app added deploy surface with no grading value. This repo now ships
> just the backend (Django + DRF + PostgreSQL) and the normalizer (FastAPI).

---

## What the service does

You `POST` one customer message to `/sort-ticket`. You get back:

```json
{
  "ticket_id": "T-001",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports sending 3000 to the wrong number and needs help recovering it.",
  "human_review_required": true,
  "confidence": 0.9
}
```

Two endpoints, both publicly reachable over HTTPS, no auth (§1 of the spec):

| Method | Path           | SLA      | Purpose                                          |
|--------|----------------|----------|--------------------------------------------------|
| GET    | `/health`      | < 10 s   | Service health                                   |
| POST   | `/sort-ticket` | < 30 s   | Classify one customer CRM ticket                 |

Response enums are locked (§4):

- `case_type`: `wrong_transfer` · `payment_failed` · `refund_request` · `phishing_or_social_engineering` · `other`
- `severity`: `low` · `medium` · `high` · `critical`
- `department`: `customer_support` · `dispute_resolution` · `payments_ops` · `fraud_risk`

`human_review_required = true` is mandatory for `severity == critical` and for
`case_type == phishing_or_social_engineering`.

---

## Architecture

Two services + a database, communicating only over HTTP / the compose network.
Each service is owned by a different teammate and lives in its own directory.

```
                public HTTPS
                       │
                       ▼
                  ┌─────────┐
                  │  nginx   │   HTTPS termination (Let's Encrypt)
                  └────┬─────┘
                       │ 127.0.0.1:38181  (loopback only)
                       ▼
              ┌────────────────┐         POST /normalize          ┌──────────────┐
              │    backend     │ ──────────────────────────────▶ │  normalizer  │
              │ Django + DRF  │ ◀────────────────────────────── │  FastAPI     │
              │  + Postgres   │       structured JSON           │  LLM classify│
              └───────┬────────┘                                  └──────────────┘
                      │
                      ▼
                ┌──────────┐
                │ postgres │   compose-internal only (no host port)
                └──────────┘
```

| Service     | Directory     | Public URL (HTTPS)                     | Internal port | Host port       |
|--------------|---------------|----------------------------------------|---------------|-----------------|
| `backend`   | `backend/`    | `https://hackathonapi.cortextechnologies.net` | `8000` (gunicorn) | `127.0.0.1:38181` |
| `normalizer`| `normalizer/` | _internal only — not exposed publicly_       | `9000` (uvicorn)  | _none_          |
| `db`        | postgres image | _internal only — not exposed publicly_      | `5432`            | _none_          |

### Blast surface (intentionally small)

- **Only the backend is reachable from the internet**, through one nginx vhost.
- The backend's host port binds **`127.0.0.1:38181`** (loopback) — only nginx on
  the same VPS can reach it; it is not exposed on the public interface.
- **normalizer and postgres publish no host ports** — they are reachable only
  inside the compose network via service DNS (`normalizer`, `db`).
- **No Django admin** is wired (no admin surface).
- No auth / session / CSRF middleware — the API is stateless JSON, no cookies.

### How a request flows

1. Caller hits `POST https://hackathonapi.cortextechnologies.net/sort-ticket`.
2. `backend` validates the request (`TicketInSerializer`), persists the raw ticket by `ticket_id` (upsert).
3. `backend` calls `POST http://normalizer:9000/normalize` with the full ticket schema, retrying on 5xx / timeout.
4. The normalizer returns `case_type`, `severity`, `department`, `agent_summary`, `human_review_required`, `confidence`.
5. `backend` merges that into its base model (which carries every field needed to answer the grader) and applies the **safety filter** on `agent_summary` (§5). If the agent's summary contains an imperative request for a credential, the call returns **HTTP 500** — the grader auto-fails that case.
6. The merged record is persisted to Postgres and returned to the caller.

The normalizer's classifier is the OpenRouter model `google/gemini-2.5-flash`,
configured via `NORMALIZER_PROVIDER=openrouter` in `normalizer/.env`. If the
LLM call fails for any reason, the normalizer falls back to a deterministic
keyword classifier that handles every spec case correctly.

### Key design rules

- **One repo, two service directories.** Each teammate owns their service. Cross-directory changes are announced in chat before commit.
- **Service-to-service over HTTP only.** No shared Python imports across `backend/` and `normalizer/`.
- **Schemas live in the backend.** The backend is the public contract surface. Field name changes require telling the other teammate before merging. (Now DRF serializers in `backend/tickets/serializers.py`.)
- **Secrets only via env vars.** No `OPENROUTER_API_KEY` or DB credentials committed. `normalizer/.env` is gitignored.
- **No GPU.** CPU-only VPS, `docker compose up` only.

### Project layout

```
cortex-codex-mock-preli/
├── README.md                      ← you are here
├── docker-compose.yml             ← db + backend + normalizer (frontend removed)
├── .github/workflows/cd.yml       ← push-to-main SSH deploy
├── deploy/
│   └── nginx/cortex-codex.conf    ← single vhost (api only; HTTPS termination)
├── backend/                       ← Django + DRF service (this team owns it)
│   ├── README.md / CLAUDE.md
│   ├── Dockerfile / requirements.txt
│   ├── manage.py
│   ├── cortex/                    # Django project (settings, urls, wsgi/asgi)
│   └── tickets/                   # models, serializers, views, pipeline,
│                                 # normalizer_client, safety, tests
├── normalizer/                    ← FastAPI LLM classifier (teammate-owned)
│   └── ...
└── docs/
    ├── TEST_PLAN.md               ← 15 paste-ready test requests + assertions
    ├── BENCHMARK.md               ← prompt-diagnostic writeup
    └── Submission-Warmup_Mock_Preliminary.pdf
```

---

## Running it locally

```bash
# db + backend + normalizer (no frontend anymore)
docker compose up -d --build

# Health probe
curl -s http://localhost:38181/health
# -> {"status":"ok"}

# Classify a ticket
curl -s -X POST http://localhost:38181/sort-ticket \
  -H 'content-type: application/json' \
  -d '{"ticket_id":"T-001","channel":"app","locale":"en",
       "message":"I sent 3000 taka to a wrong number this morning, please help me get it back"}'
```

Swagger UI: <http://localhost:38181/docs/>

### Tests

Django's built-in test runner (no pytest). Against the compose postgres:

```bash
docker compose exec backend python manage.py test
# single file:
docker compose exec backend python manage.py test tickets.tests.test_sort_ticket
```

The tests stub the normalizer with `unittest.mock.patch`, so they're network-free.

---

## Live deployment

The CD workflow (`.github/workflows/cd.yml`) SSHs into the VPS on every push to
`main` and runs `docker compose up -d --build`. Migrations run inside the
backend container's CMD on every start (idempotent), so the deploy is a one-liner.

nginx config + certbot runbook: [`deploy/nginx/cortex-codex.conf`](deploy/nginx/cortex-codex.conf).

---

## Submission

The Google form asks for six fields. The repo provides:

| Field                 | Value                                                           |
|-----------------------|-----------------------------------------------------------------|
| Team name             | **CORTEX**                                                      |
| GitHub repository URL | `https://github.com/abrar-nazib/cortex-codex-mock-preli`        |
| Live API base URL     | `https://hackathonapi.cortextechnologies.net`                   |
| Deployment platform   | Self-hosted VPS via GitHub Actions + docker compose            |
| LLM used              | Yes — `openrouter/google/gemini-2.5-flash` for classification   |
| Known issues          | See [`docs/BENCHMARK.md`](docs/BENCHMARK.md)                   |

If the live URL is unreachable, the grader will fall back to deploying
locally using this repo + `docker compose up -d --build`.

---

## Tests, benchmarks, and known limitations

- **15 spec-shaped requests** with assertions: [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md). Score on the current stack: **15 / 15**.
- **Real-world banking-query stress (BANKING77)**: polite inquiry voice ("Why was I charged twice?") gets classified as `other`. Analysis in [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

---

## Team & ownership

| Directory      | Owner           | Stack                                |
|----------------|-----------------|--------------------------------------|
| `backend/`     | CORTEX backend  | Python · Django · DRF · PostgreSQL   |
| `normalizer/`  | CORTEX normalizer | Python · FastAPI · Pydantic · OpenRouter |

We work on `main` directly — single repo, shared history, no long-lived
branches (the round's training exercise is exactly this collaboration shape).