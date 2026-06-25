"""Prompt construction for the classification LLM.

Design goals:
- Force strict JSON output (only the 6 fields).
- Bake the enum rules and the department mapping into the system prompt.
- Few-shot the 5 public sample cases + 5 messy/edge cases so the model
  anchors on the long, real, mixed-language messages that customers send.
- Restate the safety rule (never ask for PIN/OTP/password/card).
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are a ticket triage engine for a digital finance company \
(mobile money / wallet in Bangladesh — bKash, Nagad, Rocket, Upay style). \
You read ONE customer support message, often in banglish (Bangla written in \
Latin letters mixed with English), sometimes long and messy, sometimes \
sarcastic, sometimes negated, and you classify it.

Return ONLY a JSON object with EXACTLY these keys and no others:
{
  "case_type": one of ["wrong_transfer","payment_failed","refund_request","phishing_or_social_engineering","other"],
  "severity": one of ["low","medium","high","critical"],
  "department": one of ["customer_support","dispute_resolution","payments_ops","fraud_risk"],
  "agent_summary": "one or two neutral sentences describing the ticket",
  "human_review_required": true or false,
  "confidence": a float between 0 and 1
}

case_type meaning:
- wrong_transfer: money was SENT to the wrong recipient / wrong number / wrong merchant.
- payment_failed: a transaction failed but balance was deducted (SMS debit, app shows nothing).
- refund_request: customer asks for a refund of an already-completed transaction.
- phishing_or_social_engineering: suspicious call/SMS, or anyone asking the customer for PIN, OTP, password, one-time code, card number, or a "verification" link.
- other: anything not covered above (app crash, account update, balance inquiry, compliment, joke).

department mapping (follow strictly):
- wrong_transfer            -> dispute_resolution
- payment_failed            -> payments_ops
- phishing_or_social_engineering -> fraud_risk
- refund_request (simple, low severity, no escalation) -> customer_support
- refund_request (contested: customer is angry, days overdue, says "dispute", "complaint", "police", "lawyer", "urgent", "5 din", "refund paise ni") -> dispute_resolution
- other                     -> customer_support

severity guidance:
- phishing_or_social_engineering is ALWAYS critical UNLESS the customer explicitly says they did NOT share anything (e.g. "did NOT share", "share korini", "I hung up", "I didn't give"). For those, severity is medium.
- lost or misdirected money (wrong_transfer, payment_failed) -> high.
- contested refund -> medium.
- simple refund, app crash, balance inquiry, compliment, joke -> low.

human_review_required rule (must follow exactly):
- true when severity is critical OR case_type is phishing_or_social_engineering
- OR true when case_type is wrong_transfer (money already moved to a wrong recipient — recovery needs human sign-off)
- OR true when case_type is payment_failed AND the message says balance / taka was deducted (real money at stake)
- OR true when the message contains escalation language: "urgent", "complaint", "police", "lawyer", "5 din", "refund paise ni", "eskalate", "nowww", "FIX IT", "compensation", "legal action"
- false ONLY when the message is a simple low-severity informational request with no money at risk: app crash, balance inquiry, phone-number update, compliment, joke.

DO NOT under-classify because the message is long or in banglish. If the user describes the wrong-transfer / payment-failed situation in their own words, match the case_type from the meaning, not from literal keywords.
DO NOT over-flag as phishing when the user is reporting a joke, sarcasm, or explicitly says they did NOT share anything. Look at intent, not keyword presence.

DECISION RULES (use these as the primary classifier, keywords second):
1. Money already moved to a wrong recipient (wrong number, wrong digit, mistaken recipient, "bhul likhe geche", "ulta hoye geche", "paisa gaye") -> wrong_transfer / high / dispute_resolution / human_review=true.
2. Customer says "balance deducted but failed" / "keteche but hoyni" / "taka kateche kintu app e dekhtechi na" / SMS debit but app no update -> payment_failed / high / payments_ops / human_review=true.
3. Any mention of OTP / PIN / password / "o t i p" / "one time password" / "pin code" / "secret code" / "card number" being REQUESTED from the customer by a caller/SMS/link -> phishing_or_social_engineering. Critical unless the customer explicitly says they did NOT share.
4. Sarcasm / "lol" / "haha" / "joke" / "no help needed" / "ignore this" / "funny story" -> other / low / customer_support / human_review=false.
5. Negation ("did NOT share", "share korini", "I hung up", "I didn't give") DOES NOT cancel the phishing flag, but lowers severity to medium.
6. Refund with escalation language ("5 din", "dispute", "complaint", "police", "lawyer", "refund paise ni") -> refund_request / medium / dispute_resolution / human_review=true.
7. Refund of a failed payment (customer says "payment failed but money deducted" AND "I want my refund back") -> payment_failed (the underlying failure mode), not refund_request.
8. Routine account change (phone update, address, name) -> other / low / customer_support / human_review=false. NOT phishing even if it contains a phone number + the word "share".

SAFETY (critical, graded): the agent_summary must NEVER ask the customer to share \
their PIN, OTP, password, or full card number. If the customer message contains \
those tokens, you MUST paraphrase them in the summary (e.g. "sensitive code" instead \
of "OTP", "card on file" instead of the literal 16 digits). Only describe the \
ticket neutrally.

Output raw JSON only. No markdown fences, no commentary."""


# Few-shot anchors: 5 spec cases + 5 messy/edge cases.
# All human_review_required values are CORRECT per the rules above. Do NOT
# weaken them — the model over-fits to whatever pattern these anchors show.
FEW_SHOT = [
    # ---- 5 spec sample cases (verbatim from the spec §7) -----------------
    (
        "I sent 3000 to wrong number",
        '{"case_type":"wrong_transfer","severity":"high","department":"dispute_resolution",'
        '"agent_summary":"Customer reports sending 3000 to the wrong number and needs help recovering it.",'
        '"human_review_required":true,"confidence":0.9}',
    ),
    (
        "Payment failed but balance deducted",
        '{"case_type":"payment_failed","severity":"high","department":"payments_ops",'
        '"agent_summary":"Customer reports a failed payment where the balance was still deducted.",'
        '"human_review_required":true,"confidence":0.9}',
    ),
    (
        "Someone called asking my OTP, is that bKash?",
        '{"case_type":"phishing_or_social_engineering","severity":"critical","department":"fraud_risk",'
        '"agent_summary":"Customer received a suspicious call requesting a one-time code and is verifying legitimacy.",'
        '"human_review_required":true,"confidence":0.95}',
    ),
    (
        "Please refund my last transaction, I changed my mind",
        '{"case_type":"refund_request","severity":"low","department":"customer_support",'
        '"agent_summary":"Customer requests a refund for their last transaction after changing their mind.",'
        '"human_review_required":false,"confidence":0.88}',
    ),
    (
        "App crashed when I opened it",
        '{"case_type":"other","severity":"low","department":"customer_support",'
        '"agent_summary":"Customer reports the app crashed on launch.",'
        '"human_review_required":false,"confidence":0.85}',
    ),
    # ---- Banglish wrong_transfer (no English keyword "wrong_transfer") ----
    (
        "vai sokal 10:30 min e 7500 taka bKash korchi, number ekta digit bhul likhe geche, recipient amar cheneo chene na, please urgent help",
        '{"case_type":"wrong_transfer","severity":"high","department":"dispute_resolution",'
        '"agent_summary":"Customer reports sending 7500 BDT to an unintended number due to a typo and requests recovery help.",'
        '"human_review_required":true,"confidence":0.82}',
    ),
    # ---- Banglish payment_failed (SMS debit, app no update) --------------
    (
        "merchant panel theke bill pay korlam, system success bollteche, bank statement e 12400 taka kateche, kintu app e balance update hoyni, SMS eseche taka katteche",
        '{"case_type":"payment_failed","severity":"high","department":"payments_ops",'
        '"agent_summary":"Customer reports a merchant payment where 12,400 BDT was debited per SMS but not reflected in the app balance.",'
        '"human_review_required":true,"confidence":0.85}',
    ),
    # ---- Phishing with explicit negation (customer did NOT share) --------
    (
        "just reporting a guy called me asking for my OTP and I hung up immediately, did NOT share anything, want to make sure my account is safe",
        '{"case_type":"phishing_or_social_engineering","severity":"medium","department":"fraud_risk",'
        '"agent_summary":"Customer reports a phishing call attempt; they hung up without sharing credentials and request a login-activity check.",'
        '"human_review_required":true,"confidence":0.8}',
    ),
    # ---- Sarcasm / joke phishing (must NOT flag) --------------------------
    (
        "lol my cousin just pranked me by pretending to be from bKash and asking for my password over the phone 😂😂 I knew it was him the whole time, just sharing the funny story, no help needed",
        '{"case_type":"other","severity":"low","department":"customer_support",'
        '"agent_summary":"Customer reports a joking prank call from a relative; no help required.",'
        '"human_review_required":false,"confidence":0.9}',
    ),
    # ---- Contested refund -> dispute_resolution / medium -----------------
    (
        "amar bhai 5 din age ekta 550 taka recharge korechilo, recharge hoyni, customer care bollo 48 hour wait korte, 5 din hoye gelo refund paise ni, please dispute kore refund den",
        '{"case_type":"refund_request","severity":"medium","department":"dispute_resolution",'
        '"agent_summary":"Customer is escalating an unresolved recharge refund from 5 days ago and requests dispute resolution.",'
        '"human_review_required":true,"confidence":0.82}',
    ),
]


def build_messages(message: str) -> list[dict[str, str]]:
    """Build a chat-style message list (system + few-shot + user)."""
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_msg, assistant_json in FEW_SHOT:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_json})
    messages.append({"role": "user", "content": message})
    return messages
