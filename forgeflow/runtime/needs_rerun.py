from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


StageName = Literal[
    "REQUIREMENTS",
    "SOLUTION",
    "DESIGN",
    "IMPLEMENTATION",
    "TESTING",
]


ARTIFACT_TO_STAGE: dict[str, StageName] = {
    "spec": "REQUIREMENTS",
    "solution": "SOLUTION",
    "system_design": "DESIGN",
    "implementation_status": "IMPLEMENTATION",
    "test_report": "TESTING",
}


@dataclass(slots=True)
class NeedsRerunResult:
    artifacts: list[str]
    stages: list[str]


def compute_needs_rerun(
    *,
    invalidated_artifacts: list[str],
    pending_review_artifacts: list[str],
    rejected_review_artifacts: list[str],
) -> NeedsRerunResult:
    artifacts: list[str] = []
    for group in (invalidated_artifacts, pending_review_artifacts, rejected_review_artifacts):
        for item in group:
            name = str(item).strip()
            if name and name not in artifacts:
                artifacts.append(name)

    stages: list[str] = []
    for artifact in artifacts:
        stage = ARTIFACT_TO_STAGE.get(artifact)
        if stage and stage not in stages:
            stages.append(stage)

    return NeedsRerunResult(artifacts=sorted(artifacts), stages=stages)

