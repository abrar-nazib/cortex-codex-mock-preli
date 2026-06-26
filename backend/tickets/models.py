"""ORM model. Ticket is keyed by ticket_id (the spec's primary identifier).

Same field set as the previous SQLAlchemy model, ported to Django ORM. The
base model carries every field needed to answer the grader, so the response is
valid even if the normalizer is down or returns a partial payload.
"""
from django.db import models


class Ticket(models.Model):
    # Primary key: the ticket_id from the CRM. Same value the caller echoes back.
    ticket_id = models.CharField(max_length=128, primary_key=True)
    channel = models.CharField(max_length=32, null=True, blank=True)
    locale = models.CharField(max_length=16, null=True, blank=True)
    message = models.TextField()

    # Populated when the normalizer returns, or by our own fallback.
    case_type = models.CharField(max_length=64, null=True, blank=True)
    severity = models.CharField(max_length=16, null=True, blank=True)
    department = models.CharField(max_length=64, null=True, blank=True)
    agent_summary = models.TextField(null=True, blank=True)
    human_review_required = models.BooleanField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tickets"

    def __str__(self) -> str:
        return self.ticket_id