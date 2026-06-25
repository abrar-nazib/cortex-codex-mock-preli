"""Tests for the Normalizer.

These run against the deterministic fallback (NORMALIZER_PROVIDER unset ->
"rules"), so they are network-free and deterministic — exactly what CI and
the grader's sample cases need.
"""
import pytest

from normalizer import normalize
from normalizer.postprocess import scrub_summary
from normalizer.schema import CaseType, Department, Severity

# Spec §7 public sample cases: (message, expected_case_type, expected_severity)
SAMPLE_CASES = [
    ("I sent 3000 to wrong number", CaseType.WRONG_TRANSFER, Severity.HIGH),
    ("Payment failed but balance deducted", CaseType.PAYMENT_FAILED, Severity.HIGH),
    (
        "Someone called asking my OTP, is that bKash?",
        CaseType.PHISHING,
        Severity.CRITICAL,
    ),
    (
        "Please refund my last transaction, I changed my mind",
        CaseType.REFUND_REQUEST,
        Severity.LOW,
    ),
    ("App crashed when I opened it", CaseType.OTHER, Severity.LOW),
]


@pytest.mark.parametrize("message,case_type,severity", SAMPLE_CASES)
def test_public_sample_cases(message, case_type, severity):
    result = normalize(message)
    assert result.case_type == case_type
    assert result.severity == severity


def test_department_mapping():
    assert normalize("sent to wrong number").department == Department.DISPUTE_RESOLUTION
    assert normalize("payment failed deducted").department == Department.PAYMENTS_OPS
    assert normalize("someone asked my otp").department == Department.FRAUD_RISK


def test_human_review_for_phishing_and_critical():
    phishing = normalize("they asked for my pin and otp")
    assert phishing.human_review_required is True
    assert phishing.case_type == CaseType.PHISHING


def test_confidence_in_range():
    for message, *_ in SAMPLE_CASES:
        c = normalize(message).confidence
        assert 0.0 <= c <= 1.0


def test_output_validates_against_schema():
    # model_dump must produce the exact response keys the Backend serves.
    dumped = normalize("App crashed when I opened it").model_dump(mode="json")
    assert set(dumped) == {
        "case_type",
        "severity",
        "department",
        "agent_summary",
        "human_review_required",
        "confidence",
    }


@pytest.mark.parametrize(
    "unsafe",
    [
        "Please share your OTP with us to proceed.",
        "Tell me your PIN so we can verify.",
        "What is your password?",
        "Enter your full card number to continue.",
    ],
)
def test_safety_scrub_removes_credential_requests(unsafe):
    cleaned = scrub_summary(unsafe)
    for term in ("otp", "pin", "password", "card number"):
        assert term not in cleaned.lower() or "withheld" in cleaned.lower()


@pytest.mark.parametrize(
    "safe_bare_mention",
    [
        "Customer reports a sudden loss of 300,000 BDT after receiving a call "
        "from someone impersonating the bank and asking for an OTP.",
        "Customer reports a caller pretended to be from the bank and asked for a PIN.",
        "Customer reports a charge on card 4111 1111 1111 1111 they don't recognize.",
        "Customer reports they were asked for a one-time password over the phone.",
    ],
)
def test_safety_scrub_keeps_bare_mentions(safe_bare_mention):
    """Bare mentions in non-imperative context are not agent requests."""
    assert scrub_summary(safe_bare_mention) == safe_bare_mention.strip()


def test_empty_message_rejected():
    with pytest.raises(Exception):
        normalize("")
