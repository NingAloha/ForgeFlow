from __future__ import annotations

from typing import Any

from .execution_approval import build_contract_fingerprint
from .execution_gate import can_execute_contract


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def build_dry_run_apply_plan(
    contract: dict[str, Any],
    patch_draft: str,
    approval: dict[str, Any],
) -> dict[str, Any]:
    gate_result = can_execute_contract(contract, patch_draft, approval)

    files_to_create = _as_list(contract.get("create", []))
    files_to_modify = _as_list(contract.get("modify", []))
    files_to_delete = _as_list(contract.get("delete", []))
    post_apply_test_plan = _as_list(contract.get("test_plan", []))

    return {
        "apply_plan_status": "blocked",
        "patch_id": build_contract_fingerprint(contract, patch_draft),
        "target_module": str(contract.get("target_module", "")),
        "files_to_create": files_to_create,
        "files_to_modify": files_to_modify,
        "files_to_delete": files_to_delete,
        "preconditions": [
            "execution contract is valid",
            "approval artifact is valid",
            "approval status is approved",
            "mutation runtime is enabled",
            "workspace sandbox is available",
            "rollback snapshot can be created",
        ],
        "rollback_plan": [
            "create pre-patch snapshot",
            "record patch_id",
            "restore snapshot if post-apply validation fails",
        ],
        "post_apply_test_plan": post_apply_test_plan,
        "gate_result": gate_result,
        "mutation_performed": False,
    }
