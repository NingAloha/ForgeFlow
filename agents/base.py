from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


StateDict = dict[str, Any]


@dataclass(slots=True)
class QuestionOption:
    label: str
    value: str
    hint: str = ""


@dataclass(slots=True)
class QuestionAnswer:
    selected_values: list[str] = field(default_factory=list)
    free_text: str = ""


@dataclass(slots=True)
class QuestionItem:
    id: str
    title: str
    description: str
    response_type: str = "single_select"
    options: list[QuestionOption] = field(default_factory=list)
    allow_free_text: bool = False
    answer: QuestionAnswer | None = None


@dataclass(slots=True)
class QuestionState:
    status: str = "idle"
    stage_name: str = ""
    state_key: str = ""
    blocking: bool = False
    questions: list[QuestionItem] = field(default_factory=list)
    created_by: str = ""
    resolution_summary: str = ""

    @property
    def has_active_questions(self) -> bool:
        return self.status in {"awaiting_user", "answered"} and bool(
            self.questions
        )


@dataclass(slots=True)
class AgentContext:
    user_input: str = ""
    states: dict[str, StateDict] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    question_state: QuestionState | None = None

    def get_state(self, state_key: str) -> StateDict:
        return self.states.get(state_key, {})


@dataclass(slots=True)
class AgentResult:
    agent_name: str
    stage_name: str
    state_key: str
    updated_state: StateDict
    summary: str
    notes: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    handoff_ready: bool = False
    question_state_update: QuestionState | None = None
    requires_user_input: bool = False

    @property
    def blocks_on_questions(self) -> bool:
        return self.requires_user_input and self.question_state_update is not None


class BaseAgent(ABC):
    agent_name: str
    stage_name: str
    state_key: str

    def build_placeholder_summary(self) -> str:
        return (
            f"{self.agent_name} placeholder executed for stage "
            f"{self.stage_name}."
        )

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError
