from __future__ import annotations

from functools import lru_cache
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.orchestrator.models import Stage


class SEProfileManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    profile_name: str
    profile_version: str

    stages: list[Stage] = Field(default_factory=list)
    artifact_keys: list[str] = Field(default_factory=list)

    # Declarative mappings (dotted import paths; no dynamic import in PR1).
    stage_agents: dict[Stage, str] = Field(default_factory=dict)
    stage_produces: dict[Stage, str] = Field(default_factory=dict)

    # Forward chain only in PR1.
    transitions: list[tuple[Stage, Stage]] = Field(default_factory=list)

    # Artifact dependency declaration for lineage.
    lineage_dependencies: dict[str, list[str]] = Field(default_factory=dict)

    _ALLOWED_AGENT_STAGES: ClassVar[set[Stage]] = {
        Stage.REQUIREMENTS,
        Stage.SOLUTION,
        Stage.DESIGN,
        Stage.IMPLEMENTATION,
        Stage.TESTING,
    }
    _ALLOWED_PRODUCE_STAGES: ClassVar[set[Stage]] = _ALLOWED_AGENT_STAGES

    @staticmethod
    def _normalize_key(value: str) -> str:
        return str(value).strip()

    @staticmethod
    def _detect_cycle(deps: dict[str, list[str]]) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> bool:
            if node in visited:
                return False
            if node in visiting:
                return True
            visiting.add(node)
            for parent in deps.get(node, []):
                if visit(parent):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in deps)

    @model_validator(mode="after")
    def _validate_manifest(self) -> "SEProfileManifest":
        if not self.profile_name.strip():
            raise ValueError("profile_name must be non-empty.")
        if not self.profile_version.strip():
            raise ValueError("profile_version must be non-empty.")

        if len(set(self.stages)) != len(self.stages):
            raise ValueError("stages must be unique.")
        if Stage.INIT not in self.stages or Stage.DONE not in self.stages:
            raise ValueError("stages must include INIT and DONE.")

        normalized_artifacts = [self._normalize_key(x) for x in self.artifact_keys]
        if any(not key for key in normalized_artifacts):
            raise ValueError("artifact_keys must not contain empty keys.")
        if len(set(normalized_artifacts)) != len(normalized_artifacts):
            raise ValueError("artifact_keys must be unique.")
        self.artifact_keys = normalized_artifacts

        unknown_agent_stages = set(self.stage_agents) - self._ALLOWED_AGENT_STAGES
        if unknown_agent_stages:
            raise ValueError("stage_agents contains unsupported stages.")
        if any(not str(path).strip() for path in self.stage_agents.values()):
            raise ValueError("stage_agents import paths must be non-empty.")

        unknown_produce_stages = set(self.stage_produces) - self._ALLOWED_PRODUCE_STAGES
        if unknown_produce_stages:
            raise ValueError("stage_produces contains unsupported stages.")
        for produced in self.stage_produces.values():
            produced_key = self._normalize_key(produced)
            if produced_key not in set(self.artifact_keys):
                raise ValueError("stage_produces must reference artifact_keys.")

        # Validate forward transitions form a single linear chain matching `stages`.
        expected_chain = list(self.stages)
        if len(expected_chain) < 2:
            raise ValueError("stages must contain at least INIT and DONE.")
        expected_transitions = list(zip(expected_chain, expected_chain[1:]))
        if self.transitions != expected_transitions:
            raise ValueError("transitions must match the linear forward stage chain.")

        # Validate lineage dependencies.
        allowed_artifacts = set(self.artifact_keys)
        for artifact, depends_on in self.lineage_dependencies.items():
            artifact_key = self._normalize_key(artifact)
            if artifact_key not in allowed_artifacts:
                raise ValueError("lineage_dependencies contains unknown artifact key.")
            if not isinstance(depends_on, list):
                raise ValueError("lineage_dependencies values must be lists.")
            normalized_depends = [self._normalize_key(x) for x in depends_on]
            if any(not x for x in normalized_depends):
                raise ValueError("lineage_dependencies must not contain empty dependency keys.")
            if len(set(normalized_depends)) != len(normalized_depends):
                raise ValueError("lineage_dependencies must not contain duplicate dependencies.")
            if artifact_key in normalized_depends:
                raise ValueError("lineage_dependencies must not contain self-dependencies.")
            if any(dep not in allowed_artifacts for dep in normalized_depends):
                raise ValueError("lineage_dependencies must only reference artifact_keys.")
            self.lineage_dependencies[artifact_key] = normalized_depends

        if self._detect_cycle(self.lineage_dependencies):
            raise ValueError("lineage_dependencies must not contain cycles.")

        return self


@lru_cache(maxsize=1)
def get_se_manifest() -> SEProfileManifest:
    return SEProfileManifest(
        profile_name="se",
        profile_version="0.1",
        stages=[
            Stage.INIT,
            Stage.REQUIREMENTS,
            Stage.SOLUTION,
            Stage.DESIGN,
            Stage.IMPLEMENTATION,
            Stage.TESTING,
            Stage.DONE,
        ],
        artifact_keys=[
            "spec",
            "solution",
            "system_design",
            "implementation_status",
            "test_report",
            "question_state",
        ],
        stage_agents={
            Stage.REQUIREMENTS: "agents.requirements_engineer.agent.RequirementsEngineerAgent",
            Stage.SOLUTION: "agents.solution_engineer.agent.SolutionEngineerAgent",
            Stage.DESIGN: "agents.system_designer.agent.SystemDesignerAgent",
            Stage.IMPLEMENTATION: "agents.implementation_engineer.agent.ImplementationEngineerAgent",
            Stage.TESTING: "agents.test_validation_engineer.agent.TestValidationEngineerAgent",
        },
        stage_produces={
            Stage.REQUIREMENTS: "spec",
            Stage.SOLUTION: "solution",
            Stage.DESIGN: "system_design",
            Stage.IMPLEMENTATION: "implementation_status",
            Stage.TESTING: "test_report",
        },
        transitions=[
            (Stage.INIT, Stage.REQUIREMENTS),
            (Stage.REQUIREMENTS, Stage.SOLUTION),
            (Stage.SOLUTION, Stage.DESIGN),
            (Stage.DESIGN, Stage.IMPLEMENTATION),
            (Stage.IMPLEMENTATION, Stage.TESTING),
            (Stage.TESTING, Stage.DONE),
        ],
        lineage_dependencies={
            "spec": [],
            "solution": ["spec"],
            "system_design": ["solution"],
            "implementation_status": ["system_design"],
            "test_report": ["implementation_status"],
            "question_state": [],
        },
    )
