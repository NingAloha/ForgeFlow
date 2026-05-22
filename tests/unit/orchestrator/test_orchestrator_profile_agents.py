from __future__ import annotations

from agents.orchestrator.core import Orchestrator
from agents.orchestrator.models import Stage


def test_orchestrator_agents_loaded_from_manifest() -> None:
    orchestrator = Orchestrator()

    assert set(orchestrator.agents.keys()) == {
        Stage.REQUIREMENTS,
        Stage.SOLUTION,
        Stage.DESIGN,
        Stage.IMPLEMENTATION,
        Stage.TESTING,
    }

    manifest = orchestrator.profile_manifest
    for stage, dotted_path in manifest.stage_agents.items():
        agent = orchestrator.agents[stage]
        resolved = f"{agent.__class__.__module__}.{agent.__class__.__name__}"
        assert resolved == dotted_path

