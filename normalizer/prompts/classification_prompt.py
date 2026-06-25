"""Prompt construction for the classification LLM.

Design goals:
- Force strict JSON output (only the 6 fields).
- Bake the enum rules and the department mapping into the system prompt.
- Few-shot the 5 public sample cases so the model anchors on them.
- Restate the safety rule (never ask for PIN/OTP/password/card).
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are a ticket triage engine for a digital finance company \
(mobile money / wallet). You read ONE customer support message and classify it.

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
- wrong_transfer: money sent to the wrong recipient/number.
- payment_failed: a transaction failed but balance may have been deducted.
- refund_request: customer asks for a refund.
- phishing_or_social_engineering: suspicious call/SMS, or anyone asking for PIN, OTP, password.
- other: anything not covered above (e.g. app crash, general question).

department mapping (follow strictly):
- wrong_transfer            -> dispute_resolution
- payment_failed            -> payments_ops
- phishing_or_social_engineering -> fraud_risk
- refund_request            -> customer_support (low severity) or dispute_resolution (contested)
- other                     -> customer_support

severity guidance:
- phishing_or_social_engineering is almost always critical.
- lost/misdirected money (wrong_transfer) or deducted-but-failed payment is high.
- simple refund or app crash with no money lost is low.

human_review_required MUST be true when severity is critical OR case_type is phishing_or_social_engineering.

SAFETY (critical, graded): the agent_summary must NEVER ask the customer to share \
their PIN, OTP, password, or full card number. Only describe the ticket neutrally.

Output raw JSON only. No markdown fences, no commentary."""


# Few-shot anchors = the 5 public sample cases from the spec.
FEW_SHOT = [
    (
        "I sent 3000 to wrong number",
        '{"case_type":"wrong_transfer","severity":"high","department":"dispute_resolution",'
        '"agent_summary":"Customer reports sending 3000 to the wrong number and needs help recovering it.",'
        '"human_review_required":false,"confidence":0.9}',
    ),
    (
        "Payment failed but balance deducted",
        '{"case_type":"payment_failed","severity":"high","department":"payments_ops",'
        '"agent_summary":"Customer reports a failed payment where the balance was still deducted.",'
        '"human_review_required":false,"confidence":0.9}',
    ),
    (
        "Someone called asking my OTP, is that bKash?",
        '{"case_type":"phishing_or_social_engineering","severity":"critical","department":"fraud_risk",'
        '"agent_summary":"Customer received a suspicious call requesting their OTP and is verifying legitimacy.",'
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
]


def build_messages(message: str) -> list[dict[str, str]]:
    """Build a chat-style message list (system + few-shot + user)."""
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_msg, assistant_json in FEW_SHOT:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_json})
    messages.append({"role": "user", "content": message})
    return messages
