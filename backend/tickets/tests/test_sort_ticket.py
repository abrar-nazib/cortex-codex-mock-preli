"""End-to-end tests for POST /sort-ticket. Normalizer is mocked with patch.

Run with:  docker compose exec backend python manage.py test tickets.tests.test_sort_ticket
"""
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from tickets.normalizer_client import NormalizerError

# Patch target: the call the pipeline actually issues.
NORMALIZER = "tickets.pipeline.normalizer_client.call_normalize"


def _wrong_transfer():
    return {
        "case_type": "wrong_transfer",
        "severity": "high",
        "department": "dispute_resolution",
        "agent_summary": "Customer reports sending funds to a wrong number.",
        "human_review_required": True,
        "confidence": 0.8,
    }


def _phishing():
    return {
        "case_type": "phishing_or_social_engineering",
        "severity": "critical",
        "department": "fraud_risk",
        "agent_summary": "Suspicious contact reported; do not share codes.",
        "human_review_required": True,
        "confidence": 0.9,
    }


class SortTicketTest(APITestCase):
    def test_sort_ticket_happy_path(self):
        with patch(NORMALIZER, return_value=_wrong_transfer()):
            r = self.client.post(
                "/sort-ticket",
                {
                    "ticket_id": "T-001",
                    "channel": "app",
                    "locale": "en",
                    "message": "I sent 5000 taka to a wrong number this morning, please help me get it back",
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        body = r.json()
        self.assertEqual(body["ticket_id"], "T-001")
        self.assertEqual(body["case_type"], "wrong_transfer")
        self.assertEqual(body["severity"], "high")
        self.assertEqual(body["department"], "dispute_resolution")
        self.assertTrue(body["human_review_required"])
        self.assertGreaterEqual(body["confidence"], 0.0)
        self.assertLessEqual(body["confidence"], 1.0)

    def test_phishing_forces_human_review(self):
        with patch(NORMALIZER, return_value=_phishing()):
            r = self.client.post(
                "/sort-ticket",
                {
                    "ticket_id": "T-003",
                    "channel": "sms",
                    "locale": "en",
                    "message": "Someone called asking my OTP, is that bKash?",
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        body = r.json()
        self.assertEqual(body["case_type"], "phishing_or_social_engineering")
        self.assertEqual(body["severity"], "critical")
        self.assertTrue(body["human_review_required"])

    def test_safety_rule_fails_loud(self):
        """If normalizer returns an unsafe summary, /sort-ticket must 500."""
        unsafe = {
            "case_type": "other",
            "severity": "low",
            "department": "customer_support",
            "agent_summary": "Please share your PIN to continue.",
            "human_review_required": False,
            "confidence": 0.5,
        }
        with patch(NORMALIZER, return_value=unsafe):
            r = self.client.post(
                "/sort-ticket",
                {"ticket_id": "T-099", "message": "App crashed when I opened it"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_missing_message_is_422(self):
        r = self.client.post("/sort-ticket", {"ticket_id": "T-100"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_normalizer_failure_falls_back(self):
        """If normalizer is unreachable, backend still returns a valid response."""
        with patch(NORMALIZER, side_effect=NormalizerError("boom")):
            r = self.client.post(
                "/sort-ticket",
                {"ticket_id": "T-200", "message": "App crashed when I opened it"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        body = r.json()
        self.assertEqual(body["case_type"], "other")
        self.assertTrue(body["human_review_required"])