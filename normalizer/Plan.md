# Normalizer Module — Plan

> **Role in QueueStorm:** The Normalizer is the AI core. Given one customer
> support message it returns a structured classification that the Backend
> (FastAPI) serves from `POST /sort-ticket`.

---

## 1. Contract

### Input
```json
{ "message": "I sent 5000 taka to a wrong number this morning, please help me get it back" }
```
The Backend may also pass `ticket_id`, `channel`, `locale`. The Normalizer
only needs `message`; it echoes `ticket_id` through untouched.

### Output (the schema we must fill)
```json
{
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports sending 5000 BDT to a wrong number and requests recovery.",
  "human_review_required": true,
  "confidence": 0.85
}
```

---

## 2. Enums (single source of truth → `schema.py`)

**case_type**
| value | meaning |
|---|---|
| `wrong_transfer` | Money sent to wrong recipient |
| `payment_failed` | Transaction failed, balance may be deducted |
| `refund_request` | Customer asking for a refund |
| `phishing_or_social_engineering` | Asks for PIN/OTP/password, suspicious call/SMS |
| `other` | Anything else |

**severity:** `low` · `medium` · `high` · `critical`

**department**
| value | maps from |
|---|---|
| `customer_support` | `other`, low-severity `refund_request` |
| `dispute_resolution` | `wrong_transfer`, contested `refund_request` |
| `payments_ops` | `payment_failed` |
| `fraud_risk` | `phishing_or_social_engineering` |

---

## 3. Hard rules (graded — must not break)

1. **Safety:** `agent_summary` must NEVER ask the customer to share PIN, OTP,
   password, or full card number. → enforced in `postprocess.py`.
2. **human_review_required = true** when `severity == "critical"` OR
   `case_type == "phishing_or_social_engineering"`.
3. **confidence** is a float in `[0, 1]`.
4. Output must always validate against the schema — even when the LLM fails.

---

## 4. Design

```
message ──► normalizer.normalize()
                │
                ├─1─ build prompt        (prompts/classification_prompt.py)
                ├─2─ call LLM provider   (llm/openrouter.py | llm/ollama.py)
                │       └─ on failure / invalid JSON ─► fallback.py (rule-based)
                ├─3─ parse + validate     (schema.py / Pydantic)
                └─4─ postprocess          (postprocess.py)
                          ├─ derive department from case_type
                          ├─ force human_review_required rule
                          ├─ clamp confidence
                          └─ scrub agent_summary (safety)
                ▼
        NormalizedTicket  (guaranteed valid)
```

**Provider abstraction:** `llm/base.py` defines `LLMProvider.complete(prompt)`.
`config.py` picks the provider from env (`NORMALIZER_PROVIDER=openrouter|ollama`).
This lets us swap OpenRouter (cloud) ↔ OLLAMA (local) with one env var, and
keeps GPU-free + secrets-in-env compliant.

**Reliability strategy:** LLM is *primary*, rule-based `fallback.py` is the
safety net. If the LLM times out, errors, or returns unparseable JSON, the
fallback keyword classifier still produces a valid response — so the service
never 500s on the grader.

---

## 5. File responsibilities

| File | Responsibility |
|---|---|
| `schema.py` | Enums + Pydantic `TicketInput` / `NormalizedTicket` models |
| `config.py` | Env-driven settings (provider, model, API key, timeouts) |
| `prompts/classification_prompt.py` | System + user prompt builders, few-shot examples |
| `llm/base.py` | `LLMProvider` abstract interface |
| `llm/openrouter.py` | OpenRouter chat-completions client |
| `llm/ollama.py` | Local OLLAMA client |
| `fallback.py` | Deterministic keyword/rule classifier |
| `postprocess.py` | Department derivation, review-flag rule, confidence clamp, safety scrub |
| `normalizer.py` | Orchestrator: `normalize(message) -> NormalizedTicket` |
| `tests/test_normalizer.py` | 5 public sample cases + safety + fallback tests |

---

## 6. Build order (code one file at a time)

1. `schema.py` — enums + models (foundation everything imports)
2. `config.py` — settings
3. `prompts/classification_prompt.py` — the prompt
4. `llm/base.py` → `llm/openrouter.py` → `llm/ollama.py`
5. `fallback.py` — rule-based net
6. `postprocess.py` — rule enforcement + safety
7. `normalizer.py` — wire it together
8. `tests/test_normalizer.py` — verify against the 5 sample cases

---

## 7. Validation targets (from spec §7)

| message | expected case_type | severity |
|---|---|---|
| I sent 3000 to wrong number | `wrong_transfer` | `high` |
| Payment failed but balance deducted | `payment_failed` | `high` |
| Someone called asking my OTP, is that bKash? | `phishing_or_social_engineering` | `critical` |
| Please refund my last transaction, I changed my mind | `refund_request` | `low` |
| App crashed when I opened it | `other` | `low` |

---

## 8. Out of scope (other team members)

- FastAPI `/health` + `/sort-ticket` endpoints (Backend wraps this module)
- Deployment (Render/Railway/etc.)
- Frontend / DB
