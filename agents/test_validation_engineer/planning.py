from __future__ import annotations

from typing import Any


class TestValidationPlanningMixin:
    def build_issues(
        self,
        spec: dict[str, Any],
        implementation_status: dict[str, Any],
        design: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []

        if spec.get("open_questions"):
            issues.append(
                {
                    "title": "Requirements remain unresolved",
                    "severity": "critical",
                    "status": "open",
                    "related_modules": [implementation_status.get("module_name", "")],
                    "related_contracts": [],
                    "notes": "spec.open_questions is non-empty.",
                }
            )

        if implementation_status.get("implementation_status") != "done":
            issues.append(
                {
                    "title": "Implementation is not complete",
                    "severity": "high",
                    "status": "open",
                    "related_modules": [implementation_status.get("module_name", "")],
                    "related_contracts": [],
                    "notes": "implementation_status.implementation_status is not done.",
                }
            )

        blockers = implementation_status.get("blockers", [])
        if blockers:
            issues.append(
                {
                    "title": "Implementation has active blockers",
                    "severity": "high",
                    "status": "open",
                    "related_modules": [implementation_status.get("module_name", "")],
                    "related_contracts": [],
                    "notes": "; ".join(str(item) for item in blockers if item),
                }
            )

        if implementation_status.get("contract_compliance") is False:
            related_contracts = [
                str(contract.get("name", ""))
                for contract in design.get("contracts", [])
                if contract.get("name")
            ]
            issues.append(
                {
                    "title": "Contract compliance is broken",
                    "severity": "critical",
                    "status": "confirmed",
                    "related_modules": [implementation_status.get("module_name", "")],
                    "related_contracts": related_contracts,
                    "notes": "implementation_status.contract_compliance is false.",
                }
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
