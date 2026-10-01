"""Local, deterministic review receipts. No editor calls or identity verification."""

from .gates import (
    evaluate_gate,
    new_state,
    record_decision,
    register_candidate,
    request_review,
    suggest_gates,
    validate_state,
)

__all__ = [
    "evaluate_gate", "new_state", "record_decision", "register_candidate",
    "request_review", "suggest_gates", "validate_state",
]
