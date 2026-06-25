# CORTEX — QueueStorm Warmup

**Team CORTEX** submission for the SUST CSE Carnival 2026 — Codex Community Hackathon,
Mock Preliminary Round. A small public HTTPS service that classifies one
customer support ticket at a time into a structured JSON triage record.

- Submission form: <https://forms.gle/eqVNc5dzhrwaPipJ8>
- Repo: <https://github.com/abrar-nazib/cortex-codex-mock-preli>
- Live API base URL: _see the submission form response or [DEPLOY.md](deploy/DEPLOY.md)_

The original task spec is in [`docs/Submission-Warmup_Mock_Preliminary.pdf`](docs/Submission-Warmup_Mock_Preliminary.pdf).

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

| Method | Path           | SLA      | Purpose                                              |
|--------|----------------|----------|------------------------------------------------------|
| GET    | `/health`      | < 10 s   | Service health                                       |
| POST   | `/sort-ticket` | < 30 s   | Classify one customer CRM ticket                     |

Response enums are locked (§4):

- `case_type`: `wrong_transfer` · `payment_failed` · `refund_request` · `phishing_or_social_engineering` · `other`
- `severity`: `low` · `medium` · `high` · `critical`
- `department`: `customer_support` · `dispute_resolution` · `payments_ops` · `fraud_risk`

---

## Architecture

Three independently deployed services, communicating only over HTTP. Each is
owned by a different teammate and lives in its own directory under this repo:

```
                public HTTPS
                       │
                       ▼
              ┌────────────────┐
              │    frontend    │   Next.js app, served from
              │                │   hackathon.cortextechnologies.net
              └───────┬────────┘
                      │ HTTPS / JSON
                      ▼
              ┌────────────────┐         POST /normalize          ┌──────────────┐
              │    backend     │ ──────────────────────────────▶ │  normalizer  │
              │                │ ◀────────────────────────────── │              │
              │  FastAPI + DB  │       structured JSON           │  LLM classify│
              └────────────────┘                                  └──────────────┘
                       │
                       ▼
                  SQLite file (named volume)
```

| Service     | Directory     | Public URL (HTTPS)                     | Internal port |
|-------------|---------------|----------------------------------------|---------------|
| `frontend`  | `frontend/`   | `https://hackathon.cortextechnologies.net`    | `3000`         |
| `backend`   | `backend/`    | `https://hackathonapi.cortextechnologies.net` | `8000`         |
| `normalizer`| `normalizer/` | _internal only — not exposed publicly_       | `9000`         |

Host bindings on the VPS use high-numbered ports (`38181`, `38283`, `38191`)
to avoid colliding with other stacks on the shared box.

### How a request flows

1. Caller hits `POST https://hackathonapi.cortextechnologies.net/sort-ticket`.
2. `backend` validates the request, persists the raw ticket by `ticket_id` (upsert).
3. `backend` calls `POST <normalizer>:9000/normalize` with the full ticket schema, retrying on 5xx / timeout.
4. The normalizer returns `case_type`, `severity`, `department`, `agent_summary`, `human_review_required`, `confidence`.
5. `backend` merges that into its base model (which holds every field needed to answer the grader) and applies the **safety filter** on `agent_summary` (§5). If the agent's summary contains an imperative request for a credential, the call returns **HTTP 500** — the grader auto-fails that case.
6. The merged record is persisted and returned to the caller.

The normalizer's classifier is the openrouter model `google/gemini-2.5-flash`,
configured via `NORMALIZER_PROVIDER=openrouter` in `normalizer/.env`. If the
LLM call fails for any reason, the normalizer falls back to a deterministic
keyword classifier that handles every spec case correctly.

### Key design rules

- **One repo, three directories.** Each teammate owns their service. Cross-directory changes are announced in chat before commit.
- **Service-to-service over HTTP only.** No shared Python imports across `frontend/`, `backend/`, `normalizer/`.
- **Schemas live in the backend.** The backend is the public contract surface. Field name changes require telling the other two teammates before merging.
- **Secrets only via env vars.** No `OPENROUTER_API_KEY` or DB credentials in the repo. The mock round's `.env` files contain test secrets that the grader will skip.
- **No GPU.** CPU-only VPS, `docker compose up` only.

### Project layout

```
cortex-codex-mock-preli/
├── README.md                      ← you are here
├── docker-compose.yml             ← backend + normalizer by default;
│                                    `--profile full` adds the frontend
├── .github/workflows/cd.yml       ← push-to-main SSH deploy
├── deploy/
│   ├── DEPLOY.md                  ← runbook for the VPS + the live URL
│   └── nginx/cortex-codex.conf    ← nginx vhost config (HTTPS termination)
├── backend/                       ← FastAPI service (this team owns it)
│   ├── README.md
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/                       ← main, config, db, models, schemas,
│   │                                 normalizer_client, safety, pipeline
│   └── tests/
├── normalizer/                    ← LLM classifier (teammate-owned)
│   ├── README.md
│   ├── CLAUDE.md
│   ├── Dockerfile
│   └── …
├── frontend/                      ← Next.js app (teammate-owned)
│   ├── README.md
│   └── …
└── docs/
    ├── TEST_PLAN.md               ← 15 paste-ready test requests + assertions
    ├── BENCHMARK.md               ← first-round prompt-diagnostic writeup
    ├── BENCHMARK_FINAL.md         ← README + BANKING77 stress benchmark
    └── Submission-Warmup_Mock_Preliminary.pdf
```

---

## Running it locally

```bash
# Backend + normalizer only — fast (a few seconds). Default profile.
docker compose up -d --build

# Add the frontend (opt-in; needs npm registry access)
docker compose --profile full up -d --build

# Health probe
curl -s http://localhost:38181/health
# -> {"status":"ok","normalizer_url":"http://normalizer:9000"}

# Classify a ticket
curl -s -X POST http://localhost:38181/sort-ticket \
  -H 'content-type: application/json' \
  -d '{"ticket_id":"T-001","channel":"app","locale":"en",
       "message":"I sent 3000 taka to a wrong number this morning, please help me get it back"}'
```

Swagger UI: <http://localhost:38181/docs>

### Unit + integration tests

```bash
cd backend
pip install -e ".[dev]"
pytest -q                                # backend unit tests
pytest tests/test_safety.py -q           # safety regex unit tests
```

---

## Live deployment

See [`deploy/DEPLOY.md`](deploy/DEPLOY.md) for the runbook: VPS provisioning,
nginx config, GitHub Actions secrets, and the deploy workflow
(`.github/workflows/cd.yml`) that SSHs into the VPS on every push to `main`
and runs `docker compose up -d --build`.

The deployment is reproducible from this repo alone — the spec says "the
GitHub repository must contain proper deployment replication documentation /
runbook of the solution", so the runbook is the primary deliverable alongside
the live URL.

---

## Submission

The Google form asks for six fields. The repo provides:

| Field                 | Value                                                           |
|-----------------------|-----------------------------------------------------------------|
| Team name             | **CORTEX**                                                      |
| GitHub repository URL | `https://github.com/abrar-nazib/cortex-codex-mock-preli`        |
| Live API base URL     | `https://hackathonapi.cortextechnologies.net` (see `deploy/DEPLOY.md`) |
| Deployment platform   | Self-hosted VPS via GitHub Actions + docker compose             |
| LLM used              | Yes — `openrouter/google/gemini-2.5-flash` for classification   |
| Known issues          | See [`docs/BENCHMARK_FINAL.md`](docs/BENCHMARK_FINAL.md)        |

If the live URL is unreachable, the grader will fall back to deploying
locally using this repo + `deploy/DEPLOY.md`.

---

## Tests, benchmarks, and known limitations

- **15 spec-shaped requests** with assertions: [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md). Score on the current stack: **15 / 15**.
- **Real-world banking-query stress (BANKING77)**: score on the current stack: **1 / 16**. Polite inquiry voice ("Why was I charged twice?") gets classified as `other`. Analysis and three concrete fixes live in [`docs/BENCHMARK_FINAL.md`](docs/BENCHMARK_FINAL.md).
- **First-round prompt diagnostic** when the LLM was silently falling back: [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

We chose to ship on the README-test score (15/15) rather than chase BANKING77
with prompt/rule changes that risk regressing the spec-shaped cases.

---

## Team & ownership

| Directory      | Owner         | Stack                                |
|----------------|---------------|--------------------------------------|
| `backend/`     | CORTEX backend | Python 3.11 · FastAPI · SQLAlchemy · httpx |
| `normalizer/`  | CORTEX normalizer | Python 3.11 · FastAPI · Pydantic · OpenRouter |
| `frontend/`    | CORTEX frontend | Next.js (TypeScript) |

We all work on `main` directly — single repo, shared history, no long-lived
branches (the round's training exercise is exactly this collaboration shape).