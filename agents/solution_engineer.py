from __future__ import annotations

import re

from .base import AgentContext, AgentResult, BaseAgent, QuestionItem, QuestionState


class SolutionEngineerAgent(BaseAgent):
    agent_name = "Solution Engineer"
    stage_name = "SOLUTION"
    state_key = "solution"

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

    def slugify_requirement(self, requirement: str) -> str:
        text = self.normalize_text(requirement).lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")

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

    def pick_stack(
        self,
        spec: dict[str, object],
        answers: dict[str, str],
        current_state: dict[str, object],
    ) -> dict[str, str]:
        selected_stack = dict(current_state.get("selected_stack", {}))
        goal_text = self.normalize_text(str(spec.get("project_goal", ""))).lower()
        requirements_text = " ".join(spec.get("functional_requirements", []))
        constraints_text = " ".join(spec.get("constraints", []))
        preferences_text = " ".join(spec.get("preferences", []))
        context_text = " ".join(
            [
                goal_text,
                requirements_text.lower(),
                constraints_text.lower(),
                preferences_text.lower(),
                answers.get("interaction_surface", "").lower(),
                answers.get("backend_preference", "").lower(),
            ]
        )

        if not selected_stack.get("backend"):
            selected_stack["backend"] = (
                self.sentence_case(answers.get("backend_preference", ""))
                or "Python"
            )

        if not selected_stack.get("frontend"):
            if any(
                keyword in context_text
                for keyword in {"chat", "terminal", "cli", "tui", "textual"}
            ):
                selected_stack["frontend"] = "Textual"
            else:
                selected_stack["frontend"] = "CLI"

        if not selected_stack.get("database"):
            if any(
                keyword in context_text
                for keyword in {"structured", "state", "workflow", "local"}
            ):
                selected_stack["database"] = "JSON files"
            else:
                selected_stack["database"] = "SQLite"

        if not selected_stack.get("agent_framework"):
            if "agent" in context_text or "workflow" in context_text:
                selected_stack["agent_framework"] = "Custom orchestrator"
            else:
                selected_stack["agent_framework"] = ""

        if not selected_stack.get("deployment"):
            if "local" in context_text or "terminal" in context_text or "cli" in context_text:
                selected_stack["deployment"] = "Local CLI"
            else:
                selected_stack["deployment"] = "Local app"

        return {
            "frontend": selected_stack.get("frontend", ""),
            "backend": selected_stack.get("backend", ""),
            "database": selected_stack.get("database", ""),
            "agent_framework": selected_stack.get("agent_framework", ""),
            "deployment": selected_stack.get("deployment", ""),
        }

    def infer_module_name(self, requirement: str) -> str:
        slug = self.slugify_requirement(requirement)
        if any(keyword in slug for keyword in {"requirement", "spec"}):
            return "requirements_engine"
        if any(keyword in slug for keyword in {"solution", "plan", "design"}):
            return "planning_engine"
        if any(keyword in slug for keyword in {"implement", "progress", "track"}):
            return "execution_tracker"
        if any(keyword in slug for keyword in {"test", "validate"}):
            return "validation_engine"
        if any(keyword in slug for keyword in {"chat", "user", "input"}):
            return "interaction_layer"
        return slug[:40] or "workflow_core"

    def build_module_mapping(self, spec: dict[str, object]) -> list[dict[str, object]]:
        requirements = [
            self.sentence_case(item)
            for item in spec.get("functional_requirements", [])
            if self.normalize_text(str(item))
        ]
        modules: dict[str, dict[str, object]] = {}
        for requirement in requirements:
            module_name = self.infer_module_name(requirement)
            module = modules.setdefault(
                module_name,
                {
                    "module": module_name,
                    "responsibilities": [],
                    "covers_requirements": [],
                    "depends_on": [],
                    "tech_note": "",
                },
            )
            module["responsibilities"] = self.dedupe_items(
                list(module["responsibilities"]) + [requirement]
            )
            module["covers_requirements"] = self.dedupe_items(
                list(module["covers_requirements"]) + [requirement]
            )

        ordered_modules = sorted(
            modules.values(),
            key=lambda item: str(item.get("module", "")),
        )

        if len(ordered_modules) > 1:
            first_module_name = str(ordered_modules[0]["module"])
            for module in ordered_modules[1:]:
                module["depends_on"] = self.dedupe_items(
                    list(module.get("depends_on", [])) + [first_module_name]
                )

        return ordered_modules

    def build_risks(self, spec: dict[str, object], selected_stack: dict[str, str]) -> list[str]:
        risks: list[str] = []
        if len(spec.get("functional_requirements", [])) > 3:
            risks.append("Requirement scope may still be broad for a first deliverable.")
        if selected_stack.get("frontend") == "Textual":
            risks.append("Terminal UX decisions may affect how quickly the first interaction loop stabilizes.")
        return self.dedupe_items(risks)

    def build_alternatives(self, selected_stack: dict[str, str]) -> list[str]:
        alternatives: list[str] = []
        if selected_stack.get("database") == "JSON files":
            alternatives.append("Move to SQLite if local state management becomes too complex for flat files.")
        if selected_stack.get("frontend") == "Textual":
            alternatives.append("Use a simpler plain CLI interface if terminal UI complexity slows delivery.")
        return self.dedupe_items(alternatives)

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
