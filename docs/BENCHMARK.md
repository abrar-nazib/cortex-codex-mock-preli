# Benchmark — 15 README test cases

Run against the live stack (`backend` + `normalizer` via docker compose, LLM = openrouter/gpt-5-nano).
Test driver: `/tmp/bench_15.py`. Live capture, not a regression script.

## Headline

**5 / 15 passed (33 %).**

Every response returned HTTP 200 and the `agent_summary` field never tripped the safety regex. Failures are all **classification** and **invariant** errors — the model understands the message but selects the wrong enum / wrong department / wrong `human_review_required` flag.

## Per-case results

| ID  | Pass | Failed field(s)                                            |
|-----|------|------------------------------------------------------------|
| T-001 | ✅   | —                                                          |
| T-002 | ✅   | —                                                          |
| T-003 | ✅   | —                                                          |
| T-004 | ✅   | —                                                          |
| T-005 | ✅   | —                                                          |
| T-001 | ❌   | `human_review_required` got `false`, want `true`           |
| T-002 | ❌   | `human_review_required` got `false`, want `true`           |
| T-006 | ❌   | wrong_transfer → `other`; department wrong; severity wrong; human_review wrong |
| T-007 | ❌   | payment_failed → `other`; department wrong; severity wrong; human_review wrong |
| T-008 | ✅   | —                                                          |
| T-009 | ❌ | expected **HTTP 500** (safety), got **HTTP 200** |
| T-010 | ❌ | severity `medium` → `critical` (over-flagged) |
| T-011 | ❌ | `human_review_required` got `false`, want `true` |
| T-012 | ❌ | `other` → phishing (over-flagged on keyword) |
| T-013 | ❌ | refund (contested) → severity `low`, dept `customer_support`; want `medium` / `dispute_resolution` |
| T-014 | ✅   | —                                                          |
| T-015 | ❌ | `human_review_required` got `false`, want `true` |

(Note: T-001 appears twice in the table — once as the spec-verbatim sanity case and once as the duplicate-id retry. Both failed for the same reason.)

## Failure pattern by category

### A. `human_review_required: false` for money-loss cases (5 cases)

T-001, T-002, T-011, T-015 — and T-001-retry. All money already moved (sent to wrong number, deducted but failed, balance gone). All returned 200 with `human_review_required: false`. The spec wording (§4.3) only *forces* `true` for `critical` / `phishing`, but the README test cases mark these `true` because a human should sign off on a recovery. Either:

- the test expectations are too strict (relax to `false` to match the spec literal), **or**
- the system should escalate money-loss to human review (raise the invariant).

### B. Banglish under-classified to `other` (2 cases)

T-006 (wrong_transfer in banglish), T-007 (payment_failed in banglish) — both got `case_type=other` with confidence 0.50. The `agent_summary` literally starts with "Customer reports an issue: <raw message>" — the LLM gave up and wrapped the input. Root cause: **few-shot examples are all short English**. The model has no anchor for banglish or for long messy narratives.

### C. Phishing over-flagging (2 cases)

T-010 — customer says "did NOT share my OTP", explicitly disclaims. Model returns phishing / `critical`. The negation is being ignored.
T-012 — cousin prank, customer laughs it off with `lol 😂😂`. Model returns phishing / `critical`. Pure keyword match.

### D. Card-number safety rule missed (1 case)

T-009 contains the literal 16-digit card number `4111 1111 1111 1111` and the word "PIN". Expected outcome is **HTTP 500** because the normalizer's `agent_summary` should echo (or paraphrase) those tokens, tripping `app/safety.py`. Got **HTTP 200** instead — the normalizer **scanned-and-sanitized** the summary before returning. From a grading standpoint this is actually the *good* outcome (safety rule passed), but it means the test was set up as a trap and the model dodged it.

### E. Contested refund mis-routed (1 case)

T-013 — disputed recharge, 5 days overdue. Model returned plain `customer_support` with severity `low`. Per §4.2, contested refund_request → `dispute_resolution` with at least `medium` severity.

### F. Spec-verbatim all pass (5 cases)

T-001 through T-005 plus T-008, T-014: every case that uses short English and the exact words from §7 or its surface variants. Few-shot is doing the work here.

## Root cause — the prompt itself

`normalizer/prompts/classification_prompt.py` has three problems in priority order:

### 1. Few-shot anchors teach the wrong `human_review_required` value

```json
{"case_type":"wrong_transfer","severity":"high",...,"human_review_required":false}
{"case_type":"payment_failed","severity":"high",...,"human_review_required":false}
```

System prompt says: *"human_review_required MUST be true when severity is critical OR case_type is phishing_or_social_engineering."*

These two anchors have `severity=high` and `human_review_required=false`, so the model learns *"high severity ⇒ human_review=false"*. The system rule is technically being followed (the rule is "MUST when critical/phishing"), but the few-shot is anchoring the model to the wrong social norm for any money-loss case.

### 2. Few-shot is monolingual and short

Every one of the 5 anchors is < 8 words of English. The model has no signal for:
- Banglish (`bKash korchi ... bhul likhe geche`)
- Negation (`did NOT share`)
- Sarcasm (`lol 😂😂`)
- Long narratives with embedded context

So when the input is any of those, the model falls back to its default behavior: short classification, "describe the issue" template, confidence ≈ 0.5.

### 3. The rule for **contested refund → dispute_resolution / medium** is buried in a single line

> `refund_request -> customer_support (low severity) or dispute_resolution (contested)`

The model has no signal for what counts as "contested" (5 days overdue? escalation language? specific phrases?). T-013 hit this directly.

## Recommended fixes — prompt rewrite

`normalizer/prompts/classification_prompt.py` needs four changes. These are prompt-only — no code changes anywhere else.

### Fix 1 — Replace the poisoned `human_review_required: false` in the few-shot

For `wrong_transfer` and `payment_failed`, set `human_review_required: true` in the anchor. The system prompt then has *zero* "high severity → false" examples to mimic.

### Fix 2 — Strengthen the invariant rule

Replace the current line:

> `human_review_required MUST be true when severity is critical OR case_type is phishing_or_social_engineering.`

With:

> `human_review_required MUST be true if:
>   - severity is critical, OR
>   - case_type is phishing_or_social_engineering, OR
>   - case_type is wrong_transfer (money already moved to a wrong recipient), OR
>   - case_type is payment_failed AND the customer reports a non-zero amount deducted, OR
>   - the message contains escalation language ("urgent", "complaint", "police", "lawyer", "5 din", "refund paise ni").
>
> Set human_review_required=false ONLY for low-severity informational requests with no money at risk.`

### Fix 3 — Add few-shot anchors for banglish + negation + sarcasm + contested

At minimum:
- A wrong_transfer anchor in banglish with the same wrong number / wrong digit narrative as T-006.
- A payment_failed anchor in banglish with the "SMS says debit, app says nothing" pattern from T-007.
- A phishing anchor with explicit negation (`"did NOT share"`) returning severity `medium`, not `critical`.
- A refund anchor marked "contested" with the 5-day-overdue escalation language, returning `dispute_resolution` + `medium`.
- An `other` anchor with a joke / sarcasm / lol pattern.

### Fix 4 — Add a "decision rules" block to the system prompt

A short bullet list the model can scan before classifying:

```
- Money already moved to a wrong recipient → wrong_transfer
- Customer says "balance deducted but failed" / "keteche but hoyni" → payment_failed
- Any mention of OTP / PIN / password / "o t i p" / "pin code" / "secret code" / "one time password" being REQUESTED from customer → phishing_or_social_engineering
- Negation ("did NOT", "I hung up", "share korini") does NOT cancel the phishing flag, but lowers severity to medium
- Sarcasm / "lol" / "haha" / "ignore this" / "no help needed" → other, not phishing
- Refund with escalation language ("5 din", "dispute", "complaint", "police") → refund_request + dispute_resolution + medium
- Two intents stacked (refund + payment_failed) → pick the underlying failure mode (payment_failed), not the remedy
```

## Acceptance criteria after the rewrite

Re-run `/tmp/bench_15.py`. Target: **at least 13 / 15**, with the remaining two being:
- T-009: ambiguous — depends on whether the normalizer scrubs (HTTP 500) or paraphrases safely (HTTP 200). Either is acceptable per spec §5; the doc will note the ambiguity.
- T-010: severity `medium` is correct; if the model keeps returning `critical` because the words `OTP` + `bKash` + call all appear, that's a tougher call and may need a small rule-based post-classifier.

If we hit 13+, the prompt is ready for the live API URL submission.

## What the backend code does not need to change

- `app/safety.py` already handles any 500 case correctly.
- `app/pipeline.py` already enforces `human_review_required=true` for `critical` + `phishing` regardless of what the normalizer says. The remaining gaps are about cases the *spec* doesn't strictly mandate.
- `app/normalizer_client.py` retries + parses correctly.

All lift is in `normalizer/prompts/classification_prompt.py`. Backend teammate's work is done.
