from __future__ import annotations

from pydantic import Field

from .common import StateModel


class ProjectStructure(StateModel):
    directories: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)


class MvpPlan(StateModel):
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    first_deliverable: str = ""


class SystemDesignState(StateModel):
    project_structure: ProjectStructure = Field(default_factory=ProjectStructure)
    contracts: list[dict[str, object]] = Field(default_factory=list)
    data_flow: list[dict[str, object]] = Field(default_factory=list)
    mvp_plan: MvpPlan = Field(default_factory=MvpPlan)
