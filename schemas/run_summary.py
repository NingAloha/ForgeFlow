from __future__ import annotations

from typing import Any, Literal

from .common import StateModel
from .llm_trace import LLMTraceModel


class RunStepModel(StateModel):
    timestamp: str
    input: str
    decision_type: str
    computed_stage: str
    final_stage: str
    executed_stage: str
    summary: str
    llm_trace: LLMTraceModel
    execution_trace: dict[str, Any]
    state_changes: list[str]
    question_state: dict[str, Any]


class RunSummaryModel(StateModel):
    schema_version: Literal["1"]
    run_id: str
    original_request: str
    generated_project_dir: str
    state_dir: str
    latest_summary: str
    latest_final_stage: str
    latest_decision_type: str
    steps: list[RunStepModel]
