from __future__ import annotations

from pydantic import Field

from .common import StateModel


class SelectedStack(StateModel):
    frontend: str = ""
    backend: str = ""
    database: str = ""
    agent_framework: str = ""
    deployment: str = ""


class SolutionModule(StateModel):
    module: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    covers_requirements: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    tech_note: str = ""


class SolutionState(StateModel):
    selected_stack: SelectedStack = Field(default_factory=SelectedStack)
    module_mapping: list[SolutionModule] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
