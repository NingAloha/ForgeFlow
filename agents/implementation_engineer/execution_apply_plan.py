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


_REQUIRED_APPLY_PLAN_KEYS = (
    "apply_plan_status",
    "patch_id",
    "target_module",
    "files_to_create",
    "files_to_modify",
    "files_to_delete",
    "preconditions",
    "rollback_plan",
    "post_apply_test_plan",
    "gate_result",
    "mutation_performed",
)

_DISALLOWED_TEST_COMMAND_FRAGMENTS = (
    "rm -rf",
    "sudo",
    "curl",
    "bash",
    "pip install",
    "git push",
    "chmod -R",
)

_DENIED_PATH_FRAGMENTS = (
    ".git",
    ".github",
    ".env",
    "pyproject.toml",
)


def validate_apply_plan(
    apply_plan: dict[str, Any],
    contract: dict[str, Any],
    patch_draft: str,
) -> list[str]:
    issues: list[str] = []

    for key in _REQUIRED_APPLY_PLAN_KEYS:
        if key not in apply_plan:
            issues.append(f"missing required apply plan key: {key}")

    if issues:
        return issues

    expected_patch_id = build_contract_fingerprint(contract, patch_draft)
    if str(apply_plan.get("patch_id", "")) != expected_patch_id:
        issues.append("patch_id does not match execution contract fingerprint")

    target_module = str(contract.get("target_module", ""))
    if str(apply_plan.get("target_module", "")) != target_module:
        issues.append("target_module does not match execution contract")

    expected_create = _as_list(contract.get("create", []))
    files_to_create = _as_list(apply_plan.get("files_to_create", []))
    if files_to_create != expected_create:
        issues.append("files_to_create does not match execution contract create list")

    files_to_modify = _as_list(apply_plan.get("files_to_modify", []))
    files_to_delete = _as_list(apply_plan.get("files_to_delete", []))
    if files_to_modify or files_to_delete:
        issues.append("files_to_modify/delete must be empty for dry-run apply plan")

    gate_result = apply_plan.get("gate_result", {})
    gate_allowed = bool(gate_result.get("allowed")) if isinstance(gate_result, dict) else True
    gate_reason = str(gate_result.get("reason", "")) if isinstance(gate_result, dict) else ""
    if gate_allowed or gate_reason != "mutation runtime is not enabled":
        issues.append(
            "apply plan gate result must remain blocked while mutation runtime is disabled"
        )

    if bool(apply_plan.get("mutation_performed")):
        issues.append("apply plan must not perform mutation")

    if str(apply_plan.get("apply_plan_status", "")) != "blocked":
        issues.append("apply plan status must be blocked before mutation runtime exists")

    for command in _as_list(apply_plan.get("post_apply_test_plan", [])):
        normalized_command = command.lower()
        for fragment in _DISALLOWED_TEST_COMMAND_FRAGMENTS:
            if fragment in normalized_command:
                issues.append(f"post-apply test plan contains disallowed command: {fragment}")
                break

    allowed_paths = {
        f"src/{target_module}/README.md",
        f"tests/{target_module}/README.md",
    }
    for path in files_to_create:
        normalized_path = path.strip()
        if normalized_path not in allowed_paths:
            issues.append(f"apply plan path is outside allowed scope: {path}")
            continue
        lowered_path = normalized_path.lower()
        if lowered_path.startswith("/") or lowered_path.startswith("~") or ".." in normalized_path:
            issues.append(f"apply plan path is outside allowed scope: {path}")
            continue
        for denied_fragment in _DENIED_PATH_FRAGMENTS:
            if denied_fragment in lowered_path:
                issues.append(f"apply plan path is outside allowed scope: {path}")
                break

    return issues
