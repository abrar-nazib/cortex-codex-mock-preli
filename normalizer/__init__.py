"""QueueStorm Normalizer — message → structured ticket classification.

    from Normalizer import normalize
    result = normalize("I sent 3000 to wrong number")
    result.model_dump()  # -> the response schema dict
"""
from .normalizer import normalize
from .schema import (
    CaseType,
    Department,
    NormalizedTicket,
    Severity,
    TicketInput,
)

__all__ = [
    "normalize",
    "NormalizedTicket",
    "TicketInput",
    "CaseType",
    "Severity",
    "Department",
]
