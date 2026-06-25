# cortex-codex-mock-preli

Mock preliminary submission for SUST CSE Carnival 2026 — Codex Community Hackathon.

## Stack

Three Docker services defined in [`docker-compose.yml`](docker-compose.yml):

- **`backend`** — FastAPI on host `:38181`, talks to the normalizer over HTTP
- **`frontend`** — empty alpine stub (teammate's code not ready yet)
- **`normalizer`** — teammate-owned classifier, host `:38191`, internal `:9000`

Run locally:

```bash
docker compose up -d --build
curl http://localhost:38181/health
# -> {"status":"ok","normalizer_url":"http://normalizer:9000"}
```

Swagger UI for the backend: <http://localhost:38181/docs>

---

## Test requests for `POST /sort-ticket`

Paste each block into the Swagger **Try it out → Execute** box at
<http://localhost:38181/docs#/default/sort_ticket_sort_ticket_post>.

### 1. The five spec sample cases

These are the exact messages from the spec. Each one should return the
`case_type` / `severity` shown in the comment.

```json
{
  "ticket_id": "T-001",
  "channel": "app",
  "locale": "en",
  "message": "I sent 3000 to wrong number"
}
```
```json
{
  "ticket_id": "T-002",
  "channel": "app",
  "locale": "en",
  "message": "Payment failed but balance deducted?"
}
```
```json
{
  "ticket_id": "T-003",
  "channel": "sms",
  "locale": "en",
  "message": "Someone called asking my OTP, is that bKash?"
}
```
```json
{
  "ticket_id": "T-004",
  "channel": "app",
  "locale": "en",
  "message": "Please refund my last transaction, I changed my mind"
}
```
```json
{
  "ticket_id": "T-005",
  "channel": "app",
  "locale": "en",
  "message": "App crashed when I opened it"
}
```

### 2. Channel + locale variants

Same intent, different entry surface. Should hit the same `case_type`.

```json
{
  "ticket_id": "T-006",
  "channel": "call_center",
  "locale": "bn",
  "message": "আমি ভুল নাম্বারে ৫০০০ টাকা পাঠিয়ে ফেলেছি, ফেরত পেতে চাই"
}
```
```json
{
  "ticket_id": "T-007",
  "channel": "merchant_portal",
  "locale": "mixed",
  "message": "payment failed but balance deducted (bKash)"
}
```

### 3. Safety filter — must trigger

`T-008` mentions a PIN pattern in the *message body* (which the normalizer
just echoes into `agent_summary` today). If the normalizer's summary
includes a request for PIN/OTP/password/card, the backend's safety regex
fires and the request returns `500`. This is the spec's hard fail.

```json
{
  "ticket_id": "T-008",
  "channel": "sms",
  "locale": "en",
  "message": "I was told to share my PIN to verify my account"
}
```

### 4. Human-review invariants

Spec: `human_review_required = true` whenever `severity == critical` or
`case_type == phishing_or_social_engineering`. The backend enforces this
even if the normalizer disagrees.

```json
{
  "ticket_id": "T-009",
  "channel": "sms",
  "locale": "en",
  "message": "A caller pretended to be bKash and asked for my one-time password"
}
```
```json
{
  "ticket_id": "T-010",
  "channel": "app",
  "locale": "en",
  "message": "someone sent me a link asking for my password to claim a cashback"
}
```

### 5. Idempotency / upsert

`T-001` again. The DB upserts on `ticket_id` so the second call should
return 200 and overwrite the prior row without crashing.

```json
{
  "ticket_id": "T-001",
  "channel": "app",
  "locale": "en",
  "message": "I sent 3000 to wrong number (second submission of T-001)"
}
```

### 6. Edge cases

```json
{
  "ticket_id": "T-011",
  "channel": "app",
  "locale": "en",
  "message": "refund please"
}
```
```json
{
  "ticket_id": "T-012",
  "channel": "app",
  "locale": "en",
  "message": "Hello, I just wanted to say your new update is great, thanks!"
}
```
```json
{
  "ticket_id": "T-013",
  "channel": "sms",
  "locale": "en",
  "message": "balance deducted but transaction failed twice in a row, please check immediately"
}
```
```json
{
  "ticket_id": "T-014",
  "channel": "merchant_portal",
  "locale": "en",
  "message": "wrong transfer recovery is taking too long, escalating"
}
```
```json
{
  "ticket_id": "T-015",
  "channel": "call_center",
  "locale": "bn",
  "message": "আমার অ্যাপ ক্র্যাশ করছে, একদম ওপেন হচ্ছে না"
}
```

---

## What to look for in each response

- `case_type` ∈ {`wrong_transfer`, `payment_failed`, `refund_request`, `phishing_or_social_engineering`, `other`}
- `severity` ∈ {`low`, `medium`, `high`, `critical`}
- `department` ∈ {`customer_support`, `dispute_resolution`, `payments_ops`, `fraud_risk`}
- `human_review_required == true` for any phishing case or `severity == critical`
- `confidence` ∈ [0.0, 1.0]
- `T-008` is the only one expected to **fail loudly** (HTTP 500) — that's the safety rule tripping. If the normalizer scrubs its summary before returning, `T-008` may return 200; the response would then be the conservative fallback (case_type=`other`, human_review=`true`).