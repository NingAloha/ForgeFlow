from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..base import (
    AgentContext,
    AgentResult,
    QuestionAnswer,
    QuestionItem,
    QuestionOption,
    QuestionState,
)
from .models import Stage


class QuestionFlow:
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
            and question_state.get("status") == "awaiting_user"
            and question_state.get("questions")
        )
