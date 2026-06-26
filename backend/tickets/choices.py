"""Locked enum values (spec §4). Single source of truth for serializers + pipeline."""

CASE_TYPES = (
    "wrong_transfer",
    "payment_failed",
    "refund_request",
    "phishing_or_social_engineering",
    "other",
)

SEVERITIES = ("low", "medium", "high", "critical")

DEPARTMENTS = (
    "customer_support",
    "dispute_resolution",
    "payments_ops",
    "fraud_risk",
)

CHANNELS = ("app", "sms", "call_center", "merchant_portal")

LOCALES = ("bn", "en", "mixed")