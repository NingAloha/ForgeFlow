from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


StateDict = dict[str, Any]


@dataclass(slots=True)
class AgentContext:
    user_input: str = ""
    states: dict[str, StateDict] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


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
