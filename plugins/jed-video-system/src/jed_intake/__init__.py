"""Deterministic client intake; no third-party imports or production side effects."""

from .rules import evaluate

__all__ = ["evaluate"]
