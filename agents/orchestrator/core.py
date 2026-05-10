from __future__ import annotations

import json
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
from schemas.run_summary import RunSummaryModel
from .backflow_evaluator import BackflowEvaluator
from .models import OrchestrationResult, Stage, TransitionDecision
from .question_flow import QuestionFlow
from .stage_evaluator import StageEvaluator


class Orchestrator:
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

    def __init__(self, state_manager: StateManager | None = None) -> None:
        self.state_manager = state_manager or StateManager()
        state_dir_value = getattr(self.state_manager, "state_dir", None)
        state_dir = Path(state_dir_value) if state_dir_value is not None else Path.cwd() / ".forgeflow" / "state"
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        self.runs_dir = state_dir.parent / "runs" / self.run_id
        self.generated_project_dir = state_dir.parent / "generated" / self.run_id
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.generated_project_dir.mkdir(parents=True, exist_ok=True)
        self._run_steps: list[dict[str, Any]] = []
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

    def build_context(self, user_input: str = "", original_request: str = "") -> AgentContext:
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

    def evaluate_forward_transition(
        self, states: dict[str, dict[str, Any]], current_stage: Stage
    ) -> tuple[Stage | None, list[str]]:
        evidence: list[str] = []
        spec = states.get("spec", {})
        solution = states.get("solution", {})
        design = states.get("system_design", {})
        implementation_status = states.get("implementation_status", {})
        test_report = states.get("test_report", {})

        if current_stage == Stage.INIT and self.stage_evaluator.is_requirements_ready(states):
            evidence.append("spec.project_goal is non-empty.")
            evidence.append("spec.functional_requirements is non-empty.")
            evidence.append("spec.acceptance_criteria is non-empty.")
            return Stage.REQUIREMENTS, evidence
        if (
            current_stage == Stage.REQUIREMENTS
            and self.stage_evaluator.is_requirements_ready(states)
        ):
            evidence.append("spec.project_goal is non-empty.")
            evidence.append("spec.functional_requirements is non-empty.")
            evidence.append("spec.acceptance_criteria is non-empty.")
            evidence.append("Requirements are ready for solution generation.")
            return Stage.SOLUTION, evidence
        if current_stage == Stage.SOLUTION and self.stage_evaluator.is_solution_ready(states):
            evidence.append("solution.selected_stack.backend is defined.")
            evidence.append("solution.module_mapping contains stable core modules.")
            evidence.append(
                "solution.module_mapping covers core spec.functional_requirements."
            )
            evidence.append("Solution is ready for design generation.")
            return Stage.DESIGN, evidence
        if current_stage == Stage.DESIGN and self.stage_evaluator.is_design_ready(states):
            evidence.append("design.project_structure.modules is non-empty.")
            evidence.append("design.contracts contain MVP critical handoff contracts.")
            evidence.append(
                "design.data_flow references existing contracts and forms a main path."
            )
            evidence.append("design.mvp_plan.first_deliverable is defined.")
            evidence.append("Design is ready for implementation planning.")
            return Stage.IMPLEMENTATION, evidence
        if (
            current_stage == Stage.IMPLEMENTATION
            and self.stage_evaluator.has_validation_context(states)
        ):
            evidence.append("implementation_status.implementation_status is done.")
            evidence.append("implementation_status.blockers is empty.")
            evidence.append("A test scope is available for validation.")
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
        elif current_stage == Stage.DESIGN:
            if not design.get("contracts") or not design.get("data_flow"):
                evidence.append(
                    "Stay on DESIGN because contracts or data_flow are incomplete."
                )
        elif current_stage == Stage.IMPLEMENTATION:
            if implementation_status.get("implementation_status") != "done":
                evidence.append(
                    "Stay on IMPLEMENTATION because implementation is not done yet."
                )
        elif current_stage == Stage.TESTING:
            if test_report.get("result") != "pass":
                evidence.append(
                    "Stay on TESTING because validation has not reached a pass result."
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
                    "question_state is blocking and awaiting user response."
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

        return TransitionDecision(
            computed_stage=computed_stage,
            final_stage=computed_stage,
            source_stage=source_stage,
            should_stay=True,
            reason="Stay on current stage.",
            evidence=[],
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
        return {
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
            "llm_trace": dict(agent_result.diagnostics.get("llm_trace", {}))
            if agent_result
            else {},
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

    def determine_execution_stage(self, decision: TransitionDecision) -> Stage | None:
        if decision.wait_for_user_input:
            return None
        if decision.backflow_target is not None and decision.backflow_target in self.agents:
            return decision.backflow_target
        if decision.next_stage_to_execute is not None and decision.next_stage_to_execute in self.agents:
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
            return (
                f"Resolved stage to {decision.final_stage}; "
                "waiting for user input."
            )
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

    def orchestrate(self, user_input: str = "", original_request: str = "") -> OrchestrationResult:
        states_before = self.state_manager.load_all_states()
        decision = self.resolve_transition(states_before)

        executed_stage = self.determine_execution_stage(decision)
        agent_result: AgentResult | None = None
        if executed_stage is not None:
            agent_result = self.run_stage(
                executed_stage,
                user_input=user_input,
                original_request=original_request or user_input,
            )

        states_after = self.state_manager.load_all_states()
        summary = self.build_result_summary(
            decision=decision,
            executed_stage=executed_stage,
            agent_result=agent_result,
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
        self._write_run_manifest(
            result,
            step_input=user_input,
            original_request=original_request or user_input,
        )
        return result

    def _write_run_manifest(
        self,
        result: OrchestrationResult,
        step_input: str,
        original_request: str,
    ) -> None:
        step = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input": step_input,
            "decision_type": result.diagnostic.get("decision_type", ""),
            "computed_stage": result.diagnostic.get("stages", {}).get("computed", ""),
            "final_stage": result.diagnostic.get("stages", {}).get("final", ""),
            "executed_stage": result.diagnostic.get("stages", {}).get("executed", ""),
            "summary": result.summary,
            "llm_trace": result.diagnostic.get("llm_trace", {}),
            "execution_trace": result.diagnostic.get("execution_trace", {}),
            "state_changes": result.diagnostic.get("state_changes", []),
            "question_state": result.diagnostic.get("question_state", {}),
        }
        self._run_steps.append(step)
        manifest = {
            "schema_version": "1",
            "run_id": self.run_id,
            "original_request": original_request,
            "generated_project_dir": str(self.generated_project_dir),
            "state_dir": str(getattr(self.state_manager, "state_dir", "")),
            "latest_summary": result.summary,
            "latest_final_stage": result.diagnostic.get("stages", {}).get("final", ""),
            "latest_decision_type": result.diagnostic.get("decision_type", ""),
            "steps": self._run_steps,
        }
        normalized_manifest = RunSummaryModel.model_validate(manifest).model_dump(mode="python")
        path = self.runs_dir / "summary.json"
        path.write_text(
            json.dumps(normalized_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

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
