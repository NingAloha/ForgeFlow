from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import OrchestrationResult
from schemas.run_summary import RunStepModel, RunSummaryModel


class RunManifestWriter:
    def __init__(
        self,
        runs_dir: Path,
        run_id: str,
        generated_project_dir: Path,
        state_dir: str,
    ) -> None:
        self.runs_dir = runs_dir
        self.run_id = run_id
        self.generated_project_dir = generated_project_dir
        self.state_dir = state_dir
        self._run_steps: list[RunStepModel] = []

    def append_step(
        self,
        result: OrchestrationResult,
        step_input: str,
        original_request: str,
    ) -> RunSummaryModel:
        step_model = RunStepModel(
            timestamp=datetime.now(timezone.utc).isoformat(),
            input=step_input,
            decision_type=result.diagnostic.get("decision_type", ""),
            computed_stage=result.diagnostic.get("stages", {}).get("computed", ""),
            final_stage=result.diagnostic.get("stages", {}).get("final", ""),
            executed_stage=result.diagnostic.get("stages", {}).get("executed", ""),
            summary=result.summary,
            llm_trace=result.diagnostic.get("llm_trace", {}),
            execution_trace=result.diagnostic.get("execution_trace", {}),
            state_changes=result.diagnostic.get("state_changes", []),
            question_state=result.diagnostic.get("question_state", {}),
        )
        self._run_steps.append(step_model)
        return RunSummaryModel(
            schema_version="1",
            run_id=self.run_id,
            original_request=original_request,
            generated_project_dir=str(self.generated_project_dir),
            state_dir=self.state_dir,
            latest_summary=result.summary,
            latest_final_stage=result.diagnostic.get("stages", {}).get("final", ""),
            latest_decision_type=result.diagnostic.get("decision_type", ""),
            steps=self._run_steps,
        )

    def write(self, summary: RunSummaryModel) -> None:
        normalized_manifest = summary.model_dump(mode="python")
        path = self.runs_dir / "summary.json"
        path.write_text(
            json.dumps(normalized_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
