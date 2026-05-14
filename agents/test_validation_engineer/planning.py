from __future__ import annotations

from typing import Any


class TestValidationPlanningMixin:
    def _handoff_files_evidence(
        self,
        implementation_status: dict[str, Any],
    ) -> list[str]:
        primary = implementation_status.get("files_touched", [])
        fallback = implementation_status.get("files_created", [])
        source = primary if primary else fallback
        return [str(item).strip() for item in source if str(item).strip()]

    def _handoff_tests_evidence(
        self,
        implementation_status: dict[str, Any],
    ) -> list[str]:
        primary = implementation_status.get("tests_added_or_updated", [])
        fallback = implementation_status.get("unit_tests", [])
        source = primary if primary else fallback
        return [str(item).strip() for item in source if str(item).strip()]

    def is_handoff_only_mode(
        self,
        implementation_status: dict[str, Any],
    ) -> bool:
        tests_added = self._handoff_tests_evidence(implementation_status)
        files_touched = self._handoff_files_evidence(implementation_status)
        commands_executed = [
            str(item).strip()
            for item in implementation_status.get("commands_executed", [])
            if str(item).strip()
        ]
        artifacts_generated = [
            str(item).strip()
            for item in implementation_status.get("artifacts_generated", [])
            if str(item).strip()
        ]
        workspace_path = str(implementation_status.get("workspace_path", "")).strip()
        blockers = implementation_status.get("blockers", [])
        allowed_handoff_artifacts = {"handoff_package_generated"}
        artifacts_are_handoff_markers = all(
            item in allowed_handoff_artifacts for item in artifacts_generated
        )
        return (
            implementation_status.get("implementation_status") == "done"
            and implementation_status.get("contract_compliance") is True
            and not blockers
            and bool(files_touched)
            and bool(tests_added)
            and not workspace_path
            and not commands_executed
            and artifacts_are_handoff_markers
        )

    def _build_issue(
        self,
        *,
        title: str,
        severity: str,
        status: str,
        related_modules: list[str],
        related_contracts: list[str],
        notes: str,
        attribution: str,
        error_category: str,
    ) -> dict[str, Any]:
        tagged_notes = (
            f"attribution={attribution}; error_category={error_category}; {notes}"
        )
        return {
            "title": title,
            "severity": severity,
            "status": status,
            "related_modules": related_modules,
            "related_contracts": related_contracts,
            "notes": tagged_notes,
        }

    def build_issues(
        self,
        spec: dict[str, Any],
        implementation_status: dict[str, Any],
        design: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        module_name = str(implementation_status.get("module_name", "")).strip()
        contract_names = [
            str(contract.get("name", "")).strip()
            for contract in design.get("contracts", [])
            if str(contract.get("name", "")).strip()
        ]
        project_modules = [
            str(name).strip()
            for name in design.get("project_structure", {}).get("modules", [])
            if str(name).strip()
        ]
        tests_added = self._handoff_tests_evidence(implementation_status)
        handoff_only_mode = self.is_handoff_only_mode(implementation_status)

        if spec.get("open_questions"):
            issues.append(
                self._build_issue(
                    title="Requirements remain unresolved",
                    severity="critical",
                    status="open",
                    related_modules=[module_name],
                    related_contracts=[],
                    notes="spec.open_questions is non-empty.",
                    attribution="contract",
                    error_category="input_errors",
                )
            )

        if implementation_status.get("implementation_status") != "done":
            issues.append(
                self._build_issue(
                    title="Implementation is not complete",
                    severity="high",
                    status="open",
                    related_modules=[module_name],
                    related_contracts=[],
                    notes="implementation_status.implementation_status is not done.",
                    attribution="implementation",
                    error_category="processing_errors",
                )
            )

        blockers = implementation_status.get("blockers", [])
        if blockers:
            issues.append(
                self._build_issue(
                    title="Implementation has active blockers",
                    severity="high",
                    status="open",
                    related_modules=[module_name],
                    related_contracts=[],
                    notes="; ".join(str(item) for item in blockers if item),
                    attribution="implementation",
                    error_category="processing_errors",
                )
            )

        if implementation_status.get("contract_compliance") is False:
            issues.append(
                self._build_issue(
                    title="Contract compliance is broken",
                    severity="critical",
                    status="confirmed",
                    related_modules=[module_name],
                    related_contracts=contract_names,
                    notes="implementation_status.contract_compliance is false.",
                    attribution="contract",
                    error_category="processing_errors",
                )
            )

        if module_name and project_modules and module_name not in project_modules:
            issues.append(
                self._build_issue(
                    title="Implementation module is outside design structure",
                    severity="high",
                    status="open",
                    related_modules=[module_name],
                    related_contracts=[],
                    notes="implementation_status.module_name is not listed in system_design.project_structure.modules.",
                    attribution="structure",
                    error_category="processing_errors",
                )
            )

        if contract_names and not tests_added:
            issues.append(
                self._build_issue(
                    title="No tests recorded for contract validation",
                    severity="high",
                    status="open",
                    related_modules=[module_name],
                    related_contracts=contract_names,
                    notes="implementation_status.tests_added_or_updated is empty.",
                    attribution="contract",
                    error_category="output_errors",
                )
            )

        if (
            design.get("mvp_plan", {}).get("first_deliverable")
            and not implementation_status.get("suggested_test_command")
            and not handoff_only_mode
        ):
            issues.append(
                self._build_issue(
                    title="Missing verification command for MVP deliverable",
                    severity="medium",
                    status="open",
                    related_modules=[module_name],
                    related_contracts=[],
                    notes="implementation_status.suggested_test_command is empty.",
                    attribution="structure",
                    error_category="output_errors",
                )
            )

        return [
            issue
            for issue in issues
            if issue.get("related_modules") != [""]
            or issue.get("related_contracts")
            or issue.get("notes")
        ]

    def pick_result(
        self,
        issues: list[dict[str, Any]],
        implementation_status: dict[str, Any],
    ) -> str:
        if not issues:
            return "pass"

        has_critical_or_high = any(
            issue.get("severity") in {"critical", "high"}
            and issue.get("status") in {"open", "confirmed"}
            for issue in issues
        )
        if has_critical_or_high:
            return "fail"

        if implementation_status.get("implementation_status") == "done":
            return "partial"
        return "not_run"
