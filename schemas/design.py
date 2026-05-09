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


class ContractIOModel(StateModel):
    name: str
    description: str
    required: bool


class ContractModel(StateModel):
    name: str
    contract_type: str = ""
    producer: str
    consumers: list[str]
    input: list[ContractIOModel]
    output: list[ContractIOModel]
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    failure_handling: list[str] = Field(default_factory=list)


class DataFlowStepModel(StateModel):
    step: int
    contract_name: str
    from_: str = Field(alias="from")
    to: list[str]
    trigger: str
    notes: str = ""


class SystemDesignState(StateModel):
    project_structure: ProjectStructure = Field(default_factory=ProjectStructure)
    contracts: list[ContractModel] = Field(default_factory=list)
    data_flow: list[DataFlowStepModel] = Field(default_factory=list)
    mvp_plan: MvpPlan = Field(default_factory=MvpPlan)
