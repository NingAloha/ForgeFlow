from __future__ import annotations

from ..base import AgentContext, QuestionItem, QuestionState


class SolutionQuestionMixin:
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

    def build_clarifying_questions(self) -> QuestionState:
        return QuestionState(
            status="awaiting_user",
            stage_name=self.stage_name,
            state_key=self.state_key,
            blocking=True,
            questions=[
                QuestionItem(
                    id="backend_preference",
                    title="What backend constraint should guide the solution?",
                    description="Describe any required language, runtime, or backend platform preference.",
                    response_type="free_text",
                    allow_free_text=True,
                ),
                QuestionItem(
                    id="interaction_surface",
                    title="What interaction surface should we prioritize?",
                    description="Describe whether the first delivery should optimize for CLI, TUI, web, or another surface.",
                    response_type="free_text",
                    allow_free_text=True,
                ),
            ],
            created_by=self.agent_name,
        )
