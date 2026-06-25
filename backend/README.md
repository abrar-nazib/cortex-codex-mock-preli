# Backend — Cortex Mock Preliminary

FastAPI service. Public HTTPS entrypoint.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Endpoints

- `GET /health` — health probe
- `POST /sort-ticket` — classify one CRM ticket

## Env

See `.env.example`. `NORMALIZER_URL` is the only one that usually needs changing.
