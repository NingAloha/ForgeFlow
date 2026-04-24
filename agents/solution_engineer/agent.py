from __future__ import annotations

from ..base import AgentContext, AgentResult, BaseAgent
from .planning import SolutionPlanningMixin
from .questions import SolutionQuestionMixin


class SolutionEngineerAgent(SolutionPlanningMixin, SolutionQuestionMixin, BaseAgent):
    agent_name = "Solution Engineer"
    stage_name = "SOLUTION"
    state_key = "solution"

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        spec = dict(context.states.get("spec", {}))
        answers = self.extract_answers(context)

        if not (
            spec.get("project_goal")
            and spec.get("functional_requirements")
            and spec.get("acceptance_criteria")
        ):
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=current_state,
                summary="Solution work is blocked until requirements are stable.",
                notes=[
                    "Raised blocking solution questions because requirements are not ready for technical planning."
                ],
                blockers=["requirements_not_ready"],
                handoff_ready=False,
                question_state_update=self.build_clarifying_questions(),
                requires_user_input=True,
            )

        selected_stack = self.pick_stack(spec, answers, current_state)
        module_mapping = self.build_module_mapping(spec)
        updated_state = {
            **current_state,
            "selected_stack": selected_stack,
            "module_mapping": module_mapping,
            "risks": self.build_risks(spec, selected_stack),
            "alternatives": self.build_alternatives(selected_stack),
        }

        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Solution outline was generated from the current requirements state.",
            notes=[
                "Filled a first-pass technical stack and module mapping for downstream design work."
            ],
            handoff_ready=True,
        )
