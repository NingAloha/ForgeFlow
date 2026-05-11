from __future__ import annotations

from typing import Any

from .execution_approval_store import validate_approval_artifact
from .execution_contract import validate_execution_contract


def can_execute_contract(
    contract: dict[str, Any],
    patch_draft: str,
    approval: dict[str, Any],
) -> dict[str, Any]:
    contract_issues = validate_execution_contract(contract, patch_draft)
    if contract_issues:
        return {
            "allowed": False,
            "reason": "execution contract is invalid",
            "issues": contract_issues,
        }

    if not approval:
        return {
            "allowed": False,
            "reason": "approval is missing",
            "issues": [],
        }

    if bool(approval.get("stale", False)):
        return {
            "allowed": False,
            "reason": "approval is stale",
            "issues": [],
        }

    approval_issues = validate_approval_artifact(approval, contract, patch_draft)
    if approval_issues:
        return {
            "allowed": False,
            "reason": "approval is invalid",
            "issues": approval_issues,
        }

    if str(approval.get("approval_status", "")) != "approved":
        return {
            "allowed": False,
            "reason": "approval status is not approved",
            "issues": [],
        }

    return {
        "allowed": False,
        "reason": "mutation runtime is not enabled",
        "issues": [],
    }
