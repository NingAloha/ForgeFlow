from __future__ import annotations

from typing import Any, Callable

from .models import Stage


class BackflowEvaluator:
    def __init__(
        self,
        is_requirements_ready: Callable[[dict[str, dict[str, Any]]], bool],
        is_solution_ready: Callable[[dict[str, dict[str, Any]]], bool],
    ) -> None:
        self.is_requirements_ready = is_requirements_ready
        self.is_solution_ready = is_solution_ready

    def evaluate(
        self,
        states: dict[str, dict[str, Any]],
        current_stage: Stage,
    ) -> tuple[Stage | None, list[str]]:
        evidence: list[str] = []
        spec = states.get("spec", {})
        solution = states.get("solution", {})
        design = states.get("system_design", {})
        implementation_status = states.get("implementation_status", {})
        test_report = states.get("test_report", {})

        def issue_is_active(issue: dict[str, Any]) -> bool:
            return issue.get("status") in {"open", "confirmed"}

        def issue_is_blocking(issue: dict[str, Any]) -> bool:
            return issue.get("severity") in {"high", "critical"}

        def collect_text(*parts: Any) -> str:
            return " ".join(str(part).lower() for part in parts if part)

        def contains_any(text: str, keywords: set[str]) -> bool:
            return any(keyword in text for keyword in keywords)

        execution_keywords = {
            "environment",
            "dependency",
            "dependencies",
            "tool",
            "toolchain",
            "permission",
            "resource",
            "local",
            "install",
            "network",
            "dns",
            "sandbox",
            "runtime",
        }
        design_keywords = {
            "contract",
            "input",
            "output",
            "schema",
            "data flow",
            "trigger",
            "producer",
            "consumer",
            "boundary",
            "interface",
            "project structure",
            "directory",
        }
        solution_keywords = {
            "module",
            "responsibility",
            "ownership",
            "stack",
            "architecture",
            "technology",
            "framework",
            "backend",
            "frontend",
            "agent",
        }
        requirements_keywords = {
            "requirement",
            "acceptance",
            "constraint",
            "scope",
            "priority",
            "goal",
            "user",
            "mvp",
        }

        if current_stage == Stage.TESTING:
            issues = test_report.get("issues", [])
            active_issues = [issue for issue in issues if issue_is_active(issue)]
            blocking_issues = [
                issue for issue in active_issues if issue_is_blocking(issue)
            ]

            if test_report.get("result") not in {"fail", "partial"}:
                return None, evidence

            if test_report.get("result") == "partial" and not active_issues:
                evidence.append(
                    "Stay on TESTING because validation is partial and issue attribution is incomplete."
                )
                return None, evidence

            requirements_failure = (
                not spec.get("acceptance_criteria")
                or bool(spec.get("open_questions"))
                or any(
                    contains_any(
                        collect_text(issue.get("title"), issue.get("notes")),
                        requirements_keywords,
                    )
                    for issue in blocking_issues
                )
            )
            if requirements_failure and blocking_issues:
                evidence.append(
                    "Testing indicates unstable requirements, constraints, or acceptance criteria."
                )
                return Stage.REQUIREMENTS, evidence

            design_failure = any(
                issue.get("related_contracts")
                or (
                    len(issue.get("related_modules", [])) > 1
                    and contains_any(
                        collect_text(issue.get("title"), issue.get("notes")),
                        design_keywords,
                    )
                )
                for issue in blocking_issues
            )
            if design_failure:
                evidence.append(
                    "Testing found contract, data flow, or module-boundary defects."
                )
                return Stage.DESIGN, evidence

            solution_failure = any(
                len(issue.get("related_modules", [])) > 1
                and not issue.get("related_contracts")
                for issue in blocking_issues
            )
            if not solution_failure:
                solution_failure = any(
                    len(issue.get("related_modules", [])) > 1
                    and contains_any(
                        collect_text(issue.get("title"), issue.get("notes")),
                        solution_keywords,
                    )
                    for issue in blocking_issues
                )
            if solution_failure:
                evidence.append(
                    "Testing indicates unstable module ownership or solution-level structure."
                )
                return Stage.SOLUTION, evidence

            implementation_failure = any(
                issue.get("related_modules") for issue in active_issues
            ) or bool(active_issues)
            if implementation_failure:
                evidence.append(
                    "Testing found issues that are still attributable to implementation."
                )
                return Stage.IMPLEMENTATION, evidence

            if implementation_status.get("implementation_status") != "done":
                evidence.append(
                    "Testing state exists but implementation is no longer done."
                )
                return Stage.IMPLEMENTATION, evidence

        if current_stage == Stage.IMPLEMENTATION:
            blockers = implementation_status.get("blockers", [])
            blocker_text = collect_text(
                implementation_status.get("known_limitations"),
                blockers,
            )

            if implementation_status.get("implementation_status") != "blocked":
                return None, evidence

            if not blockers:
                return None, evidence

            if contains_any(blocker_text, execution_keywords):
                evidence.append(
                    "Stay on IMPLEMENTATION because blockers look execution-related rather than upstream."
                )
                return None, evidence

            requirements_failure = (
                not spec.get("acceptance_criteria")
                or bool(spec.get("open_questions"))
                or contains_any(blocker_text, requirements_keywords)
            )
            if requirements_failure:
                evidence.append(
                    "Implementation is blocked by unstable requirements, constraints, or acceptance criteria."
                )
                return Stage.REQUIREMENTS, evidence

            solution_failure = (
                not solution.get("module_mapping")
                or any(
                    len(module.get("covers_requirements", [])) == 0
                    for module in solution.get("module_mapping", [])
                    if module.get("module")
                )
                or contains_any(blocker_text, solution_keywords)
            )
            if (
                not solution_failure
                and implementation_status.get("contract_compliance") is not False
                and contains_any(blocker_text, {"ownership", "responsibility"})
            ):
                solution_failure = True
            if solution_failure:
                evidence.append(
                    "Implementation is blocked by unstable module ownership or solution structure."
                )
                return Stage.SOLUTION, evidence

            design_failure = (
                implementation_status.get("contract_compliance") is False
                or not design.get("contracts")
                or not design.get("data_flow")
            )
            if not design_failure:
                design_failure = contains_any(blocker_text, design_keywords)
            if design_failure:
                evidence.append(
                    "Implementation is blocked by insufficient design contracts, flow, or structure."
                )
                return Stage.DESIGN, evidence

        if current_stage == Stage.DESIGN and not self.is_solution_ready(states):
            if self.is_requirements_ready(states):
                evidence.append("Design is no longer supported by a ready solution.")
                return Stage.SOLUTION, evidence
            evidence.append(
                "Design is no longer supported because requirements are also unstable."
            )
            return Stage.REQUIREMENTS, evidence

        if current_stage == Stage.SOLUTION and not self.is_requirements_ready(states):
            evidence.append("Solution is no longer supported by ready requirements.")
            return Stage.REQUIREMENTS, evidence

        return None, evidence
