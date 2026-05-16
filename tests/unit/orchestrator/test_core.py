from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from agents.base import AgentResult
from agents.orchestrator import (
    OrchestrationResult,
    Orchestrator,
    Stage,
    TransitionDecision,
)
from agents.orchestrator.run_manifest import RunManifestWriter
from agents.state_manager import StateManager
from schemas.llm_trace import EMPTY_LLM_TRACE, LLMTraceModel
from schemas.run_summary import RunStepModel, RunSummaryModel
from tests.unit.support.orchestrator_fixtures import (
    make_design_ready_states,
    make_done_states,
    make_empty_states,
    make_implementing_states,
    make_requirements_ready_states,
    make_solution_ready_states,
    make_testing_states,
)


class OrchestratorCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = Orchestrator()

    def test_evaluate_forward_transition_reports_expected_targets(self) -> None:
        target, evidence = self.orchestrator.evaluate_forward_transition(
            make_requirements_ready_states(),
            Stage.INIT,
        )
        self.assertEqual(target, Stage.REQUIREMENTS)
        self.assertTrue(evidence)

        target, evidence = self.orchestrator.evaluate_forward_transition(
            make_solution_ready_states(),
            Stage.REQUIREMENTS,
        )
        self.assertEqual(target, Stage.SOLUTION)
        self.assertTrue(evidence)

        target, _ = self.orchestrator.evaluate_forward_transition(
            make_design_ready_states(),
            Stage.SOLUTION,
        )
        self.assertEqual(target, Stage.DESIGN)

        target, _ = self.orchestrator.evaluate_forward_transition(
            make_implementing_states(),
            Stage.DESIGN,
        )
        self.assertEqual(target, Stage.IMPLEMENTATION)

        handoff_states = make_testing_states()
        handoff_states["implementation_status"]["workspace_path"] = ""
        handoff_states["implementation_status"]["suggested_test_command"] = []
        target, _ = self.orchestrator.evaluate_forward_transition(
            handoff_states,
            Stage.IMPLEMENTATION,
        )
        self.assertEqual(target, Stage.TESTING)

        blocked_states = make_testing_states()
        blocked_states["implementation_status"].update(
            {
                "implementation_status": "blocked",
                "contract_compliance": False,
                "blockers": [
                    "code execution mode is not enabled; missing execution safety boundary"
                ],
            }
        )
        target, _ = self.orchestrator.evaluate_forward_transition(
            blocked_states,
            Stage.IMPLEMENTATION,
        )
        self.assertIsNone(target)

        target, _ = self.orchestrator.evaluate_forward_transition(
            make_testing_states(),
            Stage.TESTING,
        )
        self.assertIsNone(target)

        target, _ = self.orchestrator.evaluate_forward_transition(
            make_done_states(),
            Stage.TESTING,
        )
        self.assertEqual(target, Stage.DONE)

    def test_orchestrator_does_not_block_when_run_index_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir) / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            manager = StateManager(state_dir=str(state_dir))
            with patch(
                "agents.orchestrator.core.update_index_on_run_event",
                side_effect=RuntimeError("index write failed"),
            ):
                orchestrator = Orchestrator(state_manager=manager)
                _ = orchestrator.orchestrate("x", original_request="x")

            summary_path = (
                Path(manager.state_dir).parent
                / "runs"
                / orchestrator.run_id
                / "summary.json"
            )
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, dict)
            steps = payload.get("steps", [])
            self.assertIsInstance(steps, list)
            self.assertTrue(steps)
            last = steps[-1]
            self.assertIsInstance(last, dict)
            trace = last.get("execution_trace", {})
            self.assertIsInstance(trace, dict)
            warnings = trace.get("runtime_run_index_warnings", [])
            self.assertIsInstance(warnings, list)
            self.assertTrue(warnings)

    def test_determine_execution_stage_respects_wait_backflow_forward_and_bootstrap(
        self,
    ) -> None:
        self.assertIsNone(
            self.orchestrator.determine_execution_stage(
                TransitionDecision(
                    computed_stage=Stage.REQUIREMENTS,
                    final_stage=Stage.REQUIREMENTS,
                    wait_for_user_input=True,
                    should_stay=True,
                    reason="Waiting for user input.",
                )
            )
        )

        self.assertEqual(
            self.orchestrator.determine_execution_stage(
                TransitionDecision(
                    computed_stage=Stage.TESTING,
                    final_stage=Stage.DESIGN,
                    backflow_target=Stage.DESIGN,
                    should_stay=False,
                    reason="Backflow triggered.",
                )
            ),
            Stage.DESIGN,
        )

        self.assertEqual(
            self.orchestrator.determine_execution_stage(
                TransitionDecision(
                    computed_stage=Stage.REQUIREMENTS,
                    final_stage=Stage.SOLUTION,
                    next_stage_to_execute=Stage.SOLUTION,
                    should_stay=False,
                    reason="Forward transition available.",
                )
            ),
            Stage.SOLUTION,
        )

        self.assertEqual(
            self.orchestrator.determine_execution_stage(
                TransitionDecision(
                    computed_stage=Stage.INIT,
                    final_stage=Stage.INIT,
                    should_stay=True,
                    reason="Stay on current stage.",
                )
            ),
            Stage.REQUIREMENTS,
        )

    def test_build_result_summary_handles_wait_execution_and_noop_paths(self) -> None:
        wait_summary = self.orchestrator.build_result_summary(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.REQUIREMENTS,
                wait_for_user_input=True,
                should_stay=True,
                reason="Waiting for user input.",
            )
        )
        self.assertIn("waiting for user input", wait_summary)

        execution_summary = self.orchestrator.build_result_summary(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.SOLUTION,
                next_stage_to_execute=Stage.SOLUTION,
                should_stay=False,
                reason="Forward transition available.",
            ),
            executed_stage=Stage.SOLUTION,
            agent_result=AgentResult(
                agent_name="Solution Engineer",
                stage_name="SOLUTION",
                state_key="solution",
                updated_state=make_empty_states()["solution"],
                summary="Generated a solution.",
            ),
        )
        self.assertIn("executed SOLUTION via Solution Engineer", execution_summary)

        noop_summary = self.orchestrator.build_result_summary(
            decision=TransitionDecision(
                computed_stage=Stage.DONE,
                final_stage=Stage.DONE,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            executed_stage=None,
        )
        self.assertIn("no agent execution was required", noop_summary)

    def test_write_run_manifest_writes_schema_v1_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            orchestrator = Orchestrator()
            orchestrator.state_manager.state_dir = state_dir
            orchestrator.runs_dir = state_dir.parent / "runs" / orchestrator.run_id
            orchestrator.generated_project_dir = (
                state_dir.parent / "generated" / orchestrator.run_id
            )
            orchestrator.runs_dir.mkdir(parents=True, exist_ok=True)
            orchestrator.generated_project_dir.mkdir(parents=True, exist_ok=True)
            orchestrator.run_manifest = RunManifestWriter(
                runs_dir=orchestrator.runs_dir,
                run_id=orchestrator.run_id,
                generated_project_dir=orchestrator.generated_project_dir,
                state_dir=str(state_dir),
            )

            result = OrchestrationResult(
                decision=TransitionDecision(
                    computed_stage=Stage.REQUIREMENTS,
                    final_stage=Stage.REQUIREMENTS,
                    should_stay=True,
                    reason="Stay on current stage.",
                ),
                diagnostic={
                    "decision_type": "STAY",
                    "stages": {
                        "computed": "REQUIREMENTS",
                        "final": "REQUIREMENTS",
                        "executed": "REQUIREMENTS",
                    },
                    "execution_trace": {},
                    "state_changes": [],
                    "question_state": {"status": "idle"},
                },
                summary="ok",
            )
            summary_model = orchestrator.run_manifest.append_step(
                result,
                step_input="build todo",
                original_request="build todo",
            )
            orchestrator.run_manifest.write(summary_model)
            self.assertIsInstance(orchestrator.run_manifest._run_steps[0], RunStepModel)
            self.assertEqual(
                orchestrator.run_manifest._run_steps[0].llm_trace.model_dump(
                    mode="python"
                ),
                EMPTY_LLM_TRACE.model_dump(mode="python"),
            )

            payload = json.loads(
                (orchestrator.runs_dir / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["schema_version"], "1")
            self.assertEqual(
                set(payload.keys()),
                {
                    "schema_version",
                    "run_id",
                    "original_request",
                    "generated_project_dir",
                    "state_dir",
                    "latest_summary",
                    "latest_final_stage",
                    "latest_decision_type",
                    "steps",
                },
            )
            self.assertEqual(
                set(payload["steps"][0].keys()),
                {
                    "timestamp",
                    "input",
                    "decision_type",
                    "computed_stage",
                    "final_stage",
                    "executed_stage",
                    "summary",
                    "llm_trace",
                    "execution_trace",
                    "state_changes",
                    "question_state",
                },
            )
            model = RunSummaryModel.model_validate(payload)
            self.assertEqual(model.schema_version, "1")

    def test_write_run_manifest_normalizes_valid_dict_llm_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = RunManifestWriter(
                runs_dir=Path(temp_dir),
                run_id="run-1",
                generated_project_dir=Path(temp_dir) / "generated",
                state_dir=str(Path(temp_dir) / "state"),
            )
            result = OrchestrationResult(
                decision=TransitionDecision(
                    computed_stage=Stage.REQUIREMENTS,
                    final_stage=Stage.REQUIREMENTS,
                    should_stay=True,
                    reason="Stay on current stage.",
                ),
                diagnostic={
                    "decision_type": "STAY",
                    "stages": {
                        "computed": "REQUIREMENTS",
                        "final": "REQUIREMENTS",
                        "executed": "REQUIREMENTS",
                    },
                    "llm_trace": {
                        "status": "success",
                        "failure_type": "none",
                        "repair_attempts": 0,
                        "validation_errors": [],
                        "raw_excerpt": '{"ok": true}',
                        "model": "m",
                        "provider": "p",
                        "protocol": "openai",
                        "latency_ms": 1,
                        "error": None,
                    },
                    "execution_trace": {},
                    "state_changes": [],
                    "question_state": {"status": "idle"},
                },
                summary="ok",
            )
            summary = writer.append_step(result, step_input="", original_request="")
            self.assertIsInstance(summary.steps[0].llm_trace, LLMTraceModel)
            self.assertEqual(summary.steps[0].llm_trace.status, "success")

    def test_write_run_manifest_rejects_explicit_empty_dict_llm_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = RunManifestWriter(
                runs_dir=Path(temp_dir),
                run_id="run-1",
                generated_project_dir=Path(temp_dir) / "generated",
                state_dir=str(Path(temp_dir) / "state"),
            )
            result = OrchestrationResult(
                decision=TransitionDecision(
                    computed_stage=Stage.REQUIREMENTS,
                    final_stage=Stage.REQUIREMENTS,
                    should_stay=True,
                    reason="Stay on current stage.",
                ),
                diagnostic={
                    "decision_type": "STAY",
                    "stages": {
                        "computed": "REQUIREMENTS",
                        "final": "REQUIREMENTS",
                        "executed": "REQUIREMENTS",
                    },
                    "llm_trace": {},
                    "execution_trace": {},
                    "state_changes": [],
                    "question_state": {"status": "idle"},
                },
                summary="ok",
            )
            with self.assertRaises(ValidationError):
                writer.append_step(result, step_input="", original_request="")

    def test_record_auto_run_stop_writes_no_progress_metadata_into_run_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            orchestrator = Orchestrator()
            orchestrator.state_manager.state_dir = state_dir
            orchestrator.runs_dir = state_dir.parent / "runs" / orchestrator.run_id
            orchestrator.generated_project_dir = (
                state_dir.parent / "generated" / orchestrator.run_id
            )
            orchestrator.runs_dir.mkdir(parents=True, exist_ok=True)
            orchestrator.generated_project_dir.mkdir(parents=True, exist_ok=True)
            orchestrator.run_manifest = RunManifestWriter(
                runs_dir=orchestrator.runs_dir,
                run_id=orchestrator.run_id,
                generated_project_dir=orchestrator.generated_project_dir,
                state_dir=str(state_dir),
            )

            result = OrchestrationResult(
                decision=TransitionDecision(
                    computed_stage=Stage.IMPLEMENTATION,
                    final_stage=Stage.IMPLEMENTATION,
                    should_stay=True,
                    reason="Stay on current stage.",
                ),
                diagnostic={
                    "decision_type": "STAY",
                    "stages": {
                        "computed": "IMPLEMENTATION",
                        "final": "IMPLEMENTATION",
                        "executed": "IMPLEMENTATION",
                    },
                    "execution_trace": {},
                    "state_changes": [],
                    "question_state": {"status": "idle"},
                },
                summary="stay",
            )
            summary_model = orchestrator.run_manifest.append_step(
                result,
                step_input="build todo",
                original_request="build todo",
            )
            orchestrator.run_manifest.write(summary_model)

            orchestrator.record_auto_run_stop(
                stop_reason="no_progress",
                repeated_stage=Stage.IMPLEMENTATION,
                repeated_decision="STAY",
                step_index=2,
            )

            payload = json.loads(
                (orchestrator.runs_dir / "summary.json").read_text(encoding="utf-8")
            )
            stop_meta = payload["steps"][-1]["execution_trace"]["auto_run_stop"]
            self.assertEqual(stop_meta["stop_reason"], "no_progress")
            self.assertEqual(stop_meta["repeated_stage"], "IMPLEMENTATION")
            self.assertEqual(stop_meta["repeated_decision"], "STAY")
            self.assertEqual(stop_meta["step_index"], 2)


if __name__ == "__main__":
    unittest.main()
