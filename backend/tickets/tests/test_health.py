"""Health endpoint. No DB needed."""
from django.test import SimpleTestCase


class HealthTest(SimpleTestCase):
    def test_health_ok(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("normalizer_url", body)