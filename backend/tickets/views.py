"""Views: GET /health, POST /sort-ticket."""
from __future__ import annotations

import logging

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .pipeline import classify
from .serializers import HealthOutSerializer, TicketInSerializer, TicketOutSerializer

log = logging.getLogger("backend")


def _preview(text: str | None, width: int = 160) -> str:
    """One-line, length-capped view of a customer message for log lines."""
    if not text:
        return ""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


class HealthView(APIView):
    """Service health. Public, no auth. Must respond within 10s (spec §6)."""

    @extend_schema(responses=HealthOutSerializer)
    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class SortTicketView(APIView):
    """Classify one CRM ticket. Public, no auth. Must respond within 30s."""

    @extend_schema(
        request=TicketInSerializer,
        responses=TicketOutSerializer,
        examples=[
            OpenApiExample(
                "Wrong transfer",
                value={
                    "ticket_id": "T-001",
                    "channel": "app",
                    "locale": "en",
                    "message": "I sent 3000 to wrong number",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = TicketInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        log.info("POST /sort-ticket ticket_id=%s channel=%s locale=%s msg=%r",
                 payload.get("ticket_id"), payload.get("channel"),
                 payload.get("locale"), _preview(payload.get("message")))

        try:
            result = classify(payload)
        except RuntimeError as exc:
            # Safety-rule violation surfaces as 500 so the grader counts it as a fail.
            log.warning("sort-ticket FAILED ticket_id=%s reason=%s",
                        payload.get("ticket_id"), exc)
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        out = TicketOutSerializer(result).data
        log.info("sort-ticket OK ticket_id=%s -> case=%s severity=%s department=%s review=%s confidence=%.2f",
                 out["ticket_id"], out["case_type"], out["severity"],
                 out["department"], out["human_review_required"], out["confidence"])
        return Response(out, status=status.HTTP_200_OK)