from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..base import AgentContext, AgentResult
from ..implementation_engineer import ImplementationEngineerAgent
from ..requirements_engineer import RequirementsEngineerAgent
from ..solution_engineer import SolutionEngineerAgent
from ..state_manager import StateManager
from ..system_designer import SystemDesignerAgent
from ..test_validation_engineer import TestValidationEngineerAgent
from .backflow_evaluator import BackflowEvaluator
from .models import OrchestrationResult, Stage, TransitionDecision
from .question_flow import QuestionFlow
from .run_manifest import RunManifestWriter
from .stage_evaluator import StageEvaluator
from schemas.run_summary import RunSummaryModel
from forgeflow.runtime.events import append_runtime_event
from forgeflow.runtime.lineage import upsert_lineage_entry
from forgeflow.runtime.run_index import update_index_on_run_event


class Orchestrator:
    DISPLAY_ARTIFACT_KEYS = {
        "spec": "spec",
        "solution": "solution",
        "design": "system_design",
        "system_design": "system_design",
        "implementation_status": "implementation_status",
        "test_report": "test_report",
        "question_state": "question_state",
    }

    @staticmethod
    def changed_state_keys(
        states_before: dict[str, dict[str, Any]],
        states_after: dict[str, dict[str, Any]],
    ) -> list[str]:
        changed: list[str] = []
        all_keys = set(states_before) | set(states_after)
        for state_key in sorted(all_keys):
            if states_before.get(state_key) != states_after.get(state_key):
                changed.append(state_key)
        return changed

    @staticmethod
    def _normalize_llm_trace(raw_llm_trace: object) -> dict[str, Any]:
        if hasattr(raw_llm_trace, "model_dump"):
            dumped = raw_llm_trace.model_dump(mode="python")
            return dumped if isinstance(dumped, dict) else {}
        if isinstance(raw_llm_trace, dict):
            return dict(raw_llm_trace)
        return {}

    def __init__(self, state_manager: StateManager | None = None) -> None:
        self.state_manager = state_manager or StateManager()
        state_dir_value = getattr(self.state_manager, "state_dir", None)
        state_dir = (
            Path(state_dir_value)
            if state_dir_value is not None
            else Path.cwd() / ".forgeflow" / "state"
        )
        self.run_id = (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid4().hex[:8]
        )
        self._started_at = datetime.now(timezone.utc)
        self.runs_dir = state_dir.parent / "runs" / self.run_id
        self.generated_project_dir = state_dir.parent / "generated" / self.run_id
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.generated_project_dir.mkdir(parents=True, exist_ok=True)
        self._event_log_warnings: list[dict[str, Any]] = []
        self._run_index_warnings: list[dict[str, Any]] = []
        self.run_manifest = RunManifestWriter(
            runs_dir=self.runs_dir,
            run_id=self.run_id,
            generated_project_dir=self.generated_project_dir,
            state_dir=str(state_dir),
        )
        try:
            runs_root = self.runs_dir.parent
            update_index_on_run_event(
                runs_root=runs_root,
                event_type="run_started",
                run_id=self.run_id,
            )
        except Exception as exc:
            self._run_index_warnings.append(
                {"action": "run_started", "error": str(exc)}
            )
        try:
            append_runtime_event(
                self.runs_dir,
                event_type="run_started",
                run_id=self.run_id,
                payload={
                    "generated_project_dir": str(self.generated_project_dir),
                    "state_dir": str(state_dir),
                },
            )
        except Exception as exc:
            self._event_log_warnings.append(
                {"event_type": "run_started", "error": str(exc)}
            )
        self.question_flow = QuestionFlow()
        self.stage_evaluator = StageEvaluator()
        self.backflow_evaluator = BackflowEvaluator(
            is_requirements_ready=self.stage_evaluator.is_requirements_ready,
            is_solution_ready=self.stage_evaluator.is_solution_ready,
        )
        self.agents = {
            Stage.REQUIREMENTS: RequirementsEngineerAgent(),
            Stage.SOLUTION: SolutionEngineerAgent(),
            Stage.DESIGN: SystemDesignerAgent(),
            Stage.IMPLEMENTATION: ImplementationEngineerAgent(),
            Stage.TESTING: TestValidationEngineerAgent(),
        }

    def build_context(
        self, user_input: str = "", original_request: str = ""
    ) -> AgentContext:
        states = self.state_manager.load_all_states()
        state_dir = getattr(self.state_manager, "state_dir", "")
        return AgentContext(
            user_input=user_input,
            states=states,
            metadata={
                "run_id": self.run_id,
                "runs_dir": str(self.runs_dir),
                "generated_project_dir": str(self.generated_project_dir),
                "state_dir": str(state_dir),
                "original_request": original_request,
            },
            question_state=self.question_flow.parse_question_state(
                states.get("question_state", {})
            ),
        )

    def get_status_snapshot(self) -> dict[str, dict[str, Any]]:
        # Read-only display API for entrypoints.
        return self.state_manager.load_all_states()

    def get_artifact_names(self) -> list[str]:
        return sorted(set(self.DISPLAY_ARTIFACT_KEYS.keys()))

    def get_artifact_for_display(self, artifact_name: str) -> dict[str, Any]:
        target = self.DISPLAY_ARTIFACT_KEYS.get(str(artifact_name).strip())
        if target is None:
            return {}
        return self.state_manager.load_state(target)

    def evaluate_forward_transition(
        self, states: dict[str, dict[str, Any]], current_stage: Stage
    ) -> tuple[Stage | None, list[str]]:
        evidence: list[str] = []
        spec = states.get("spec", {})
        solution = states.get("solution", {})
        design = states.get("system_design", {})
        implementation_status = states.get("implementation_status", {})
        test_report = states.get("test_report", {})

        if current_stage == Stage.INIT and self.stage_evaluator.is_requirements_ready(
            states
        ):
            evidence.append("spec.project_goal is non-empty.")
            evidence.append("spec.functional_requirements is non-empty.")
            evidence.append("spec.acceptance_criteria is non-empty.")
            evidence.append(
                "Requirements artifact is consumable and can seed REQUIREMENTS stage execution."
            )
            return Stage.REQUIREMENTS, evidence
        if (
            current_stage == Stage.REQUIREMENTS
            and self.stage_evaluator.is_requirements_ready(states)
        ):
            evidence.append("spec.project_goal is non-empty.")
            evidence.append("spec.functional_requirements is non-empty.")
            evidence.append("spec.acceptance_criteria is non-empty.")
            evidence.append(
                "Requirements artifact is consumable by SOLUTION via functional requirement mapping."
            )
            return Stage.SOLUTION, evidence
        if current_stage == Stage.SOLUTION and self.stage_evaluator.is_solution_ready(
            states
        ):
            evidence.append("solution.selected_stack.backend is defined.")
            evidence.append(
                "solution.module_mapping is non-empty and ties modules to requirements."
            )
            evidence.append(
                "solution.module_mapping covers core spec.functional_requirements."
            )
            evidence.append(
                "Solution artifact is consumable by DESIGN for project_structure/contracts/data_flow."
            )
            return Stage.DESIGN, evidence
        if current_stage == Stage.DESIGN and self.stage_evaluator.is_design_ready(
            states
        ):
            evidence.append("design.project_structure.modules is non-empty.")
            evidence.append("design.contracts contain MVP critical handoff contracts.")
            evidence.append(
                "design.data_flow references existing contracts and forms a main path."
            )
            evidence.append("design.mvp_plan.first_deliverable is defined.")
            evidence.append(
                "Design artifact is consumable by IMPLEMENTATION as handoff checklist input."
            )
            return Stage.IMPLEMENTATION, evidence
        if (
            current_stage == Stage.IMPLEMENTATION
            and self.stage_evaluator.is_implementation_handoff_ready(states)
        ):
            evidence.append(
                "implementation_status.implementation_status is done (handoff-ready)."
            )
            evidence.append("implementation_status.blockers is empty.")
            evidence.append(
                "implementation_status.contract_compliance indicates handoff/design alignment."
            )
            evidence.append(
                "Implementation handoff artifact is consumable by TESTING without code mutation."
            )
            return Stage.TESTING, evidence
        if current_stage == Stage.TESTING and self.stage_evaluator.is_done(states):
            evidence.append("test_report.result is pass.")
            evidence.append("No high/critical open or confirmed issues block delivery.")
            return Stage.DONE, evidence

        if current_stage == Stage.REQUIREMENTS:
            if spec.get("open_questions"):
                evidence.append(
                    "Stay on REQUIREMENTS because blocking open_questions still exist."
                )
        elif current_stage == Stage.SOLUTION:
            if not solution.get("module_mapping"):
                evidence.append(
                    "Stay on SOLUTION because module_mapping is still empty."
                )
            elif not self.stage_evaluator.is_solution_ready(states):
                evidence.append(
                    "Stay on SOLUTION because module mapping does not yet satisfy requirements coverage invariants."
                )
        elif current_stage == Stage.DESIGN:
            if not design.get("contracts") or not design.get("data_flow"):
                evidence.append(
                    "Stay on DESIGN because contracts or data_flow are incomplete."
                )
            elif not self.stage_evaluator.is_design_ready(states):
                evidence.append(
                    "Stay on DESIGN because downstream implementation handoff invariants are not yet satisfied."
                )
        elif current_stage == Stage.IMPLEMENTATION:
            if implementation_status.get("implementation_status") != "done":
                evidence.append(
                    "Stay on IMPLEMENTATION because implementation is not done yet."
                )
            if implementation_status.get("blockers"):
                evidence.append(
                    "Stay on IMPLEMENTATION because blockers remain in implementation_status.blockers."
                )
            if not implementation_status.get("contract_compliance"):
                evidence.append(
                    "Stay on IMPLEMENTATION because handoff/design alignment is not yet established."
                )
        elif current_stage == Stage.TESTING:
            if test_report.get("result") != "pass":
                evidence.append(
                    "Stay on TESTING because validation has not reached a pass result."
                )
            if test_report.get("issues"):
                evidence.append(
                    "Stay on TESTING because open or confirmed issues still require upstream fixes."
                )

        return None, evidence

    def evaluate_backflow(
        self, states: dict[str, dict[str, Any]], current_stage: Stage
    ) -> tuple[Stage | None, list[str]]:
        return self.backflow_evaluator.evaluate(states, current_stage)

    def resolve_transition(
        self, states: dict[str, dict[str, Any]]
    ) -> TransitionDecision:
        flags = self.stage_evaluator.evaluate_stage_flags(states)
        computed_stage = self.stage_evaluator.stage_from_flags(flags)
        source_stage = self.stage_evaluator.infer_source_stage(states)
        answered_stage = self.question_flow.get_answered_question_stage(states)
        if answered_stage is not None and answered_stage in self.agents:
            return TransitionDecision(
                computed_stage=computed_stage,
                final_stage=answered_stage,
                source_stage=source_stage,
                should_stay=True,
                reason="Answered questions must be consumed by the same stage.",
                evidence=[
                    "question_state.status is answered and must be consumed before new transitions."
                ],
            )

        if self.question_flow.is_waiting_for_user_input(states):
            waiting_stage = self.question_flow.get_blocking_question_stage(
                states, source_stage
            )
            return TransitionDecision(
                computed_stage=computed_stage,
                final_stage=waiting_stage,
                source_stage=source_stage,
                wait_for_user_input=True,
                should_stay=True,
                reason="Waiting for user input.",
                evidence=[
                    "question_state is blocking and awaiting user response.",
                    "Progress is paused until the blocking question is resolved.",
                ],
            )

        backflow_target, backflow_evidence = self.evaluate_backflow(
            states, source_stage
        )
        if backflow_target is not None:
            resolved_flags = self.stage_evaluator.apply_backflow_to_flags(
                flags, backflow_target
            )
            return TransitionDecision(
                computed_stage=computed_stage,
                final_stage=self.stage_evaluator.stage_from_flags(resolved_flags),
                source_stage=source_stage,
                backflow_target=backflow_target,
                should_stay=False,
                reason="Backflow triggered.",
                evidence=backflow_evidence,
            )

        next_stage_to_execute, forward_evidence = self.evaluate_forward_transition(
            states, computed_stage
        )
        if next_stage_to_execute is not None:
            return TransitionDecision(
                computed_stage=computed_stage,
                final_stage=next_stage_to_execute,
                source_stage=source_stage,
                next_stage_to_execute=next_stage_to_execute,
                should_stay=False,
                reason="Forward transition available.",
                evidence=forward_evidence,
            )

        stay_evidence = list(forward_evidence) if forward_evidence else []
        if not stay_evidence:
            stay_evidence.append(
                f"Stay on {computed_stage} because no forward or backflow invariant is satisfied."
            )
        return TransitionDecision(
            computed_stage=computed_stage,
            final_stage=computed_stage,
            source_stage=source_stage,
            should_stay=True,
            reason="Stay on current stage.",
            evidence=stay_evidence,
        )

    def build_diagnostic_payload(
        self,
        decision: TransitionDecision,
        states_before: dict[str, dict[str, Any]],
        states_after: dict[str, dict[str, Any]],
        executed_stage: Stage | None = None,
        agent_result: AgentResult | None = None,
        summary: str = "",
    ) -> dict[str, Any]:
        question_state = states_after.get("question_state", {})
        decision_type = "STAY"
        if decision.wait_for_user_input:
            decision_type = "WAIT"
        elif decision.backflow_target is not None:
            decision_type = "BACKFLOW"
        elif decision.next_stage_to_execute is not None:
            decision_type = "FORWARD"
        elif decision.final_stage == Stage.INIT and executed_stage is not None:
            decision_type = "BOOTSTRAP"
        elif not decision.should_stay:
            decision_type = "EXECUTE"
        diagnostic_payload: dict[str, Any] = {
            "decision_type": decision_type,
            "stages": {
                "computed": str(decision.computed_stage),
                "source": str(decision.source_stage) if decision.source_stage else "",
                "final": str(decision.final_stage),
                "executed": str(executed_stage) if executed_stage else "",
            },
            "transition": {
                "reason": decision.reason,
                "next_stage_to_execute": str(decision.next_stage_to_execute)
                if decision.next_stage_to_execute
                else "",
                "backflow_target": str(decision.backflow_target)
                if decision.backflow_target
                else "",
                "wait_for_user_input": decision.wait_for_user_input,
                "evidence": list(decision.evidence),
            },
            "state_changes": self.changed_state_keys(states_before, states_after),
            "question_state": {
                "status": question_state.get("status", "idle"),
                "stage_name": question_state.get("stage_name", ""),
                "state_key": question_state.get("state_key", ""),
                "blocking": bool(question_state.get("blocking", False)),
                "question_count": len(question_state.get("questions", [])),
            },
            "execution": {
                "agent_name": agent_result.agent_name if agent_result else "",
                "state_key": agent_result.state_key if agent_result else "",
                "handoff_ready": bool(agent_result.handoff_ready)
                if agent_result
                else False,
                "requires_user_input": bool(agent_result.requires_user_input)
                if agent_result
                else False,
                "blockers": list(agent_result.blockers) if agent_result else [],
            },
            "execution_trace": dict(agent_result.diagnostics.get("execution_trace", {}))
            if agent_result
            else {},
            "state_validation_errors": dict(
                getattr(self.state_manager, "validation_errors", {})
            ),
            "run": {
                "run_id": self.run_id,
                "generated_project_dir": str(self.generated_project_dir),
                "runs_dir": str(self.runs_dir),
            },
            "summary": summary,
        }
        if self._event_log_warnings:
            trace = diagnostic_payload.get("execution_trace", {})
            if not isinstance(trace, dict):
                trace = {}
            trace["runtime_event_log_warnings"] = list(self._event_log_warnings)
            diagnostic_payload["execution_trace"] = trace
        if self._run_index_warnings:
            trace = diagnostic_payload.get("execution_trace", {})
            if not isinstance(trace, dict):
                trace = {}
            trace["runtime_run_index_warnings"] = list(self._run_index_warnings)
            diagnostic_payload["execution_trace"] = trace
        if agent_result:
            raw_llm_trace = agent_result.diagnostics.get("llm_trace")
            if raw_llm_trace:
                diagnostic_payload["llm_trace"] = self._normalize_llm_trace(
                    raw_llm_trace
                )
        return diagnostic_payload

    def determine_execution_stage(self, decision: TransitionDecision) -> Stage | None:
        if decision.wait_for_user_input:
            return None
        if (
            decision.backflow_target is not None
            and decision.backflow_target in self.agents
        ):
            return decision.backflow_target
        if (
            decision.next_stage_to_execute is not None
            and decision.next_stage_to_execute in self.agents
        ):
            return decision.next_stage_to_execute
        if decision.final_stage == Stage.INIT:
            return Stage.REQUIREMENTS
        if decision.final_stage in self.agents:
            return decision.final_stage
        return None

    def build_result_summary(
        self,
        decision: TransitionDecision,
        executed_stage: Stage | None = None,
        agent_result: AgentResult | None = None,
    ) -> str:
        if decision.wait_for_user_input:
            return f"Resolved stage to {decision.final_stage}; waiting for user input."
        if executed_stage is None:
            return (
                f"Resolved stage to {decision.final_stage}; "
                f"no agent execution was required."
            )

        agent_name = agent_result.agent_name if agent_result else "Unknown agent"
        return (
            f"Resolved stage to {decision.final_stage}; "
            f"executed {executed_stage} via {agent_name}."
        )

    def orchestrate(
        self, user_input: str = "", original_request: str = ""
    ) -> OrchestrationResult:
        states_before = self.state_manager.load_all_states()
        decision = self.resolve_transition(states_before)
        try:
            append_runtime_event(
                self.runs_dir,
                event_type="decision_computed",
                run_id=self.run_id,
                payload={
                    "computed_stage": str(decision.computed_stage),
                    "final_stage": str(decision.final_stage),
                    "should_stay": bool(decision.should_stay),
                    "wait_for_user_input": bool(decision.wait_for_user_input),
                    "next_stage_to_execute": str(decision.next_stage_to_execute)
                    if decision.next_stage_to_execute
                    else "",
                    "backflow_target": str(decision.backflow_target)
                    if decision.backflow_target
                    else "",
                },
            )
        except Exception as exc:
            self._event_log_warnings.append(
                {"event_type": "decision_computed", "error": str(exc)}
            )

        executed_stage = self.determine_execution_stage(decision)
        agent_result: AgentResult | None = None
        if executed_stage is not None:
            agent_result = self.run_stage(
                executed_stage,
                user_input=user_input,
                original_request=original_request or user_input,
            )
            try:
                append_runtime_event(
                    self.runs_dir,
                    event_type="stage_executed",
                    run_id=self.run_id,
                    payload={
                        "executed_stage": str(executed_stage),
                        "agent_name": agent_result.agent_name,
                        "state_key": agent_result.state_key,
                        "handoff_ready": bool(agent_result.handoff_ready),
                        "requires_user_input": bool(agent_result.requires_user_input),
                    },
                )
            except Exception as exc:
                self._event_log_warnings.append(
                    {"event_type": "stage_executed", "error": str(exc)}
                )

        states_after = self.state_manager.load_all_states()
        if executed_stage is not None and agent_result is not None:
            try:
                # Only record lineage after confirming the stage output was persisted.
                # run_stage() may return a fallback AgentResult when save_state() fails
                # schema validation, leaving the prior state in place.
                state_key = str(agent_result.state_key).strip()
                before = states_before.get(state_key)
                after = states_after.get(state_key)
                persisted = before != after
                if persisted:
                    artifact_by_stage = {
                        Stage.REQUIREMENTS: "spec",
                        Stage.SOLUTION: "solution",
                        Stage.DESIGN: "system_design",
                        Stage.IMPLEMENTATION: "implementation_status",
                        Stage.TESTING: "test_report",
                    }
                    artifact = artifact_by_stage.get(Stage(executed_stage))
                    if artifact:
                        upsert_lineage_entry(
                            run_dir=self.runs_dir,
                            run_id=self.run_id,
                            artifact=artifact,  # type: ignore[arg-type]
                            generated_by=str(agent_result.agent_name).strip() or "unknown",
                        )
            except Exception as exc:
                self._event_log_warnings.append(
                    {"event_type": "lineage_write", "error": str(exc)}
                )
        summary = self.build_result_summary(
            decision=decision,
            executed_stage=executed_stage,
            agent_result=agent_result,
        )

        decision_type_for_event = "STAY"
        if decision.wait_for_user_input:
            decision_type_for_event = "WAIT"
        elif decision.backflow_target is not None:
            decision_type_for_event = "BACKFLOW"
        elif decision.next_stage_to_execute is not None:
            decision_type_for_event = "FORWARD"
        elif decision.final_stage == Stage.INIT and executed_stage is not None:
            decision_type_for_event = "BOOTSTRAP"
        elif not decision.should_stay:
            decision_type_for_event = "EXECUTE"

        try:
            append_runtime_event(
                self.runs_dir,
                event_type="run_finished",
                run_id=self.run_id,
                payload={
                    "latest_final_stage": str(decision.final_stage),
                    "latest_decision_type": decision_type_for_event,
                },
            )
        except Exception as exc:
            self._event_log_warnings.append(
                {"event_type": "run_finished", "error": str(exc)}
            )

        try:
            runs_root = self.runs_dir.parent
            update_index_on_run_event(
                runs_root=runs_root,
                event_type="run_finished",
                run_id=self.run_id,
                final_stage=str(decision.final_stage),
                finished_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        except Exception as exc:
            self._run_index_warnings.append(
                {"action": "run_finished", "error": str(exc)}
            )

        result = OrchestrationResult(
            decision=decision,
            executed_stage=executed_stage,
            agent_result=agent_result,
            states_before=states_before,
            states_after=states_after,
            diagnostic=self.build_diagnostic_payload(
                decision=decision,
                states_before=states_before,
                states_after=states_after,
                executed_stage=executed_stage,
                agent_result=agent_result,
                summary=summary,
            ),
            summary=summary,
        )
        summary_model = self.run_manifest.append_step(
            result,
            step_input=user_input,
            original_request=original_request or user_input,
        )
        self.run_manifest.write(summary_model)
        return result

    def run_stage(
        self,
        stage_name: Stage | str,
        user_input: str = "",
        original_request: str = "",
    ) -> AgentResult:
        stage = Stage(stage_name)
        try:
            agent = self.agents[stage]
        except KeyError as exc:
            raise KeyError(f"Unknown stage: {stage}") from exc

        context = self.build_context(
            user_input=user_input,
            original_request=original_request or user_input,
        )
        result = agent.run(context)
        try:
            self.state_manager.save_state(result.state_key, result.updated_state)
        except ValueError as exc:
            fallback_result = AgentResult(
                agent_name=result.agent_name,
                stage_name=result.stage_name,
                state_key=result.state_key,
                updated_state=context.states.get(result.state_key, {}),
                summary="Stage output failed schema validation and was blocked.",
                notes=[str(exc)],
                blockers=["schema_validation_failed"],
                handoff_ready=False,
                requires_user_input=True,
                question_state_update=self.question_flow.parse_question_state(
                    {
                        "status": "awaiting_user",
                        "stage_name": str(stage),
                        "state_key": result.state_key,
                        "blocking": True,
                        "questions": [
                            {
                                "id": "schema_validation_failed",
                                "title": "Schema validation failed",
                                "description": str(exc),
                                "response_type": "free_text",
                                "options": [],
                                "allow_free_text": True,
                                "answer": None,
                            }
                        ],
                        "created_by": result.agent_name,
                        "resolution_summary": "",
                    }
                ),
                diagnostics=result.diagnostics,
            )
            self.state_manager.save_state(
                "question_state",
                self.question_flow.serialize_question_state(
                    fallback_result.question_state_update
                ),
            )
            return fallback_result
        if result.question_state_update is not None:
            self.state_manager.save_state(
                "question_state",
                self.question_flow.serialize_question_state(
                    result.question_state_update
                ),
            )
        elif self.question_flow.should_clear_question_state(context, result):
            self.state_manager.save_state(
                "question_state",
                self.question_flow.default_question_state_payload(),
            )
        return result

    def record_auto_run_stop(
        self,
        *,
        stop_reason: str,
        repeated_stage: Stage | str,
        repeated_decision: str,
        step_index: int,
    ) -> None:
        if not self.run_manifest._run_steps:
            return
        last_step = self.run_manifest._run_steps[-1]
        trace = dict(last_step.execution_trace)
        trace["auto_run_stop"] = {
            "stop_reason": stop_reason,
            "repeated_stage": str(repeated_stage),
            "repeated_decision": repeated_decision,
            "step_index": step_index,
        }
        last_step.execution_trace = trace
        summary = RunSummaryModel(
            schema_version="1",
            run_id=self.run_id,
            original_request=str(self.run_manifest._run_steps[0].input),
            generated_project_dir=str(self.generated_project_dir),
            state_dir=str(getattr(self.state_manager, "state_dir", "")),
            latest_summary=last_step.summary,
            latest_final_stage=last_step.final_stage,
            latest_decision_type=last_step.decision_type,
            steps=self.run_manifest._run_steps,
        )
        self.run_manifest.write(summary)
