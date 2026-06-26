# Normalizer — Generic FastAPI Skeleton

Placeholder service for the **SUST CSE Carnival 2026 — Codex Community Hackathon**
preliminary. The official Problem Statement has not been published yet, so this
module is intentionally generic: it stays up, answers `/health`, and accepts any
JSON on `/normalize`. The real classification/reasoning logic replaces the
placeholder here once the problem statement lands.

## Endpoints

| Method | Path        | Body                                | Response                                   |
|--------|-------------|-------------------------------------|--------------------------------------------|
| GET    | `/health`   | —                                   | `{"status":"ok"}`                          |
| POST   | `/normalize`| any JSON (optional `message` field) | `{"status":"placeholder","note":"…","echoed":{…}}` |

`/normalize` rejects an explicitly empty `message` with `422`; everything else
is accepted and echoed back.

## Run

From the repo root (parent of this package):

```bash
pip install -r normalizer/requirements.txt
uvicorn normalizer.main:app --port 9000
```

Docker (built by the root `docker-compose.yml`):

```bash
docker compose up -d --build normalizer
curl -s http://127.0.0.1:9000/health        # only reachable on the compose network
```

## Files

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app: `/health`, `/normalize` (generic skeleton) |
| `requirements.txt` | fastapi, uvicorn, pydantic (LLM deps re-added post-problem-statement) |
| `Dockerfile` | `python:3.11-slim`, runs `uvicorn normalizer.main:app` on `:9000` |
| `.env.example` | placeholder — no env consumed yet |

## What comes next

When the Problem Statement is published: lock the `/normalize` request/response
schema here, add the reasoning provider (rules and/or LLM) behind it, and wire
the safety + escalation guardrails the rubric requires.