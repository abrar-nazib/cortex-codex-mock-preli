from app.safety import safe_fallback_summary, violates_safety


def test_pin_request_is_unsafe():
    assert violates_safety("Please share your PIN so we can verify your account.")


def test_otp_request_is_unsafe():
    assert violates_safety("Send me the OTP you just received.")


def test_password_request_is_unsafe():
    assert violates_safety("Provide your password to continue.")


def test_full_card_number_request_is_unsafe():
    # Imperative shape: agent is asking the customer to disclose the number.
    assert violates_safety(
        "Please share your full card number 4111 1111 1111 1111 so we can verify."
    )


def test_what_is_your_pin_is_unsafe():
    assert violates_safety("What is your PIN?")


def test_normal_summary_is_safe():
    assert not violates_safety(
        "Customer reports sending 5000 BDT to a wrong number and requests recovery."
    )


# --- Bare mentions in non-imperative context must NOT trip the filter -----
# A summary that describes a scam is informational, not a request to share.
# The grader (§5) cares about the agent asking, not about token presence.

def test_bare_otp_mention_in_scam_description_is_safe():
    assert not violates_safety(
        "Customer reports a sudden loss of 300,000 BDT after receiving a call "
        "from someone impersonating the bank and asking for an OTP."
    )


def test_bare_pin_mention_in_scam_description_is_safe():
    assert not violates_safety(
        "Customer reports a caller pretended to be from the bank and asked for a PIN."
    )


def test_bare_password_mention_in_scam_description_is_safe():
    assert not violates_safety(
        "Customer received an SMS requesting a password reset link."
    )


def test_bare_card_number_mention_is_safe():
    # A non-imperative sentence that contains a card number should NOT trip
    # the filter — the agent is reporting, not asking.
    assert not violates_safety(
        "Customer reports a charge on card 4111 1111 1111 1111 they don't recognize."
    )


def test_safe_fallback_summary_mentions_safety():
    s = safe_fallback_summary("T-001")
    assert "T-001" in s
    assert "PIN" in s and "OTP" in s
