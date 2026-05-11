from __future__ import annotations

from ..base import AgentContext, AgentResult, BaseAgent
from ..common import LLMGateway, PromptContract
from ..common.llm_policy import (
    resolve_gateway_failure,
    should_use_llm,
)
from ..common.runtime_config import LLMRuntimeConfig, load_llm_runtime_config
from schemas.llm_trace import EMPTY_LLM_TRACE, LLMTraceModel
from schemas.spec import SpecState
from .extraction import RequirementsExtractionMixin
from .questions import RequirementsQuestionMixin


class RequirementsEngineerAgent(
    RequirementsExtractionMixin, RequirementsQuestionMixin, BaseAgent
):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return load_llm_runtime_config()

    def get_llm_gateway(self) -> LLMGateway:
        return LLMGateway()

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        answers = self.extract_answers(context)
        user_input = context.user_input.strip()
        llm_config = self.get_llm_runtime_config()
        llm_trace: LLMTraceModel = EMPTY_LLM_TRACE
        llm_project_goal = ""
        llm_functional_requirements: list[str] = []
        llm_acceptance_criteria: list[str] = []
        llm_failure_result: AgentResult | None = None

        llm_stage_enabled = should_use_llm(llm_config, self.stage_name)
        if llm_stage_enabled and user_input:
            contract = PromptContract(
                stage_name=self.stage_name,
                system_prompt=(
                    "You extract requirement state as strict JSON. "
                    "Return only JSON with keys: project_goal, functional_requirements, acceptance_criteria."
                ),
                required_fields=[
                    "project_goal",
                    "functional_requirements",
                    "acceptance_criteria",
                ],
                output_model=SpecState,
            )
            llm_result = self.get_llm_gateway().generate(
                contract=contract,
                user_prompt=user_input,
                config=llm_config,
            )
            llm_trace = llm_result.to_trace()
            llm_failure_result = resolve_gateway_failure(
                llm_result=llm_result,
                llm_config=llm_config,
                stage_name=self.stage_name,
                state_key=self.state_key,
                agent_name=self.agent_name,
                updated_state={
                    **current_state,
                    "open_questions": ["llm_generation_failed"],
                },
                fallback_factory=None,
                strict_summary="Requirements blocked: strict_llm mode requires successful LLM output.",
                fatal_summary="Requirements blocked: LLM output is unavailable.",
            )
            # Requirements can still move forward in strict_llm mode when deterministic
            # extraction provides a complete spec from user input.
            if llm_failure_result is not None and llm_result.status in {
                "fatal_error",
                "needs_user_input",
            }:
                return llm_failure_result
            if llm_result.status == "success" and isinstance(
                llm_result.parsed_output, dict
            ):
                payload = llm_result.parsed_output
                llm_project_goal = self.normalize_text(
                    str(payload.get("project_goal", ""))
                )
                llm_functional_requirements = self.dedupe_items(
                    [str(item) for item in payload.get("functional_requirements", [])]
                )
                llm_acceptance_criteria = self.dedupe_items(
                    [str(item) for item in payload.get("acceptance_criteria", [])]
                )

        project_goal = self.normalize_text(str(current_state.get("project_goal", "")))
        if not project_goal:
            project_goal = self.sentence_case(llm_project_goal)
        if not project_goal:
            project_goal = self.extract_goal_from_input(answers.get("project_goal", ""))
        if not project_goal:
            project_goal = self.extract_goal_from_input(user_input)

        functional_requirements = list(current_state.get("functional_requirements", []))
        if not functional_requirements:
            functional_requirements = list(llm_functional_requirements)
        if not functional_requirements:
            functional_requirements = self.extract_requirements_from_input(
                answers.get("functional_requirements", "")
            )
        if not functional_requirements:
            functional_requirements = self.extract_requirements_from_input(user_input)
        if not functional_requirements and project_goal:
            functional_requirements = [
                f"Support the core workflow for {project_goal.lower()}"
            ]
        functional_requirements = self.dedupe_items(functional_requirements)

        acceptance_criteria = list(current_state.get("acceptance_criteria", []))
        if not acceptance_criteria:
            acceptance_criteria = list(llm_acceptance_criteria)
        if not acceptance_criteria:
            answered_acceptance = self.normalize_text(
                answers.get("acceptance_criteria", "")
            )
            if answered_acceptance:
                acceptance_criteria = [self.sentence_case(answered_acceptance)]
        if not acceptance_criteria:
            acceptance_criteria = self.derive_acceptance_criteria(
                project_goal, functional_requirements
            )
        acceptance_criteria = self.dedupe_items(acceptance_criteria)

        updated_state = {
            **current_state,
            "project_goal": project_goal,
            "functional_requirements": functional_requirements,
            "acceptance_criteria": acceptance_criteria,
            "open_questions": [],
        }

        if not project_goal or not functional_requirements or not acceptance_criteria:
            missing_fields: list[str] = []
            if not project_goal:
                missing_fields.append("project_goal")
            if not functional_requirements:
                missing_fields.append("functional_requirements")
            if not acceptance_criteria:
                missing_fields.append("acceptance_criteria")
            updated_state["open_questions"] = missing_fields
            if llm_failure_result is not None:
                return llm_failure_result
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=updated_state,
                summary="Requirements need clarification before spec can be completed.",
                notes=[
                    "Raised blocking requirement questions for missing core spec fields."
                ],
                blockers=missing_fields,
                handoff_ready=False,
                question_state_update=self.build_clarifying_questions(updated_state),
                requires_user_input=True,
                diagnostics={"llm_trace": llm_trace},
            )

        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Requirements were extracted into spec state.",
            notes=["Filled the core spec fields needed for downstream solution work."],
            handoff_ready=True,
            diagnostics={"llm_trace": llm_trace},
        )
