from __future__ import annotations

from pydantic import Field

from .common import StateModel


class TestIssue(StateModel):
    title: str = ""
    severity: str = ""
    status: str = ""
    related_modules: list[str] = Field(default_factory=list)
    related_contracts: list[str] = Field(default_factory=list)
    notes: str = ""


class TestReportState(StateModel):
    __test__ = False
    test_scope: str = "integration"
    result: str = "not_run"
    issues: list[TestIssue] = Field(default_factory=list)
