from app.safety import safe_fallback_summary, violates_safety


def test_pin_request_is_unsafe():
    assert violates_safety("Please share your PIN so we can verify your account.")


def test_otp_request_is_unsafe():
    assert violates_safety("Send me the OTP you just received.")


def test_password_request_is_unsafe():
    assert violates_safety("Provide your password to continue.")


def test_full_card_number_string_is_unsafe():
    assert violates_safety("Your card 4111 1111 1111 1111 was charged.")


def test_normal_summary_is_safe():
    assert not violates_safety(
        "Customer reports sending 5000 BDT to a wrong number and requests recovery."
    )


def test_safe_fallback_summary_mentions_safety():
    s = safe_fallback_summary("T-001")
    assert "T-001" in s
    assert "PIN" in s and "OTP" in s
