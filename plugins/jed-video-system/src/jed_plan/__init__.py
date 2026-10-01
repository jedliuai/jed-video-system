"""Compile an explicit source-time edit plan into deterministic motion props."""
from .compiler import compile_plan, seconds_to_frame

__all__ = ["compile_plan", "seconds_to_frame"]
