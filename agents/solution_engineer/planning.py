from __future__ import annotations

from ..common.text import TextHelper


class SolutionPlanningMixin(TextHelper):
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
            if (
                "local" in context_text
                or "terminal" in context_text
                or "cli" in context_text
            ):
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
        slug = self.slugify_text(requirement)
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

    def build_module_mapping(
        self, spec: dict[str, object]
    ) -> list[dict[str, object]]:
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

    def build_risks(
        self, spec: dict[str, object], selected_stack: dict[str, str]
    ) -> list[str]:
        risks: list[str] = []
        if len(spec.get("functional_requirements", [])) > 3:
            risks.append(
                "Requirement scope may still be broad for a first deliverable."
            )
        if selected_stack.get("frontend") == "Textual":
            risks.append(
                "Terminal UX decisions may affect how quickly the first interaction loop stabilizes."
            )
        return self.dedupe_items(risks)

    def build_alternatives(self, selected_stack: dict[str, str]) -> list[str]:
        alternatives: list[str] = []
        if selected_stack.get("database") == "JSON files":
            alternatives.append(
                "Move to SQLite if local state management becomes too complex for flat files."
            )
        if selected_stack.get("frontend") == "Textual":
            alternatives.append(
                "Use a simpler plain CLI interface if terminal UI complexity slows delivery."
            )
        return self.dedupe_items(alternatives)
