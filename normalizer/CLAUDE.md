# CLAUDE.md — normalizer

Generic FastAPI skeleton for the SUST CSE Carnival 2026 — Codex Community
Hackathon preliminary. The Problem Statement is not published yet, so this
module only proves the service is up and accepts requests.

## What this module does

Exposes two endpoints (see `main.py`):

- `GET /health` -> `{"status":"ok"}`
- `POST /normalize` -> accepts any JSON (optional `message`), returns a
  placeholder `{"status":"placeholder","note":"…","echoed":{…}}`.

No classification, no LLM, no env vars read yet. All of that gets added back
once the problem statement locks the contract.

## Commands

```bash
pip install -r normalizer/requirements.txt
uvicorn normalizer.main:app --port 9000          # from repo root
curl -s http://127.0.0.1:9000/health
```

## Hard rules (carry forward once the real logic lands)

1. `normalize()` must be total — always return a valid response, never 500
   (after initial input validation).
2. Never ask the customer for PIN/OTP/password/full card number in any
   generated text (rubric safety category, hard requirement).
3. Escalate risky/uncertain cases to human review.

## Out of scope

Backend, deployment, database — owned by the backend team. This module is
imported as a Python package (`normalizer.main:app`) and run as its own
container in the root `docker-compose.yml`.