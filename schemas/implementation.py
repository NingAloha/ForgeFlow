from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic import model_validator

from .common import StateModel


class PatchPreviewMetadataModel(StateModel):
    generated_by: str
    source_artifacts: list[str] = Field(default_factory=list)
    preview_only: bool = True
    target_module: str


class ExecutionPolicyModel(StateModel):
    mutation_enabled: bool = False
    execution_allowed: bool = False
    execution_mode: Literal["preview-only"] = "preview-only"
    requires_approval: bool = True
    blocking_reason: Literal["mutation_disabled"] = "mutation_disabled"
    safe_preview_available: bool = False


def build_execution_policy(
    patch_preview_metadata: PatchPreviewMetadataModel | None,
) -> ExecutionPolicyModel:
    return ExecutionPolicyModel(
        mutation_enabled=False,
        execution_allowed=False,
        execution_mode="preview-only",
        requires_approval=True,
        blocking_reason="mutation_disabled",
        safe_preview_available=patch_preview_metadata is not None,
    )


class ImplementationStatusState(StateModel):
    module_name: str = ""
    implementation_status: str = "not_started"
    files_touched: list[str] = Field(default_factory=list)
    tests_added_or_updated: list[str] = Field(default_factory=list)
    contract_compliance: bool = True
    known_limitations: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    workspace_path: str = ""
    commands_executed: list[str] = Field(default_factory=list)
    artifacts_generated: list[str] = Field(default_factory=list)
    suggested_test_command: list[str] = Field(default_factory=list)
    patch_preview_metadata: PatchPreviewMetadataModel | None = None
    execution_policy: ExecutionPolicyModel = Field(
        default_factory=lambda: build_execution_policy(None)
    )

    @model_validator(mode="after")
    def _sync_execution_policy(self) -> "ImplementationStatusState":
        # Lock invariant:
        # safe_preview_available == (patch_preview_metadata is not None)
        self.execution_policy = build_execution_policy(self.patch_preview_metadata)
        return self
