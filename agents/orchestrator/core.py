from __future__ import annotations

from typing import Any

from ..base import AgentContext, AgentResult
from ..implementation_engineer import ImplementationEngineerAgent
from ..requirements_engineer import RequirementsEngineerAgent
from ..solution_engineer import SolutionEngineerAgent
from ..state_manager import StateManager
from ..system_designer import SystemDesignerAgent
from ..test_validation_engineer import TestValidationEngineerAgent
from .backflow_evaluator import BackflowEvaluator
from .models import OrchestrationResult, Stage, StageFlags, TransitionDecision
from .question_flow import QuestionFlow
from .stage_evaluator import StageEvaluator


class Orchestrator:
    def __init__(self, state_manager: StateManager | None = None) -> None:
        self.state_manager = state_manager or StateManager()
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

    def build_context(self, user_input: str = "") -> AgentContext:
        states = self.state_manager.load_all_states()
        return AgentContext(
            user_input=user_input,
            states=states,
            question_state=self.parse_question_state(
                states.get("question_state", {})
            ),
        )

    def parse_question_state(self, payload: dict[str, Any]):
        return self.question_flow.parse_question_state(payload)

    def serialize_question_state(self, question_state):
        return self.question_flow.serialize_question_state(question_state)

    def default_question_state_payload(self) -> dict[str, Any]:
        return self.question_flow.default_question_state_payload()

    def should_clear_question_state(
        self, context: AgentContext, result: AgentResult
    ) -> bool:
        return self.question_flow.should_clear_question_state(context, result)

    def get_blocking_question_stage(
        self, states: dict[str, dict[str, Any]], fallback_stage: Stage
    ) -> Stage:
        return self.question_flow.get_blocking_question_stage(states, fallback_stage)

    def is_waiting_for_user_input(
        self, states: dict[str, dict[str, Any]]
    ) -> bool:
        return self.question_flow.is_waiting_for_user_input(states)

    def is_requirements_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        return self.stage_evaluator.is_requirements_ready(states)

    def is_solution_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        return self.stage_evaluator.is_solution_ready(states)

    def is_design_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        return self.stage_evaluator.is_design_ready(states)

    def has_active_implementation(self, states: dict[str, dict[str, Any]]) -> bool:
        return self.stage_evaluator.has_active_implementation(states)

    def has_validation_context(self, states: dict[str, dict[str, Any]]) -> bool:
        return self.stage_evaluator.has_validation_context(states)

    def is_done(self, states: dict[str, dict[str, Any]]) -> bool:
        return self.stage_evaluator.is_done(states)

    def evaluate_stage_flags(self, states: dict[str, dict[str, Any]]) -> StageFlags:
        return self.stage_evaluator.evaluate_stage_flags(states)

    def stage_from_flags(self, flags: StageFlags) -> Stage:
        return self.stage_evaluator.stage_from_flags(flags)

    def compute_current_stage(
        self, states: dict[str, dict[str, Any]]
    ) -> Stage:
        return self.stage_evaluator.compute_current_stage(states)

    def infer_source_stage(self, states: dict[str, dict[str, Any]]) -> Stage:
        return self.stage_evaluator.infer_source_stage(states)

    def apply_backflow_to_flags(
        self, flags: StageFlags, backflow_target: Stage
    ) -> StageFlags:
        return self.stage_evaluator.apply_backflow_to_flags(flags, backflow_target)

    def evaluate_forward_transition(
        self, states: dict[str, dict[str, Any]], current_stage: Stage
    ) -> tuple[Stage | None, list[str]]:
        evidence: list[str] = []
        spec = states.get("spec", {})
        solution = states.get("solution", {})
        design = states.get("system_design", {})
        implementation_status = states.get("implementation_status", {})
        test_report = states.get("test_report", {})

        if current_stage == Stage.INIT and self.is_requirements_ready(states):
            evidence.append("spec.project_goal is non-empty.")
            evidence.append("spec.functional_requirements is non-empty.")
            evidence.append("spec.acceptance_criteria is non-empty.")
            return Stage.REQUIREMENTS, evidence
        if (
            current_stage == Stage.REQUIREMENTS
            and self.is_solution_ready(states)
        ):
            evidence.append("solution.selected_stack.backend is defined.")
            if solution.get("selected_stack", {}).get("frontend"):
                evidence.append("solution.selected_stack.frontend is defined.")
            if solution.get("selected_stack", {}).get("agent_framework"):
                evidence.append(
                    "solution.selected_stack.agent_framework is defined."
                )
            evidence.append("solution.module_mapping contains stable core modules.")
            evidence.append(
                "solution.module_mapping covers core spec.functional_requirements."
            )
            return Stage.SOLUTION, evidence
        if current_stage == Stage.SOLUTION and self.is_design_ready(states):
            evidence.append("design.project_structure.modules is non-empty.")
            evidence.append("design.contracts contain MVP critical handoff contracts.")
            evidence.append(
                "design.data_flow references existing contracts and forms a main path."
            )
            evidence.append("design.mvp_plan.in_scope is non-empty.")
            evidence.append("design.mvp_plan.first_deliverable is defined.")
            return Stage.DESIGN, evidence
        if current_stage == Stage.DESIGN and self.has_active_implementation(states):
            evidence.append("implementation_status.module_name is defined.")
            evidence.append(
                "implementation_status.implementation_status is active."
            )
            return Stage.IMPLEMENTATION, evidence
        if (
            current_stage == Stage.IMPLEMENTATION
            and self.has_validation_context(states)
        ):
            evidence.append("implementation_status.implementation_status is done.")
            evidence.append("implementation_status.blockers is empty.")
            evidence.append("A test scope is available for validation.")
            return Stage.TESTING, evidence
        if current_stage == Stage.TESTING and self.is_done(states):
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
        flags = self.evaluate_stage_flags(states)
        computed_stage = self.stage_from_flags(flags)
        source_stage = self.infer_source_stage(states)
        if self.is_waiting_for_user_input(states):
            waiting_stage = self.get_blocking_question_stage(
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
            resolved_flags = self.apply_backflow_to_flags(flags, backflow_target)
            return TransitionDecision(
                computed_stage=computed_stage,
                final_stage=self.stage_from_flags(resolved_flags),
                source_stage=source_stage,
                backflow_target=backflow_target,
                should_stay=False,
                reason="Backflow triggered.",
                evidence=backflow_evidence,
            )

        forward_target, forward_evidence = self.evaluate_forward_transition(
            states, computed_stage
        )
        if forward_target is not None:
            return TransitionDecision(
                computed_stage=computed_stage,
                final_stage=forward_target,
                source_stage=source_stage,
                forward_target=forward_target,
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

    def determine_execution_stage(self, decision: TransitionDecision) -> Stage | None:
        if decision.wait_for_user_input:
            return None
        if decision.backflow_target is not None and decision.backflow_target in self.agents:
            return decision.backflow_target
        if decision.forward_target is not None and decision.forward_target in self.agents:
            return decision.forward_target
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

    def orchestrate(self, user_input: str = "") -> OrchestrationResult:
        states_before = self.state_manager.load_all_states()
        decision = self.resolve_transition(states_before)

        executed_stage = self.determine_execution_stage(decision)
        agent_result: AgentResult | None = None
        if executed_stage is not None:
            agent_result = self.run_stage(executed_stage, user_input=user_input)

        states_after = self.state_manager.load_all_states()
        summary = self.build_result_summary(
            decision=decision,
            executed_stage=executed_stage,
            agent_result=agent_result,
        )

        return OrchestrationResult(
            decision=decision,
            executed_stage=executed_stage,
            agent_result=agent_result,
            states_before=states_before,
            states_after=states_after,
            summary=summary,
        )

    def run_stage(
        self, stage_name: Stage | str, user_input: str = ""
    ) -> AgentResult:
        stage = Stage(stage_name)
        try:
            agent = self.agents[stage]
        except KeyError as exc:
            raise KeyError(f"Unknown stage: {stage}") from exc

        context = self.build_context(user_input=user_input)
        result = agent.run(context)
        self.state_manager.save_state(result.state_key, result.updated_state)
        if result.question_state_update is not None:
            self.state_manager.save_state(
                "question_state",
                self.serialize_question_state(result.question_state_update),
            )
        elif self.should_clear_question_state(context, result):
            self.state_manager.save_state(
                "question_state",
                self.default_question_state_payload(),
            )
        return result
