from __future__ import annotations

import re
from typing import Any

CONTRACT_BEGIN = "BEGIN_EXECUTION_CONTRACT"
CONTRACT_END = "END_EXECUTION_CONTRACT"
DRAFT_BEGIN = "BEGIN_PATCH_DRAFT"
DRAFT_END = "END_PATCH_DRAFT"

REQUIRED_KEYS = [
    "execution_contract_version",
    "execution_intent",
    "mutation_performed",
    "target_module",
    "plan_type",
    "create",
    "modify",
    "delete",
    "rationale",
    "risk",
    "test_plan",
    "rollback_expectation",
]


def _extract_block(text: str, begin: str, end: str) -> tuple[str, bool]:
    pattern = rf"{re.escape(begin)}\n(.*?)\n{re.escape(end)}"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return "", False
    return match.group(1).strip(), True


def _parse_list_value(raw: str) -> list[str]:
    value = raw.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return [value] if value else []
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [item.strip() for item in inner.split(",") if item.strip()]


def parse_execution_contract(notes: str) -> dict[str, Any]:
    block, present = _extract_block(notes, CONTRACT_BEGIN, CONTRACT_END)
    contract: dict[str, Any] = {"_contract_boundary_present": present}
    if not present:
        return contract

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in {"create", "modify", "delete", "test_plan"}:
            contract[key] = _parse_list_value(value)
        else:
            contract[key] = value
    return contract


def parse_patch_draft(notes: str) -> str:
    block, _present = _extract_block(notes, DRAFT_BEGIN, DRAFT_END)
    return block


def validate_execution_contract(
    contract: dict[str, Any], patch_draft: str
) -> list[str]:
    issues: list[str] = []

    if not contract.get("_contract_boundary_present"):
        issues.append("missing execution contract boundary")
    if not patch_draft:
        issues.append("missing patch draft boundary")

    for key in REQUIRED_KEYS:
        if key not in contract:
            issues.append(f"missing required contract key: {key}")

    if contract.get("mutation_performed", "").strip().lower() != "false":
        issues.append("mutation must be disabled for review-only contract")

    modify = contract.get("modify", [])
    delete = contract.get("delete", [])
    if modify or delete:
        issues.append("modify/delete must be empty for current patch draft contract")

    target_module = str(contract.get("target_module", "")).strip()
    create_paths = contract.get("create", [])
    if not isinstance(create_paths, list):
        create_paths = []

    allowed_paths = {
        f"src/{target_module}/README.md",
        f"tests/{target_module}/README.md",
    }

    for path in create_paths:
        path_str = str(path).strip()
        if not path_str:
            continue

        if path_str not in allowed_paths:
            issues.append(f"create path is outside allowlist: {path_str}")

        denied_hit = any(
            token in path_str
            for token in [".git", ".github", ".env", "pyproject.toml", "~"]
        )
        if denied_hit or path_str.startswith("/"):
            issues.append(f"create path uses denied scope: {path_str}")

    draft = patch_draft
    if draft:
        if "diff --git" not in draft:
            issues.append("patch draft is not unified diff")
        if "new file mode 100644" not in draft:
            issues.append("patch draft must be create-only with new file mode")
        if "deleted file mode" in draft:
            issues.append("patch draft must not delete files")
        if "rename from" in draft or "rename to" in draft:
            issues.append("patch draft must not rename files")
        if ".py" in draft:
            issues.append("patch draft must not include python files")
        if "import " in draft or "class " in draft or "def " in draft:
            issues.append("patch draft must not include python code constructs")

        for path in create_paths:
            path_str = str(path).strip()
            expected_marker = f"+++ b/{path_str}"
            if path_str and expected_marker not in draft:
                issues.append(
                    f"patch draft does not cover declared create path: {path_str}"
                )

    return issues
