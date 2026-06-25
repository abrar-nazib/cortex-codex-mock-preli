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

### How each test is annotated

Under every paste-ready JSON block you'll see:

- **Expected** — the right answer per the spec (§4.2 case_type↔department, §7 sample table, §5 safety rule).
- **Why** — one line tying back to the spec.
- **Likely failure** — the mistake a typical LLM-based normalizer will make if it slips.

Messages are deliberately long, messy, and in **banglish** (Bangla written in
Latin letters mixed with English), since that's how a real customer from
Bangladesh actually types.

---

### 1. The five spec sample cases (verbatim)

These are exactly the messages from §7 of the spec. Use them as a sanity
check that the wiring is alive before trying the messy ones.

```json
{
  "ticket_id": "T-001",
  "channel": "app",
  "locale": "en",
  "message": "I sent 3000 to wrong number"
}
```
- **Expected**: `wrong_transfer` · `high` · `dispute_resolution` · `human_review_required: true`
- **Why**: §7 sample #1.
- **Likely failure**: model returns `human_review_required: false`. Spec §4.3
  only *forces* it for `critical`/`phishing`, but for any money-already-sent
  case a sane bank would route it to human review.

```json
{
  "ticket_id": "T-002",
  "channel": "app",
  "locale": "en",
  "message": "Payment failed but balance deducted?"
}
```
- **Expected**: `payment_failed` · `high` · `payments_ops` · `human_review_required: true`
- **Why**: §7 sample #2 + §4.2 row.
- **Likely failure**: model picks `wrong_transfer` because "deducted" reads
  like money leaving the account.

```json
{
  "ticket_id": "T-003",
  "channel": "sms",
  "locale": "en",
  "message": "Someone called asking my OTP, is that bKash?"
}
```
- **Expected**: `phishing_or_social_engineering` · `critical` · `fraud_risk` · `human_review_required: true`
- **Why**: §7 sample #3 + §4.2 row.
- **Likely failure**: model downgrades severity to `high` because the
  customer sounds calm — phishing must be `critical` per spec.

```json
{
  "ticket_id": "T-004",
  "channel": "app",
  "locale": "en",
  "message": "Please refund my last transaction, I changed my mind"
}
```
- **Expected**: `refund_request` · `low` · `customer_support` · `human_review_required: false`
- **Why**: §7 sample #4 + §4.2 row for plain refund.
- **Likely failure**: model routes to `dispute_resolution` (contested-refund
  column) instead of `customer_support` because "changed my mind" reads
  emotional.

```json
{
  "ticket_id": "T-005",
  "channel": "app",
  "locale": "en",
  "message": "App crashed when I opened it"
}
```
- **Expected**: `other` · `low` · `customer_support` · `human_review_required: false`
- **Why**: §7 sample #5.
- **Likely failure**: model picks `payment_failed` because "crashed" + "open"
  sometimes get conflated by weaker classifiers.

---

### 2. Long messy banglish — `wrong_transfer`

```json
{
  "ticket_id": "T-006",
  "channel": "app",
  "locale": "mixed",
  "message": "vai ekta problem hoise, ami sokal 10:30 min e 7500 taka bKash korchi apnar merchant number chinta kore, kintu number ekta digit bhul likhe geche mone hoy, mone hoy last 2 digit ulta hoye geche. recipient er naam Shamim, she toh amar cheneo chene na. ami ki kichu korte parbo? please urgent help needed, customer care e call korle keu uthteche na"
}
```
- **Expected**: `wrong_transfer` · `high` · `dispute_resolution` · `human_review_required: true`
- **Why**: "bKash korchi ... bhul likhe geche" = money sent to wrong number.
  §4.2 routes to `dispute_resolution`.
- **Likely failure**: model classifies as `other` because the word
  "wrong_transfer" never literally appears — the user described the
  situation in a story.

### 3. Long messy banglish — `payment_failed` with deduction

```json
{
  "ticket_id": "T-007",
  "channel": "merchant_portal",
  "locale": "mixed",
  "message": "merchant panel theke bill pay korar try korlam, system bollteche transaction successful, kintu amar bank statement e dekhtechi 12,400 taka kateche. app e balance update hoyni, kintu SMS eseche taka katteche. ektu bujhiye bolen vaia ki korbo, ekhon customer dara amake dhamka dicche"
}
```
- **Expected**: `payment_failed` · `high` · `payments_ops` · `human_review_required: true`
- **Why**: SMS says debit, app says nothing happened = failed-but-deducted.
- **Likely failure**: model picks `wrong_transfer` (because money "went"
  somewhere) or `other`.

### 4. Phishing — banglish with phonetically spelled OTP

```json
{
  "ticket_id": "T-008",
  "channel": "sms",
  "locale": "mixed",
  "message": "vai ekjon lok amake call kore bollo ami bKash theke bollche, tader ekta verification campaign cholche, amar mobile number verify korte hobe, tader pathano link e click kore amar o t i p (one time password) diye dile 5000 taka bonus pabo. ami kichu korini, ektu janaben eta ki scam?"
}
```
- **Expected**: `phishing_or_social_engineering` · `critical` · `fraud_risk` · `human_review_required: true`
- **Why**: classic "verify with OTP for cashback" social-engineering script.
  §4.2 → `fraud_risk`. Even though the customer didn't share the code, the
  *attempt* is the reportable event.
- **Likely failure**: model skips because "o t i p" is split with spaces and
  the literal string `OTP` doesn't appear. Normalizer must understand
  banglish phonetics.

### 5. Phishing — full card number inside the message

```json
{
  "ticket_id": "T-009",
  "channel": "call_center",
  "locale": "bn",
  "message": "ami ekjon customer ke call e help korte gesilam, she bollo tar card number 4111 1111 1111 1111 theke taka keteche but kono purchase hoyni, tumi ki kore dekhba? she toh amake PIN o jiggesh korlo"
}
```
- **Expected** (HTTP **500**): `agent_summary` will echo either the 16-digit
  PAN or the word `PIN`, tripping the safety regex in `app/safety.py`.
- **Why**: §5 — "any response that asks the customer to share PIN, OTP,
  password, or full card number will fail that test case automatically."
  Including those tokens anywhere in the summary fails.
- **Likely failure**: normalizer leaks the card number / PIN into
  `agent_summary`. Backend is correct to 500; the failure is in the
  normalizer's postprocess, not in classification.

### 6. Negation — phishing that DIDN'T happen

```json
{
  "ticket_id": "T-010",
  "channel": "app",
  "locale": "en",
  "message": "just reporting that a guy called me asking for my OTP and I hung up immediately, did NOT share anything. want to make sure my account is safe, can someone check the recent login activity please? thanks"
}
```
- **Expected**: `phishing_or_social_engineering` · `medium` · `fraud_risk` · `human_review_required: true`
- **Why**: a phishing *attempt* against the customer still routes to fraud
  risk; severity is not `critical` because no compromise occurred.
- **Likely failure**: model returns `other` because the customer explicitly
  says "did NOT share" — the negation traps a naive classifier.

### 7. Two stacked intents — refund of a failed payment

```json
{
  "ticket_id": "T-011",
  "channel": "app",
  "locale": "en",
  "message": "I tried to pay 2300 taka to a merchant yesterday, payment failed message ashse kintu 2300 taka kete geche amar account theke. I want my refund back immediately. Also please add 500 taka compensation for the hassle, this is not the first time"
}
```
- **Expected**: `payment_failed` · `high` · `payments_ops` · `human_review_required: true`
- **Why**: the underlying event is failed-and-deducted; "refund" here is a
  remedy, not a voluntary cancellation. §4.2 row says payment_failed →
  payments_ops, not refund_request → dispute_resolution.
- **Likely failure**: model picks `refund_request` because the word "refund"
  appears explicitly. The spec resolves the conflict in favor of the
  underlying failure mode.

### 8. Sarcasm / joke phishing

```json
{
  "ticket_id": "T-012",
  "channel": "sms",
  "locale": "en",
  "message": "lol my cousin just pranked me by pretending to be from bKash and asking for my password over the phone 😂😂 I knew it was him the whole time, just sharing the funny story. no help needed, ignore this"
}
```
- **Expected**: `other` · `low` · `customer_support` · `human_review_required: false`
- **Why**: no fraud event, no money at risk, customer says "no help needed".
  Even though "password" + "bKash" + phone both appear, the framing is a
  joke. Spec §5 cares about the agent_summary, not the inbound message.
- **Likely failure**: model flags as phishing purely on keyword presence.

### 9. Refund — contested

```json
{
  "ticket_id": "T-013",
  "channel": "call_center",
  "locale": "mixed",
  "message": "amar bhai 5 din age ekta recharge korechilo 550 taka, kintu recharge hoyni phone e. ami customer care e call korlam, tara bollo 48 hour wait korte. 5 din hoye gelo, refund paise ni. please dispute kore refund ta den"
}
```
- **Expected**: `refund_request` · `medium` · `dispute_resolution` · `human_review_required: true`
- **Why**: §4.2 row "contested refund_request → dispute_resolution". The
  dispute framing bumps it out of plain customer_support.
- **Likely failure**: model picks the low-severity `customer_support` row
  for refund_request because severity rules aren't specified in §4.2.

### 10. Suspicious-looking but legit request

```json
{
  "ticket_id": "T-014",
  "channel": "app",
  "locale": "en",
  "message": "I want to update my registered phone number on my bKash account. My current number is 01712345678 and I want to change it to 01987654321. Please share the procedure"
}
```
- **Expected**: `other` · `low` · `customer_support` · `human_review_required: false`
- **Why**: routine account change, not phishing. Spec §4.1 `other` catches
  "anything not covered above".
- **Likely failure**: model flags as phishing because the message contains
  a phone number + a request to "share" something.

### 11. Repeated punctuation + caps rage

```json
{
  "ticket_id": "T-015",
  "channel": "sms",
  "locale": "en",
  "message": "WHY IS MY BALANCE DEDUCTED BUT TRANSACTION FAILED!!!!! I TRIED 4 TIMES TODAY, ALL 4 TIMES SAME PROBLEM. 8000 TAKA GONE!!! THIS IS RIDICULOUS, FIX IT NOWWWWWWW"
}
```
- **Expected**: `payment_failed` · `high` · `payments_ops` · `human_review_required: true`
- **Why**: explicit "balance deducted but transaction failed" — §4.2 row.
- **Likely failure**: model truncates the message or picks `wrong_transfer`
  because "GONE" reads like money moved.

---

## What to look for in every response

- `case_type` ∈ {`wrong_transfer`, `payment_failed`, `refund_request`, `phishing_or_social_engineering`, `other`}
- `severity` ∈ {`low`, `medium`, `high`, `critical`}
- `department` ∈ {`customer_support`, `dispute_resolution`, `payments_ops`, `fraud_risk`}
- `human_review_required == true` for every phishing case and every `critical` severity
- `confidence` ∈ [0.0, 1.0]
- `agent_summary` must NEVER contain `PIN`, `OTP`, `password`, or a 13–19 digit run. If it does, the backend returns **HTTP 500** — that's the spec §5 safety rule working.

**T-009 is the only one expected to fail loudly** (HTTP 500). If the
normalizer scrubs the card number before returning, `T-009` will return
200 with a sanitized fallback.

---

## What to look for in every response

- `case_type` ∈ {`wrong_transfer`, `payment_failed`, `refund_request`, `phishing_or_social_engineering`, `other`}
- `severity` ∈ {`low`, `medium`, `high`, `critical`}
- `department` ∈ {`customer_support`, `dispute_resolution`, `payments_ops`, `fraud_risk`}
- `human_review_required == true` for every phishing case and every `critical` severity
- `confidence` ∈ [0.0, 1.0]
- `agent_summary` must NEVER contain `PIN`, `OTP`, `password`, or a 13–19 digit run. If it does, the backend returns **HTTP 500** — that's the spec §5 safety rule working.

**T-009 is the only one expected to fail loudly** (HTTP 500). If the
normalizer scrubs the card number before returning, `T-009` will return
200 with a sanitized fallback.