from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from .base import (
    AgentContext,
    AgentResult,
    QuestionAnswer,
    QuestionItem,
    QuestionOption,
    QuestionState,
)
from .implementation_engineer import ImplementationEngineerAgent
from .requirements_engineer import RequirementsEngineerAgent
from .solution_engineer import SolutionEngineerAgent
from .state_manager import StateManager
from .system_designer import SystemDesignerAgent
from .test_validation_engineer import TestValidationEngineerAgent


class Stage(StrEnum):
    INIT = "INIT"
    REQUIREMENTS = "REQUIREMENTS"
    SOLUTION = "SOLUTION"
    DESIGN = "DESIGN"
    IMPLEMENTATION = "IMPLEMENTATION"
    TESTING = "TESTING"
    DONE = "DONE"


@dataclass(slots=True)
class StageFlags:
    requirements_ready: bool = False
    solution_ready: bool = False
    design_ready: bool = False
    implementing_active: bool = False
    testing_active: bool = False
    done_ready: bool = False


@dataclass(slots=True)
class TransitionDecision:
    computed_stage: Stage
    final_stage: Stage
    source_stage: Stage | None = None
    forward_target: Stage | None = None
    backflow_target: Stage | None = None
    wait_for_user_input: bool = False
    should_stay: bool = True
    reason: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OrchestrationResult:
    decision: TransitionDecision
    executed_stage: Stage | None = None
    agent_result: AgentResult | None = None
    states_before: dict[str, dict[str, Any]] = field(default_factory=dict)
    states_after: dict[str, dict[str, Any]] = field(default_factory=dict)
    summary: str = ""


class Orchestrator:
    def __init__(self, state_manager: StateManager | None = None) -> None:
        self.state_manager = state_manager or StateManager()
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

    def parse_question_state(self, payload: dict[str, Any]) -> QuestionState:
        questions: list[QuestionItem] = []
        for item in payload.get("questions", []):
            options = [
                QuestionOption(
                    label=option.get("label", ""),
                    value=option.get("value", ""),
                    hint=option.get("hint", ""),
                )
                for option in item.get("options", [])
            ]
            answer_payload = item.get("answer")
            answer = None
            if isinstance(answer_payload, dict):
                answer = QuestionAnswer(
                    selected_values=list(
                        answer_payload.get("selected_values", [])
                    ),
                    free_text=answer_payload.get("free_text", ""),
                )
            questions.append(
                QuestionItem(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    response_type=item.get("response_type", "single_select"),
                    options=options,
                    allow_free_text=item.get("allow_free_text", False),
                    answer=answer,
                )
            )

        return QuestionState(
            status=payload.get("status", "idle"),
            stage_name=payload.get("stage_name", ""),
            state_key=payload.get("state_key", ""),
            blocking=payload.get("blocking", False),
            questions=questions,
            created_by=payload.get("created_by", ""),
            resolution_summary=payload.get("resolution_summary", ""),
        )

    def serialize_question_state(
        self, question_state: QuestionState | None
    ) -> dict[str, Any]:
        if question_state is None:
            return self.default_question_state_payload()
        return asdict(question_state)

    def default_question_state_payload(self) -> dict[str, Any]:
        return {
            "status": "idle",
            "stage_name": "",
            "state_key": "",
            "blocking": False,
            "questions": [],
            "created_by": "",
            "resolution_summary": "",
        }

    def should_clear_question_state(
        self, context: AgentContext, result: AgentResult
    ) -> bool:
        question_state = context.question_state
        if question_state is None:
            return False
        if question_state.status != "answered":
            return False
        if result.requires_user_input or result.question_state_update is not None:
            return False
        return question_state.stage_name == result.stage_name

    def get_blocking_question_stage(
        self, states: dict[str, dict[str, Any]], fallback_stage: Stage
    ) -> Stage:
        question_state = states.get("question_state", {})
        stage_name = question_state.get("stage_name")
        if not stage_name:
            return fallback_stage
        try:
            return Stage(stage_name)
        except ValueError:
            return fallback_stage

    def is_waiting_for_user_input(
        self, states: dict[str, dict[str, Any]]
    ) -> bool:
        question_state = states.get("question_state", {})
        return bool(
            question_state.get("blocking")
            and question_state.get("status") in {"awaiting_user", "answered"}
            and question_state.get("questions")
        )

    def is_requirements_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        spec = states.get("spec", {})
        return bool(
            spec.get("project_goal")
            and spec.get("functional_requirements")
            and spec.get("acceptance_criteria")
        )

    def is_solution_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.is_requirements_ready(states):
            return False

        solution = states.get("solution", {})
        selected_stack = solution.get("selected_stack", {})
        module_mapping = solution.get("module_mapping", [])
        spec = states.get("spec", {})
        functional_requirements = spec.get("functional_requirements", [])

        has_core_backend = bool(selected_stack.get("backend"))

        stable_modules = [
            module
            for module in module_mapping
            if module.get("module") and module.get("responsibilities")
        ]
        covered_requirements = {
            requirement
            for module in stable_modules
            for requirement in module.get("covers_requirements", [])
            if requirement
        }

        return bool(
            has_core_backend
            and stable_modules
            and functional_requirements
            and covered_requirements
        )

    def is_design_ready(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.is_solution_ready(states):
            return False

        design = states.get("system_design", {})
        project_structure = design.get("project_structure", {})
        modules = project_structure.get("modules", [])
        contracts = design.get("contracts", [])
        data_flow = design.get("data_flow", [])
        mvp_plan = design.get("mvp_plan", {})

        stable_contracts = [
            contract
            for contract in contracts
            if contract.get("name")
            and contract.get("producer")
            and contract.get("consumers")
            and contract.get("input")
            and contract.get("output")
        ]
        stable_contract_names = {
            contract["name"] for contract in stable_contracts if contract.get("name")
        }
        valid_data_flow = [
            step
            for step in data_flow
            if step.get("contract_name") in stable_contract_names
        ]

        return bool(
            modules
            and stable_contracts
            and valid_data_flow
            and mvp_plan.get("in_scope")
            and mvp_plan.get("first_deliverable")
        )

    def has_active_implementation(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.is_design_ready(states):
            return False

        implementation_status = states.get("implementation_status", {})
        return bool(
            implementation_status.get("module_name")
            and implementation_status.get("implementation_status")
            in {"in_progress", "blocked", "done"}
        )

    def has_validation_context(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.has_active_implementation(states):
            return False

        implementation_status = states.get("implementation_status", {})
        test_report = states.get("test_report", {})

        return bool(
            implementation_status.get("implementation_status") == "done"
            and not implementation_status.get("blockers")
            and test_report.get("test_scope")
        )

    def is_done(self, states: dict[str, dict[str, Any]]) -> bool:
        if not self.has_validation_context(states):
            return False

        test_report = states.get("test_report", {})
        issues = test_report.get("issues", [])
        blocking_issue_exists = any(
            issue.get("status") in {"open", "confirmed"}
            and issue.get("severity") in {"high", "critical"}
            for issue in issues
        )

        return bool(
            test_report.get("result") == "pass" and not blocking_issue_exists
        )

    def evaluate_stage_flags(self, states: dict[str, dict[str, Any]]) -> StageFlags:
        requirements_ready = self.is_requirements_ready(states)
        solution_ready = requirements_ready and self.is_solution_ready(states)
        design_ready = solution_ready and self.is_design_ready(states)
        implementing_active = design_ready and self.has_active_implementation(states)
        testing_active = implementing_active and self.has_validation_context(states)
        done_ready = testing_active and self.is_done(states)

        return StageFlags(
            requirements_ready=requirements_ready,
            solution_ready=solution_ready,
            design_ready=design_ready,
            implementing_active=implementing_active,
            testing_active=testing_active,
            done_ready=done_ready,
        )

    def stage_from_flags(self, flags: StageFlags) -> Stage:
        if flags.done_ready:
            return Stage.DONE
        if flags.testing_active:
            return Stage.TESTING
        if flags.implementing_active:
            return Stage.IMPLEMENTATION
        if flags.design_ready:
            return Stage.DESIGN
        if flags.solution_ready:
            return Stage.SOLUTION
        if flags.requirements_ready:
            return Stage.REQUIREMENTS
        return Stage.INIT

    def compute_current_stage(
        self, states: dict[str, dict[str, Any]]
    ) -> Stage:
        return self.stage_from_flags(self.evaluate_stage_flags(states))

    def infer_source_stage(self, states: dict[str, dict[str, Any]]) -> Stage:
        computed_stage = self.compute_current_stage(states)
        if computed_stage in {
            Stage.TESTING,
            Stage.IMPLEMENTATION,
            Stage.DESIGN,
            Stage.SOLUTION,
        }:
            return computed_stage

        test_report = states.get("test_report", {})
        implementation_status = states.get("implementation_status", {})
        design = states.get("system_design", {})
        solution = states.get("solution", {})

        if (
            implementation_status.get("implementation_status") == "done"
            and (
                test_report.get("result") != "not_run"
                or bool(test_report.get("issues"))
            )
        ):
            return Stage.TESTING

        if (
            implementation_status.get("module_name")
            and implementation_status.get("implementation_status")
            in {"in_progress", "blocked", "done"}
        ):
            return Stage.IMPLEMENTATION

        if (
            design.get("project_structure", {}).get("modules")
            or design.get("contracts")
            or design.get("data_flow")
            or design.get("mvp_plan", {}).get("first_deliverable")
        ):
            return Stage.DESIGN

        selected_stack = solution.get("selected_stack", {})
        if (
            solution.get("module_mapping")
            or selected_stack.get("backend")
            or selected_stack.get("frontend")
            or selected_stack.get("agent_framework")
        ):
            return Stage.SOLUTION

        return computed_stage

    def apply_backflow_to_flags(
        self, flags: StageFlags, backflow_target: Stage
    ) -> StageFlags:
        resolved = StageFlags(
            requirements_ready=flags.requirements_ready,
            solution_ready=flags.solution_ready,
            design_ready=flags.design_ready,
            implementing_active=flags.implementing_active,
            testing_active=flags.testing_active,
            done_ready=flags.done_ready,
        )

        if backflow_target == Stage.REQUIREMENTS:
            resolved.solution_ready = False
            resolved.design_ready = False
            resolved.implementing_active = False
            resolved.testing_active = False
            resolved.done_ready = False
            return resolved

        if backflow_target == Stage.SOLUTION:
            resolved.design_ready = False
            resolved.implementing_active = False
            resolved.testing_active = False
            resolved.done_ready = False
            return resolved

        if backflow_target == Stage.DESIGN:
            resolved.implementing_active = False
            resolved.testing_active = False
            resolved.done_ready = False
            return resolved

        if backflow_target == Stage.IMPLEMENTATION:
            resolved.testing_active = False
            resolved.done_ready = False
            return resolved

        return resolved

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
        if current_stage == Stage.IMPLEMENTATION and self.has_validation_context(states):
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
        evidence: list[str] = []
        spec = states.get("spec", {})
        solution = states.get("solution", {})
        design = states.get("system_design", {})
        implementation_status = states.get("implementation_status", {})
        test_report = states.get("test_report", {})

        def issue_is_active(issue: dict[str, Any]) -> bool:
            return issue.get("status") in {"open", "confirmed"}

        def issue_is_blocking(issue: dict[str, Any]) -> bool:
            return issue.get("severity") in {"high", "critical"}

        def collect_text(*parts: Any) -> str:
            return " ".join(str(part).lower() for part in parts if part)

        def contains_any(text: str, keywords: set[str]) -> bool:
            return any(keyword in text for keyword in keywords)

        execution_keywords = {
            "environment",
            "dependency",
            "dependencies",
            "tool",
            "toolchain",
            "permission",
            "resource",
            "local",
            "install",
            "network",
            "dns",
            "sandbox",
            "runtime",
        }
        design_keywords = {
            "contract",
            "input",
            "output",
            "schema",
            "data flow",
            "trigger",
            "producer",
            "consumer",
            "boundary",
            "interface",
            "project structure",
            "directory",
        }
        solution_keywords = {
            "module",
            "responsibility",
            "ownership",
            "stack",
            "architecture",
            "technology",
            "framework",
            "backend",
            "frontend",
            "agent",
        }
        requirements_keywords = {
            "requirement",
            "acceptance",
            "constraint",
            "scope",
            "priority",
            "goal",
            "user",
            "mvp",
        }

        if current_stage == Stage.TESTING:
            issues = test_report.get("issues", [])
            active_issues = [issue for issue in issues if issue_is_active(issue)]
            blocking_issues = [
                issue for issue in active_issues if issue_is_blocking(issue)
            ]

            if test_report.get("result") not in {"fail", "partial"}:
                return None, evidence

            if test_report.get("result") == "partial" and not active_issues:
                evidence.append(
                    "Stay on TESTING because validation is partial and issue attribution is incomplete."
                )
                return None, evidence

            requirements_failure = (
                not spec.get("acceptance_criteria")
                or bool(spec.get("open_questions"))
                or any(
                    contains_any(
                        collect_text(issue.get("title"), issue.get("notes")),
                        requirements_keywords,
                    )
                    for issue in blocking_issues
                )
            )
            if requirements_failure and blocking_issues:
                evidence.append(
                    "Testing indicates unstable requirements, constraints, or acceptance criteria."
                )
                return Stage.REQUIREMENTS, evidence

            design_failure = any(
                issue.get("related_contracts")
                or (
                    len(issue.get("related_modules", [])) > 1
                    and contains_any(
                        collect_text(issue.get("title"), issue.get("notes")),
                        design_keywords,
                    )
                )
                for issue in blocking_issues
            )
            if design_failure:
                evidence.append(
                    "Testing found contract, data flow, or module-boundary defects."
                )
                return Stage.DESIGN, evidence

            solution_failure = any(
                len(issue.get("related_modules", [])) > 1
                and not issue.get("related_contracts")
                for issue in blocking_issues
            )
            if not solution_failure:
                solution_failure = any(
                    len(issue.get("related_modules", [])) > 1
                    and contains_any(
                        collect_text(issue.get("title"), issue.get("notes")),
                        solution_keywords,
                    )
                    for issue in blocking_issues
                )
            if solution_failure:
                evidence.append(
                    "Testing indicates unstable module ownership or solution-level structure."
                )
                return Stage.SOLUTION, evidence

            implementation_failure = any(
                issue.get("related_modules") for issue in active_issues
            ) or bool(active_issues)
            if implementation_failure:
                evidence.append(
                    "Testing found issues that are still attributable to implementation."
                )
                return Stage.IMPLEMENTATION, evidence

            if implementation_status.get("implementation_status") != "done":
                evidence.append("Testing state exists but implementation is no longer done.")
                return Stage.IMPLEMENTATION, evidence

        if current_stage == Stage.IMPLEMENTATION:
            blockers = implementation_status.get("blockers", [])
            blocker_text = collect_text(
                implementation_status.get("known_limitations"),
                blockers,
            )

            if implementation_status.get("implementation_status") != "blocked":
                return None, evidence

            if not blockers:
                return None, evidence

            if contains_any(blocker_text, execution_keywords):
                evidence.append(
                    "Stay on IMPLEMENTATION because blockers look execution-related rather than upstream."
                )
                return None, evidence

            requirements_failure = (
                not spec.get("acceptance_criteria")
                or bool(spec.get("open_questions"))
                or contains_any(blocker_text, requirements_keywords)
            )
            if requirements_failure:
                evidence.append(
                    "Implementation is blocked by unstable requirements, constraints, or acceptance criteria."
                )
                return Stage.REQUIREMENTS, evidence

            solution_failure = (
                not solution.get("module_mapping")
                or any(
                    len(module.get("covers_requirements", [])) == 0
                    for module in solution.get("module_mapping", [])
                    if module.get("module")
                )
                or contains_any(blocker_text, solution_keywords)
            )
            if (
                not solution_failure
                and implementation_status.get("contract_compliance") is not False
                and contains_any(blocker_text, {"ownership", "responsibility"})
            ):
                solution_failure = True
            if solution_failure:
                evidence.append(
                    "Implementation is blocked by unstable module ownership or solution structure."
                )
                return Stage.SOLUTION, evidence

            design_failure = (
                implementation_status.get("contract_compliance") is False
                or not design.get("contracts")
                or not design.get("data_flow")
            )
            if not design_failure:
                design_failure = contains_any(blocker_text, design_keywords)
            if design_failure:
                evidence.append(
                    "Implementation is blocked by insufficient design contracts, flow, or structure."
                )
                return Stage.DESIGN, evidence

        if current_stage == Stage.DESIGN and not self.is_solution_ready(states):
            if self.is_requirements_ready(states):
                evidence.append("Design is no longer supported by a ready solution.")
                return Stage.SOLUTION, evidence
            evidence.append(
                "Design is no longer supported because requirements are also unstable."
            )
            return Stage.REQUIREMENTS, evidence

        if current_stage == Stage.SOLUTION and not self.is_requirements_ready(states):
            evidence.append("Solution is no longer supported by ready requirements.")
            return Stage.REQUIREMENTS, evidence

        return None, evidence

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
