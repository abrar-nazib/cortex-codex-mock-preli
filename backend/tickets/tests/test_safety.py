"""Safety regex unit tests. Pure functions, no DB."""
from django.test import SimpleTestCase

from tickets.safety import safe_fallback_summary, violates_safety


class SafetyTest(SimpleTestCase):
    def test_pin_request_is_unsafe(self):
        self.assertTrue(violates_safety("Please share your PIN so we can verify your account."))

    def test_otp_request_is_unsafe(self):
        self.assertTrue(violates_safety("Send me the OTP you just received."))

    def test_password_request_is_unsafe(self):
        self.assertTrue(violates_safety("Provide your password to continue."))

    def test_full_card_number_request_is_unsafe(self):
        self.assertTrue(violates_safety(
            "Please share your full card number 4111 1111 1111 1111 so we can verify."
        ))

    def test_what_is_your_pin_is_unsafe(self):
        self.assertTrue(violates_safety("What is your PIN?"))

    def test_normal_summary_is_safe(self):
        self.assertFalse(violates_safety(
            "Customer reports sending 5000 BDT to a wrong number and requests recovery."
        ))

    # --- Bare mentions in non-imperative context must NOT trip the filter -----

    def test_bare_otp_mention_in_scam_description_is_safe(self):
        self.assertFalse(violates_safety(
            "Customer reports a sudden loss of 300,000 BDT after receiving a call "
            "from someone impersonating the bank and asking for an OTP."
        ))

    def test_bare_pin_mention_in_scam_description_is_safe(self):
        self.assertFalse(violates_safety(
            "Customer reports a caller pretended to be from the bank and asked for a PIN."
        ))

    def test_bare_password_mention_in_scam_description_is_safe(self):
        self.assertFalse(violates_safety(
            "Customer received an SMS requesting a password reset link."
        ))

    def test_bare_card_number_mention_is_safe(self):
        self.assertFalse(violates_safety(
            "Customer reports a charge on card 4111 1111 1111 1111 they don't recognize."
        ))

    def test_safe_fallback_summary_mentions_safety(self):
        s = safe_fallback_summary("T-001")
        self.assertIn("T-001", s)
        self.assertIn("PIN", s)
        self.assertIn("OTP", s)