from __future__ import annotations

from copy import deepcopy

from agents.base import AgentResult, BaseAgent, QuestionItem, QuestionState


class InMemoryStateManager:
    def __init__(self, states: dict[str, dict]) -> None:
        self.states = deepcopy(states)
        self.saved_states: dict[str, dict] = {}

    def load_all_states(self) -> dict[str, dict]:
        return deepcopy(self.states)

    def save_state(self, state_key: str, payload: dict) -> None:
        self.saved_states[state_key] = deepcopy(payload)
        self.states[state_key] = deepcopy(payload)


class QuestionAskingAgent(BaseAgent):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def run(self, context):  # type: ignore[override]
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=dict(context.states.get("spec", {})),
            summary="Need user clarification before proceeding.",
            question_state_update=QuestionState(
                status="awaiting_user",
                stage_name=self.stage_name,
                state_key=self.state_key,
                blocking=True,
                questions=[
                    QuestionItem(
                        id="target-user",
                        title="Who is the first target user?",
                        description="Need one concrete initial user persona.",
                    )
                ],
                created_by=self.agent_name,
            ),
            requires_user_input=True,
        )


class AnswerConsumingAgent(BaseAgent):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def run(self, context):  # type: ignore[override]
        updated_state = dict(context.states.get("spec", {}))
        updated_state["target_users"] = ["indie_hacker"]
        updated_state["open_questions"] = []
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Consumed answered question and updated spec.",
        )


class ReaskingAgent(BaseAgent):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def run(self, context):  # type: ignore[override]
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=dict(context.states.get("spec", {})),
            summary="Need one more clarification round.",
            question_state_update=QuestionState(
                status="awaiting_user",
                stage_name=self.stage_name,
                state_key=self.state_key,
                blocking=True,
                questions=[
                    QuestionItem(
                        id="target-user-followup",
                        title="What is the user's biggest pain point?",
                        description="Need a sharper first-use-case boundary.",
                    )
                ],
                created_by=self.agent_name,
            ),
            requires_user_input=True,
        )
