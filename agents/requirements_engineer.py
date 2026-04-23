from __future__ import annotations

import re

from .base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    QuestionItem,
    QuestionState,
)


class RequirementsEngineerAgent(BaseAgent):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def normalize_text(self, value: str) -> str:
        text = re.sub(r"\s+", " ", value).strip()
        return text.strip(" \t\r\n-*:;,.")

    def sentence_case(self, value: str) -> str:
        text = self.normalize_text(value)
        if not text:
            return ""
        return text[0].upper() + text[1:]

    def dedupe_items(self, items: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for item in items:
            normalized = self.normalize_text(item)
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(self.sentence_case(normalized))
        return deduped

    def extract_goal_from_input(self, user_input: str) -> str:
        text = self.normalize_text(user_input)
        if not text:
            return ""
        text = re.sub(
            r"^(please\s+)?(help me\s+)?(build|create|make|design|develop)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"^(i want to|we need to|need to|want to)\s+", "", text, flags=re.IGNORECASE)
        text = self.normalize_text(text)
        if not text:
            return ""
        return self.sentence_case(text)

    def extract_requirements_from_input(self, user_input: str) -> list[str]:
        text = user_input.strip()
        if not text:
            return []

        bullet_candidates: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^([-*]|\d+\.)\s+", stripped):
                bullet_candidates.append(
                    re.sub(r"^([-*]|\d+\.)\s+", "", stripped)
                )
        if bullet_candidates:
            return self.dedupe_items(bullet_candidates)

        normalized = re.sub(r"\s+", " ", text)
        clauses = re.split(r"[。\n.;；]|(?:\s+and\s+)|(?:\s+then\s+)", normalized)
        candidates: list[str] = []
        for clause in clauses:
            cleaned = self.normalize_text(clause)
            if len(cleaned.split()) < 2:
                continue
            cleaned = re.sub(
                r"^(please\s+)?(help me\s+)?(build|create|make|design|develop)\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(
                r"^(i want to|we need to|need to|want to)\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            if len(cleaned.split()) < 2:
                continue
            candidates.append(cleaned)
        return self.dedupe_items(candidates)

    def derive_acceptance_criteria(
        self, project_goal: str, functional_requirements: list[str]
    ) -> list[str]:
        criteria: list[str] = []
        for requirement in functional_requirements[:3]:
            criteria.append(f"The system can {requirement[0].lower() + requirement[1:]}.")
        if not criteria and project_goal:
            criteria.append(
                f"The delivered workflow satisfies the core goal: {project_goal[0].lower() + project_goal[1:]}."
            )
        return self.dedupe_items(criteria)

    def extract_answers(
        self, context: AgentContext
    ) -> dict[str, str]:
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

    def build_clarifying_questions(self, current_state: dict[str, object]) -> QuestionState:
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

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        answers = self.extract_answers(context)
        user_input = context.user_input.strip()

        project_goal = self.normalize_text(str(current_state.get("project_goal", "")))
        if not project_goal:
            project_goal = self.extract_goal_from_input(answers.get("project_goal", ""))
        if not project_goal:
            project_goal = self.extract_goal_from_input(user_input)

        functional_requirements = list(
            current_state.get("functional_requirements", [])
        )
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
        )
