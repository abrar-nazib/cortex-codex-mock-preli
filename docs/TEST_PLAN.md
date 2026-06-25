# Test plan — 15 paste-ready requests for `POST /sort-ticket`

This document is the manual test suite for the live `/sort-ticket` endpoint.

Each block is a JSON body you can paste into the Swagger **Try it out → Execute**
box at `/docs#/default/sort_ticket_sort_ticket_post`, or send with `curl`:

```bash
curl -s -X POST http://localhost:38181/sort-ticket \
  -H 'content-type: application/json' \
  -d @<(cat <<'JSON'
{ "ticket_id": "T-001", "channel": "app", "locale": "en",
  "message": "I sent 3000 to wrong number" }
JSON
)
```

On the live VPS use `https://hackathonapi.cortextechnologies.net/sort-ticket`.

## Annotation format

Under every paste-ready JSON block you'll see:

- **Expected** — the right answer per the spec (§4.2 case_type↔department, §7 sample table, §5 safety rule).
- **Why** — one line tying back to the spec.
- **Likely failure** — the mistake a typical LLM-based normalizer will make if it slips.

Messages are deliberately long, messy, and in **banglish** (Bangla written in
Latin letters mixed with English), since that's how a real customer from
Bangladesh actually types.

---

## 1. The five spec sample cases (verbatim)

These are exactly the messages from §7 of the spec. Use them as a sanity
check that the wiring is alive before trying the messy ones.

### T-001 — wrong_transfer (spec verbatim)

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
- **Likely failure**: model returns `human_review_required: false`. Spec §4.3 only *forces* it for `critical`/`phishing`, but for any money-already-sent case a sane bank would route it to human review.

### T-002 — payment_failed (spec verbatim)

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
- **Likely failure**: model picks `wrong_transfer` because "deducted" reads like money leaving the account.

### T-003 — phishing (spec verbatim)

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
- **Likely failure**: model downgrades severity to `high` because the customer sounds calm — phishing must be `critical` per spec.

### T-004 — refund (spec verbatim)

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
- **Likely failure**: model routes to `dispute_resolution` (contested-refund column) instead of `customer_support` because "changed my mind" reads emotional.

### T-005 — other / app crash (spec verbatim)

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
- **Likely failure**: model picks `payment_failed` because "crashed" + "open" sometimes get conflated by weaker classifiers.

---

## 2. Long messy banglish

### T-006 — wrong_transfer in banglish

```json
{
  "ticket_id": "T-006",
  "channel": "app",
  "locale": "mixed",
  "message": "vai ekta problem hoise, ami sokal 10:30 min e 7500 taka bKash korchi apnar merchant number chinta kore, kintu number ekta digit bhul likhe geche mone hoy, mone hoy last 2 digit ulta hoye geche. recipient er naam Shamim, she toh amar cheneo chene na. ami ki kichu korte parbo? please urgent help needed, customer care e call korle keu uthteche na"
}
```
- **Expected**: `wrong_transfer` · `high` · `dispute_resolution` · `human_review_required: true`
- **Why**: "bKash korchi ... bhul likhe geche" = money sent to wrong number. §4.2 routes to `dispute_resolution`.
- **Likely failure**: model classifies as `other` because the word `wrong_transfer` never literally appears — the user described the situation in a story.

### T-007 — payment_failed in banglish with deduction

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
- **Likely failure**: model picks `wrong_transfer` (because money "went" somewhere) or `other`.

### T-008 — phishing with phonetically spelled OTP

```json
{
  "ticket_id": "T-008",
  "channel": "sms",
  "locale": "mixed",
  "message": "vai ekjon lok amake call kore bollo ami bKash theke bollche, tader ekta verification campaign cholche, amar mobile number verify korte hobe, tader pathano link e click kore amar o t i p (one time password) diye dile 5000 taka bonus pabo. ami kichu korini, ektu janaben eta ki scam?"
}
```
- **Expected**: `phishing_or_social_engineering` · `critical` · `fraud_risk` · `human_review_required: true`
- **Why**: classic "verify with OTP for cashback" social-engineering script. §4.2 → `fraud_risk`. Even though the customer didn't share the code, the *attempt* is the reportable event.
- **Likely failure**: model skips because "o t i p" is split with spaces and the literal string `OTP` doesn't appear. Normalizer must understand banglish phonetics.

### T-009 — bare card number + PIN mention (not an agent request)

The customer's message contains the literal 16-digit card number `4111 1111 1111 1111` and the word "PIN". Both are *customer-supplied tokens*, not agent-issued requests — so the safety filter (§5) does **not** trip on them. The expected response is HTTP 200.

```json
{
  "ticket_id": "T-009",
  "channel": "call_center",
  "locale": "bn",
  "message": "ami ekjon customer ke call e help korte gesilam, she bollo tar card number 4111 1111 1111 1111 theke taka keteche but kono purchase hoyni, tumi ki kore dekhba? she toh amake PIN o jiggesh korlo"
}
```
- **Expected**: HTTP **200**. `case_type` may be `other` (no real fraud described) or `phishing_or_social_engineering` (operator asked the caller for a PIN). Severity `low` or `medium`. `human_review_required: true` if phishing.
- **Why**: §5 forbids the *agent* from requesting credentials. A customer quoting a card number back to the operator does not trigger that rule.
- **Likely failure**: backend returns 500 if the normalizer or postprocess treats a bare mention of "PIN" / "card number" as a request — that's the safety regex over-firing. Test confirms the filter is correctly scoped.

### T-010 — phishing with negation (customer did NOT share)

```json
{
  "ticket_id": "T-010",
  "channel": "app",
  "locale": "en",
  "message": "just reporting that a guy called me asking for my OTP and I hung up immediately, did NOT share anything. want to make sure my account is safe, can someone check the recent login activity please? thanks"
}
```
- **Expected**: `phishing_or_social_engineering` · `medium` · `fraud_risk` · `human_review_required: true`
- **Why**: a phishing *attempt* against the customer still routes to fraud risk; severity is not `critical` because no compromise occurred.
- **Likely failure**: model returns `other` because the customer explicitly says "did NOT share" — the negation traps a naive classifier.

### T-011 — two stacked intents (refund of a failed payment)

```json
{
  "ticket_id": "T-011",
  "channel": "app",
  "locale": "en",
  "message": "I tried to pay 2300 taka to a merchant yesterday, payment failed message ashse kintu 2300 taka kete geche amar account theke. I want my refund back immediately. Also please add 500 taka compensation for the hassle, this is not the first time"
}
```
- **Expected**: `payment_failed` · `high` · `payments_ops` · `human_review_required: true`
- **Why**: the underlying event is failed-and-deducted; "refund" here is a remedy, not a voluntary cancellation. §4.2 row says payment_failed → payments_ops, not refund_request → dispute_resolution.
- **Likely failure**: model picks `refund_request` because the word "refund" appears explicitly. The spec resolves the conflict in favor of the underlying failure mode.

### T-012 — sarcasm / joke phishing (must NOT flag)

```json
{
  "ticket_id": "T-012",
  "channel": "sms",
  "locale": "en",
  "message": "lol my cousin just pranked me by pretending to be from bKash and asking for my password over the phone 😂😂 I knew it was him the whole time, just sharing the funny story. no help needed, ignore this"
}
```
- **Expected**: `other` · `low` · `customer_support` · `human_review_required: false`
- **Why**: no fraud event, no money at risk, customer says "no help needed". Even though "password" + "bKash" + phone both appear, the framing is a joke.
- **Likely failure**: model flags as phishing purely on keyword presence.

### T-013 — contested refund (escalation language)

```json
{
  "ticket_id": "T-013",
  "channel": "call_center",
  "locale": "mixed",
  "message": "amar bhai 5 din age ekta recharge korechilo 550 taka, kintu recharge hoyni phone e. ami customer care e call korlam, tara bollo 48 hour wait korte. 5 din hoye gelo, refund paise ni. please dispute kore refund ta den"
}
```
- **Expected**: `refund_request` · `medium` · `dispute_resolution` · `human_review_required: true`
- **Why**: §4.2 row "contested refund_request → dispute_resolution". The dispute framing + 5-day overdue language bumps it out of plain customer_support.
- **Likely failure**: model picks the low-severity `customer_support` row for refund_request because severity rules aren't specified in §4.2.

### T-014 — suspicious-looking but legit request

```json
{
  "ticket_id": "T-014",
  "channel": "app",
  "locale": "en",
  "message": "I want to update my registered phone number on my bKash account. My current number is 01712345678 and I want to change it to 01987654321. Please share the procedure"
}
```
- **Expected**: `other` · `low` · `customer_support` · `human_review_required: false`
- **Why**: routine account change, not phishing. Spec §4.1 `other` catches "anything not covered above".
- **Likely failure**: model flags as phishing because the message contains a phone number + a request to "share" something.

### T-015 — repeated punctuation + caps rage (payment_failed)

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
- **Likely failure**: model truncates the message or picks `wrong_transfer` because "GONE" reads like money moved.

---

## What to look for in every response

- `case_type` ∈ {`wrong_transfer`, `payment_failed`, `refund_request`, `phishing_or_social_engineering`, `other`}
- `severity` ∈ {`low`, `medium`, `high`, `critical`}
- `department` ∈ {`customer_support`, `dispute_resolution`, `payments_ops`, `fraud_risk`}
- `human_review_required == true` for every phishing case and every `critical` severity, plus any money-already-moved case
- `confidence` ∈ [0.0, 1.0]
- `agent_summary` must NEVER contain agent-issued requests for `PIN`, `OTP`, `password`, or full card number. Bare mentions in non-imperative context (e.g. "Customer reports being asked for an OTP") are allowed — the grader cares about whether the agent is asking, not whether the tokens appear. If the summary contains an imperative request like "Please share your PIN", the backend returns **HTTP 500** — that's the spec §5 safety rule working.

**T-009 expects HTTP 200** — the customer's mention of a card number and "PIN" is informational, not an agent-issued request. The safety filter forbids the *agent* from requesting credentials; it does not penalize paraphrasing a customer's report.

---

## Score on the live stack

**15 / 15 passing** as of the most recent deployment. Driver: `/tmp/bench_15.py`
in the team's dev environment.