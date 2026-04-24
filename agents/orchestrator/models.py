from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..base import AgentResult


class Stage(StrEnum):
    INIT = "INIT"
    REQUIREMENTS = "REQUIREMENTS"
    SOLUTION = "SOLUTION"
    DESIGN = "DESIGN"
    IMPLEMENTATION = "IMPLEMENTATION"
    TESTING = "TESTING"
    DONE = "DONE"


@dataclass(slots=True)
class StageFlags:
    requirements_ready: bool = False
    solution_ready: bool = False
    design_ready: bool = False
    implementing_active: bool = False
    testing_active: bool = False
    done_ready: bool = False


@dataclass(slots=True)
class TransitionDecision:
    computed_stage: Stage
    final_stage: Stage
    source_stage: Stage | None = None
    forward_target: Stage | None = None
    backflow_target: Stage | None = None
    wait_for_user_input: bool = False
    should_stay: bool = True
    reason: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OrchestrationResult:
    decision: TransitionDecision
    executed_stage: Stage | None = None
    agent_result: AgentResult | None = None
    states_before: dict[str, dict[str, Any]] = field(default_factory=dict)
    states_after: dict[str, dict[str, Any]] = field(default_factory=dict)
    summary: str = ""
