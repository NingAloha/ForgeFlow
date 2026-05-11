from __future__ import annotations

from ..common.text import TextHelper


class SolutionPlanningMixin(TextHelper):
    def _semantic_module_name(self, slug: str) -> str:
        if not slug:
            return "workflow_engine"
        banned = {"md", "core", "utils", "util", "misc", "module"}
        if slug in banned or len(slug) < 4:
            return f"{slug}_workflow_module" if slug else "workflow_engine"
        return slug

    def _module_tech_note(
        self, requirement: str, selected_stack: dict[str, str], module_name: str
    ) -> str:
        req = requirement.lower()
        backend = selected_stack.get("backend", "Python") or "Python"
        notes: list[str] = [f"tech={backend}"]
        if any(k in req for k in {"markdown", ".md"}):
            notes.append("library=markdown-it-py")
            notes.append(
                "reason=need robust markdown parsing for heading and section extraction"
            )
        elif any(k in req for k in {"summary", "summarize", "要点", "行动项"}):
            notes.append("library=regex+rule-based text splitter")
            notes.append(
                "reason=need deterministic extraction of key points and action items"
            )
        elif any(k in req for k in {"cli", "command", "terminal", "命令行"}):
            notes.append("library=argparse")
            notes.append("reason=need local command interface and argument validation")
        else:
            notes.append("library=python-standard-library")
            notes.append(
                "reason=map requirement to implementation module with minimal deps"
            )
        notes.append(f"module={module_name}")
        return "; ".join(notes)

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
                self.sentence_case(answers.get("backend_preference", "")) or "Python"
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
        if any(keyword in slug for keyword in {"markdown", "md_file", "markdown_file"}):
            return "markdown_parser"
        if any(
            keyword in slug
            for keyword in {"summary", "summarize", "key_point", "action_item"}
        ):
            return "summary_extractor"
        if any(
            keyword in slug for keyword in {"cli", "command", "terminal", "input_file"}
        ):
            return "cli_interface"
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
        return self._semantic_module_name(slug[:40])

    def build_module_mapping(
        self, spec: dict[str, object], selected_stack: dict[str, str]
    ) -> list[dict[str, object]]:
        requirements = [
            self.sentence_case(item)
            for item in spec.get("functional_requirements", [])
            if self.normalize_text(str(item))
        ]
        modules: dict[str, dict[str, object]] = {}
        for requirement in requirements:
            module_name = self._semantic_module_name(
                self.infer_module_name(requirement)
            )
            module = modules.setdefault(
                module_name,
                {
                    "module": module_name,
                    "responsibilities": [],
                    "covers_requirements": [],
                    "depends_on": [],
                    "tech_note": self._module_tech_note(
                        requirement=requirement,
                        selected_stack=selected_stack,
                        module_name=module_name,
                    ),
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
        requirements = " ".join(
            str(item).lower() for item in spec.get("functional_requirements", [])
        )
        constraints = " ".join(
            str(item).lower() for item in spec.get("constraints", [])
        )
        goal = str(spec.get("project_goal", "")).lower()
        context = " ".join([requirements, constraints, goal])

        if "markdown" in context or ".md" in context:
            risks.append(
                "Markdown input may contain irregular heading structure; parser fallback rules are needed."
            )
        if any(k in context for k in {"summary", "要点", "action", "行动项"}):
            risks.append(
                "Rule-based summarization may miss implicit action items in narrative paragraphs."
            )
        if "local" in context and selected_stack.get("deployment") == "Local CLI":
            risks.append(
                "Local file path handling may fail on invalid encodings or missing files."
            )
        return self.dedupe_items(risks)

    def build_alternatives(self, selected_stack: dict[str, str]) -> list[str]:
        alternatives: list[str] = []
        if selected_stack.get("frontend") == "CLI":
            alternatives.append(
                "Non-goal: do not build Web UI in this iteration; focus on local CLI interaction only."
            )
        if selected_stack.get("database") in {"SQLite", "JSON files"}:
            alternatives.append(
                "Non-goal: do not add database service; keep processing stateless per input markdown file."
            )
        if selected_stack.get("deployment") == "Local CLI":
            alternatives.append(
                "Non-goal: do not add background service or API server; single-process command execution only."
            )
        return self.dedupe_items(alternatives)
