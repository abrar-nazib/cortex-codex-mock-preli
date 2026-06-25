# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this module does

The Normalizer is the AI core of QueueStorm. It exposes a single function:

```python
from normalizer import normalize
result: NormalizedTicket = normalize(message)
```

Given a customer support message string, it returns a structured `NormalizedTicket` — always valid, never raises. The Backend's `POST /sort-ticket` wraps this directly.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests (network-free, uses deterministic fallback)
pytest tests/

# Run a single test
pytest tests/test_normalizer.py::test_public_sample_cases

# Run with a specific provider
NORMALIZER_PROVIDER=openrouter OPENROUTER_API_KEY=sk-... pytest tests/

# Try the normalizer interactively
python -c "from normalizer import normalize; print(normalize('sent 3000 to wrong number').model_dump())"
```

## Architecture

```
normalize(message)
    │
    ├─ 1. TicketInput validation (raises on empty message)
    ├─ 2. _classify_with_llm() → LLM provider (openrouter | ollama) or None
    │       └─ on any failure → returns None
    ├─ 3. fallback.classify() if LLM returned None
    └─ 4. postprocess.enforce() applied to EVERY result
```

**Provider selection** is controlled by `NORMALIZER_PROVIDER` env var (`openrouter` | `ollama` | `rules`). `rules` skips the LLM entirely. `config.py` is the single place that reads env.

**LLM path:** `normalizer.py` calls `build_messages()` → provider `.complete()` → `_extract_json()` → `NormalizedTicket.model_validate()`. Any exception at any step silently degrades to the fallback — the service must never 500.

**Fallback** (`fallback.py`): keyword-based classifier. Priority order: phishing > payment_failed > wrong_transfer > refund > other. Passes all 5 public sample cases on its own.

**Postprocess** (`postprocess.py`): re-derives `department` and `human_review_required` from the ticket's own fields, clamps `confidence`, and safety-scrubs `agent_summary`. Applied centrally so the rules hold regardless of where the ticket came from.

## Hard rules (must never break)

1. `agent_summary` must never ask for PIN, OTP, password, or card number — enforced by `scrub_summary()` in `postprocess.py`.
2. `human_review_required = true` when `severity == "critical"` OR `case_type == "phishing_or_social_engineering"`.
3. `confidence` is always clamped to `[0, 1]`.
4. `normalize()` is total — it must always return a valid `NormalizedTicket` and never raise (after initial input validation).

## File responsibilities

| File | Responsibility |
|---|---|
| `schema.py` | Enums (`CaseType`, `Severity`, `Department`) + Pydantic models (`TicketInput`, `NormalizedTicket`) |
| `config.py` | Reads all env vars; exposes `SETTINGS` singleton and `load_settings()` |
| `prompts/classification_prompt.py` | `SYSTEM_PROMPT`, `FEW_SHOT` examples, `build_messages()` |
| `llm/base.py` | `LLMProvider` ABC + `LLMError` |
| `llm/openrouter.py` | OpenRouter (cloud, OpenAI-compatible) |
| `llm/ollama.py` | OLLAMA (local, GPU-free) |
| `fallback.py` | Deterministic keyword classifier — the reliability net |
| `postprocess.py` | Rule enforcement: `department_for()`, `needs_human_review()`, `scrub_summary()`, `enforce()` |
| `normalizer.py` | Orchestrator — only public API entry point |
| `tests/test_normalizer.py` | 5 spec sample cases + department/safety/schema tests |

## Environment setup

Copy `.env.example` to `.env`. For network-free development, `NORMALIZER_PROVIDER=rules` requires no API key. For cloud LLM, set `NORMALIZER_PROVIDER=openrouter` and `OPENROUTER_API_KEY`.

## Test import convention

Tests import using lowercase package name: `from normalizer import normalize`. The package root is `normalizer/` with `__init__.py` — run pytest from the parent directory.

## Out of scope

FastAPI endpoints, deployment, frontend, and database — those are owned by the Backend team. This module is imported directly as a Python package.
