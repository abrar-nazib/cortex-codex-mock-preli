"""End-to-end tests against a stubbed normalizer."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

NORMALIZER_URL = "http://normalizer.test"


def _stub_normalize(payload: dict) -> dict:
    msg = payload["message"].lower()
    if "otp" in msg or "pin" in msg or "password" in msg:
        return {
            "case_type": "phishing_or_social_engineering",
            "severity": "critical",
            "department": "fraud_risk",
            "agent_summary": "Suspicious contact reported; do not share codes.",
            "human_review_required": True,
            "confidence": 0.9,
        }
    if "wrong" in msg or "sent" in msg and "wrong" in msg:
        return {
            "case_type": "wrong_transfer",
            "severity": "high",
            "department": "dispute_resolution",
            "agent_summary": "Customer reports sending funds to a wrong number.",
            "human_review_required": True,
            "confidence": 0.8,
        }
    if "failed" in msg or "deducted" in msg:
        return {
            "case_type": "payment_failed",
            "severity": "high",
            "department": "payments_ops",
            "agent_summary": "Payment failed but balance was deducted.",
            "human_review_required": True,
            "confidence": 0.85,
        }
    if "refund" in msg:
        return {
            "case_type": "refund_request",
            "severity": "low",
            "department": "customer_support",
            "agent_summary": "Customer requests a refund.",
            "human_review_required": False,
            "confidence": 0.7,
        }
    return {
        "case_type": "other",
        "severity": "low",
        "department": "customer_support",
        "agent_summary": "General inquiry.",
        "human_review_required": False,
        "confidence": 0.5,
    }


@pytest.fixture
def stub_normalizer():
    with respx.mock(base_url=NORMALIZER_URL) as mock:
        route = respx.post("/normalize").mock(
            side_effect=lambda req: Response(200, json=_stub_normalize(req.content and __import__("json").loads(req.content)))
        )
        yield route


def test_sort_ticket_happy_path(client, stub_normalizer):
    r = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-001",
            "channel": "app",
            "locale": "en",
            "message": "I sent 5000 taka to a wrong number this morning, please help me get it back",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ticket_id"] == "T-001"
    assert body["case_type"] == "wrong_transfer"
    assert body["severity"] == "high"
    assert body["department"] == "dispute_resolution"
    assert body["human_review_required"] is True
    assert 0.0 <= body["confidence"] <= 1.0


def test_phishing_forces_human_review(client, stub_normalizer):
    r = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-003",
            "channel": "sms",
            "locale": "en",
            "message": "Someone called asking my OTP, is that bKash?",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_type"] == "phishing_or_social_engineering"
    assert body["severity"] == "critical"
    assert body["human_review_required"] is True


def test_safety_rule_fails_loud(client, stub_normalizer):
    """If normalizer returns an unsafe summary, /sort-ticket must 500."""
    import respx as _respx
    from httpx import Response

    # Replace the route with a payload that violates safety.
    stub_normalizer.mock(
        return_value=Response(
            200,
            json={
                "case_type": "other",
                "severity": "low",
                "department": "customer_support",
                "agent_summary": "Please share your PIN to continue.",
                "human_review_required": False,
                "confidence": 0.5,
            },
        )
    )

    r = client.post(
        "/sort-ticket",
        json={"ticket_id": "T-099", "message": "App crashed when I opened it"},
    )
    assert r.status_code == 500


def test_missing_message_is_422(client):
    r = client.post("/sort-ticket", json={"ticket_id": "T-100"})
    assert r.status_code == 422


def test_normalizer_failure_falls_back(client):
    """If normalizer is unreachable, backend still returns a valid response (conservative)."""
    import respx as _respx
    from httpx import ConnectError

    with _respx.mock(base_url=NORMALIZER_URL) as mock:
        mock.post("/normalize").mock(side_effect=ConnectError("boom"))
        r = client.post(
            "/sort-ticket",
            json={"ticket_id": "T-200", "message": "App crashed when I opened it"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_type"] == "other"
    assert body["human_review_required"] is True
