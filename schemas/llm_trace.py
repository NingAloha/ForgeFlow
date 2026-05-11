from __future__ import annotations

from typing import Literal

from .common import StateModel


class LLMTraceModel(StateModel):
    status: Literal[
        "success", "retryable_error", "fatal_error", "needs_user_input", "none"
    ]
    failure_type: str
    repair_attempts: int
    validation_errors: list[str]
    raw_excerpt: str
    model: str
    provider: str
    protocol: str
    latency_ms: int
    error: str | None = None


EMPTY_LLM_TRACE = LLMTraceModel(
    status="none",
    failure_type="none",
    repair_attempts=0,
    validation_errors=[],
    raw_excerpt="",
    model="",
    provider="",
    protocol="",
    latency_ms=0,
    error=None,
)
