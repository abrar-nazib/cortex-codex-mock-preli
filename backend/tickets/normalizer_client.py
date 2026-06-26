"""HTTP client for the normalizer service.

Contract: POST {NORMALIZER_URL}/normalize with the same full CRM schema.
Returns a dict on success. Treats everything else as a failure worth retrying.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger("tickets.normalizer_client")


class NormalizerError(Exception):
    """Raised when the normalizer can't give us a usable payload in time."""


class _RetryableHTTPError(Exception):
    """Internal signal: status code warrants a retry."""


def _build_retry_decorator() -> Any:
    return retry(
        reraise=True,
        retry=retry_if_exception_type(
            (_RetryableHTTPError, httpx.TimeoutException, httpx.NetworkError)
        ),
        stop=stop_after_attempt(max(1, settings.NORMALIZER_MAX_RETRIES + 1)),
        wait=wait_exponential(
            multiplier=settings.NORMALIZER_RETRY_BACKOFF_S,
            min=settings.NORMALIZER_RETRY_BACKOFF_S,
            max=2.0,
        ),
        before_sleep=before_sleep_log(log, logging.WARNING),
    )


@_build_retry_decorator()
def _post_normalize(url: str, payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    """One HTTP attempt. Raises _RetryableHTTPError on 5xx / network / timeout."""
    try:
        resp = httpx.post(url, json=payload, timeout=timeout_s)
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        # Tenacity will retry on these.
        raise exc

    if 500 <= resp.status_code < 600:
        raise _RetryableHTTPError(f"normalizer {resp.status_code}: {resp.text[:200]}")

    if resp.status_code >= 400:
        # 4xx: do not retry, the caller is wrong.
        raise NormalizerError(f"normalizer {resp.status_code}: {resp.text[:200]}")

    try:
        return resp.json()
    except ValueError as exc:
        raise NormalizerError(f"normalizer returned non-JSON: {resp.text[:200]}") from exc


def call_normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Public entry. Returns the parsed JSON body from the normalizer."""
    url = settings.NORMALIZER_URL.rstrip("/") + "/normalize"
    log.info("-> normalizer POST url=%s ticket_id=%s timeout=%.1fs",
             url, payload.get("ticket_id"), float(settings.NORMALIZER_TIMEOUT_S))
    result = _post_normalize(url, payload, timeout_s=float(settings.NORMALIZER_TIMEOUT_S))
    log.info("<- normalizer 200 ticket_id=%s body=%s",
             payload.get("ticket_id"), result)
    return result