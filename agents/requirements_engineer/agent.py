from __future__ import annotations

from ..base import AgentContext, AgentResult, BaseAgent
from ..common.llm_adapter import LLMAdapter
from ..common.runtime_config import LLMRuntimeConfig, load_llm_runtime_config
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

    def get_llm_adapter(self) -> LLMAdapter:
        return LLMAdapter()

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        answers = self.extract_answers(context)
        user_input = context.user_input.strip()
        llm_config = self.get_llm_runtime_config()
        llm_trace = {
            "enabled": llm_config.enabled,
            "provider": llm_config.provider,
            "model": llm_config.model,
            "protocol": llm_config.protocol,
            "used": False,
            "fallback_used": False,
            "error": "",
            "latency_ms": 0,
        }
        llm_project_goal = ""
        llm_functional_requirements: list[str] = []
        llm_acceptance_criteria: list[str] = []

        if llm_config.enabled and user_input:
            llm_result = self.get_llm_adapter().generate_requirements(
                user_input=user_input,
                config=llm_config,
            )
            llm_trace["used"] = True
            llm_trace["latency_ms"] = llm_result.latency_ms
            llm_trace["error"] = llm_result.error
            if llm_result.ok:
                llm_project_goal = self.normalize_text(
                    str(llm_result.content.get("project_goal", ""))
                )
                llm_functional_requirements = self.dedupe_items(
                    [
                        str(item)
                        for item in llm_result.content.get(
                            "functional_requirements", []
                        )
                    ]
                )
                llm_acceptance_criteria = self.dedupe_items(
                    [
                        str(item)
                        for item in llm_result.content.get("acceptance_criteria", [])
                    ]
                )
                if (
                    not llm_project_goal
                    or not llm_functional_requirements
                    or not llm_acceptance_criteria
                ):
                    llm_trace["fallback_used"] = True
                    llm_trace["error"] = "LLM response missing required fields."
            else:
                llm_trace["fallback_used"] = True

        project_goal = self.normalize_text(str(current_state.get("project_goal", "")))
        if not project_goal:
            project_goal = self.sentence_case(llm_project_goal)
        if not project_goal:
            project_goal = self.extract_goal_from_input(answers.get("project_goal", ""))
        if not project_goal:
            project_goal = self.extract_goal_from_input(user_input)

        functional_requirements = list(
            current_state.get("functional_requirements", [])
        )
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
            notes=[
                "Filled the core spec fields needed for downstream solution work."
            ],
            handoff_ready=True,
            diagnostics={"llm_trace": llm_trace},
        )
