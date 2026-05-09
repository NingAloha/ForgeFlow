from __future__ import annotations

from pydantic import Field

from .common import StateModel


class QuestionOptionModel(StateModel):
    label: str = ""
    value: str = ""
    hint: str = ""


class QuestionAnswerModel(StateModel):
    selected_values: list[str] = Field(default_factory=list)
    free_text: str = ""


class QuestionItemModel(StateModel):
    id: str = ""
    title: str = ""
    description: str = ""
    response_type: str = "single_select"
    options: list[QuestionOptionModel] = Field(default_factory=list)
    allow_free_text: bool = False
    answer: QuestionAnswerModel | None = None


class QuestionStateModel(StateModel):
    status: str = "idle"
    stage_name: str = ""
    state_key: str = ""
    blocking: bool = False
    questions: list[QuestionItemModel] = Field(default_factory=list)
    created_by: str = ""
    resolution_summary: str = ""
