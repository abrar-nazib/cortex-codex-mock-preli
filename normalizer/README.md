# Normalizer Module

The AI core of **QueueStorm**: reads one customer support message and returns a
structured classification. The Backend (FastAPI) wraps this in `POST /sort-ticket`.

## Quick start
```bash
pip install -r requirements.txt
cp .env.example .env        # defaults to rules-only mode (no LLM, no network)
```

```python
from Normalizer import normalize

result = normalize("I sent 3000 to wrong number")
print(result.model_dump(mode="json"))
# {'case_type': 'wrong_transfer', 'severity': 'high',
#  'department': 'dispute_resolution', 'agent_summary': '...',
#  'human_review_required': False, 'confidence': 0.7}
```

## Backend integration
```python
from Normalizer import normalize

@app.post("/sort-ticket")
def sort_ticket(req: TicketRequest):
    result = normalize(req.message)
    return {"ticket_id": req.ticket_id, **result.model_dump(mode="json")}
```

## Modes (set `NORMALIZER_PROVIDER`)
| value | behavior |
|---|---|
| `rules` *(default)* | deterministic keyword classifier — no network, always works |
| `openrouter` | cloud LLM (set `OPENROUTER_API_KEY`) |
| `ollama` | local LLM, GPU-free |

The LLM is *primary*; if it fails/times out/returns bad JSON, the rule-based
classifier takes over automatically — the service never errors out.

## Guarantees
- Output always validates against the response schema (`schema.py`).
- `department` is derived deterministically from `case_type`.
- `human_review_required` is forced `true` for critical / phishing.
- `agent_summary` is scrubbed so it never asks for PIN/OTP/password/card (graded safety rule).

## Tests
```bash
python -m pytest Normalizer/tests/ -v
```
Covers all 5 public sample cases, department mapping, the review flag,
confidence range, schema shape, and the safety scrub.

## Files
See [`Plan.md`](./Plan.md) for the full design and per-file responsibilities.
