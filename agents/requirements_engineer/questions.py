from __future__ import annotations

from ..base import AgentContext, QuestionItem, QuestionState


class RequirementsQuestionMixin:
    stage_name: str
    state_key: str
    agent_name: str

    def extract_answers(self, context: AgentContext) -> dict[str, str]:
        question_state = context.question_state
        if (
            question_state is None
            or question_state.status != "answered"
            or question_state.stage_name != self.stage_name
            or question_state.state_key != self.state_key
        ):
            return {}

        answers: dict[str, str] = {}
        for question in question_state.questions:
            if question.answer is None:
                continue
            value = question.answer.free_text.strip()
            if not value and question.answer.selected_values:
                value = ", ".join(question.answer.selected_values)
            if value:
                answers[question.id] = value
        return answers

    def build_clarifying_questions(
        self, current_state: dict[str, object]
    ) -> QuestionState:
        return QuestionState(
            status="awaiting_user",
            stage_name=self.stage_name,
            state_key=self.state_key,
            blocking=True,
            questions=[
                QuestionItem(
                    id="project_goal",
                    title="What are we building?",
                    description="Describe the primary project goal in one sentence.",
                    response_type="free_text",
                    allow_free_text=True,
                ),
                QuestionItem(
                    id="functional_requirements",
                    title="What must it do?",
                    description="List the core capabilities or workflow steps the system must support.",
                    response_type="free_text",
                    allow_free_text=True,
                ),
                QuestionItem(
                    id="acceptance_criteria",
                    title="How will we know it works?",
                    description="Describe the acceptance signal or concrete success criteria for the first deliverable.",
                    response_type="free_text",
                    allow_free_text=True,
                ),
            ],
            created_by=self.agent_name,
        )
