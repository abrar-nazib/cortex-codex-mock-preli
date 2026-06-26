"""DRF serializers — the public contract surface for this round.

These replace the previous Pydantic schemas. Field names, types and enum
values are identical (spec §2, §3, §4).
"""
from rest_framework import serializers

from .choices import (
    CASE_TYPES,
    CHANNELS,
    DEPARTMENTS,
    LOCALES,
    SEVERITIES,
)


def _choices(values):
    return [(v, v) for v in values]


class TicketInSerializer(serializers.Serializer):
    """Inbound CRM ticket from the public API."""

    ticket_id = serializers.CharField(min_length=1, max_length=128)
    channel = serializers.ChoiceField(
        choices=_choices(CHANNELS), required=False, allow_null=True
    )
    locale = serializers.ChoiceField(
        choices=_choices(LOCALES), required=False, allow_null=True
    )
    message = serializers.CharField(min_length=1)


class TicketOutSerializer(serializers.Serializer):
    """Final response sent back to the caller."""

    ticket_id = serializers.CharField()
    case_type = serializers.ChoiceField(choices=_choices(CASE_TYPES))
    severity = serializers.ChoiceField(choices=_choices(SEVERITIES))
    department = serializers.ChoiceField(choices=_choices(DEPARTMENTS))
    agent_summary = serializers.CharField()
    human_review_required = serializers.BooleanField()
    confidence = serializers.FloatField(min_value=0.0, max_value=1.0)


class HealthOutSerializer(serializers.Serializer):
    status = serializers.CharField()
    normalizer_url = serializers.CharField()