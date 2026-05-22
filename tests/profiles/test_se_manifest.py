from __future__ import annotations

from agents.orchestrator.models import Stage
from forgeflow.profiles.se.manifest import get_se_manifest


def test_se_manifest_shapes_and_invariants() -> None:
    manifest = get_se_manifest()

    assert manifest.profile_name == "se"
    assert manifest.profile_version == "0.1"

    assert manifest.stages == [
        Stage.INIT,
        Stage.REQUIREMENTS,
        Stage.SOLUTION,
        Stage.DESIGN,
        Stage.IMPLEMENTATION,
        Stage.TESTING,
        Stage.DONE,
    ]

    assert manifest.artifact_keys == [
        "spec",
        "solution",
        "system_design",
        "implementation_status",
        "test_report",
        "question_state",
    ]

    assert manifest.stage_agents == {
        Stage.REQUIREMENTS: "agents.requirements_engineer.agent.RequirementsEngineerAgent",
        Stage.SOLUTION: "agents.solution_engineer.agent.SolutionEngineerAgent",
        Stage.DESIGN: "agents.system_designer.agent.SystemDesignerAgent",
        Stage.IMPLEMENTATION: "agents.implementation_engineer.agent.ImplementationEngineerAgent",
        Stage.TESTING: "agents.test_validation_engineer.agent.TestValidationEngineerAgent",
    }

    assert manifest.stage_produces == {
        Stage.REQUIREMENTS: "spec",
        Stage.SOLUTION: "solution",
        Stage.DESIGN: "system_design",
        Stage.IMPLEMENTATION: "implementation_status",
        Stage.TESTING: "test_report",
    }

    assert manifest.transitions == [
        (Stage.INIT, Stage.REQUIREMENTS),
        (Stage.REQUIREMENTS, Stage.SOLUTION),
        (Stage.SOLUTION, Stage.DESIGN),
        (Stage.DESIGN, Stage.IMPLEMENTATION),
        (Stage.IMPLEMENTATION, Stage.TESTING),
        (Stage.TESTING, Stage.DONE),
    ]

    assert manifest.lineage_dependencies == {
        "spec": [],
        "solution": ["spec"],
        "system_design": ["solution"],
        "implementation_status": ["system_design"],
        "test_report": ["implementation_status"],
        "question_state": [],
    }


def test_se_manifest_internal_consistency() -> None:
    manifest = get_se_manifest()

    assert set(manifest.stage_produces.values()).issubset(set(manifest.artifact_keys))

    # transitions should match the stages chain
    expected = list(zip(manifest.stages, manifest.stages[1:]))
    assert manifest.transitions == expected

    # lineage dependencies should be acyclic and only point upstream in the main chain order
    order = {key: idx for idx, key in enumerate(manifest.artifact_keys)}
    for artifact, deps in manifest.lineage_dependencies.items():
        for dep in deps:
            assert order[dep] < order[artifact]
