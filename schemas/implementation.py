from __future__ import annotations

from pydantic import Field

from .common import StateModel


class ImplementationStatusState(StateModel):
    module_name: str = ""
    implementation_status: str = "not_started"
    files_touched: list[str] = Field(default_factory=list)
    tests_added_or_updated: list[str] = Field(default_factory=list)
    contract_compliance: bool = True
    known_limitations: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
