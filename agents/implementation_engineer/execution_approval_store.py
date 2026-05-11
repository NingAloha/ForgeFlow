from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .execution_approval import build_contract_fingerprint

ALLOWED_APPROVAL_STATUSES = {"pending", "approved", "rejected", "invalidated"}
REQUIRED_APPROVAL_KEYS = [
    "approval_status",
    "contract_hash",
    "contract_version",
    "target_module",
    "review_decision",
    "review_reason",
    "approved_at",
    "approved_by",
    "stale",
]


def _is_hex_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


def build_approval_artifact_path(run_dir: Path, contract_hash: str) -> Path:
    safe_hash = contract_hash.strip().lower()
    if not _is_hex_sha256(safe_hash):
        raise ValueError("contract_hash must be a lowercase sha256 hex digest")

    base = run_dir.resolve()
    approvals_dir = base / "approvals"
    return approvals_dir / f"{safe_hash}.json"


def save_approval_artifact_for_run(
    run_dir: Path,
    contract_hash: str,
    approval: dict[str, Any],
) -> Path:
    path = build_approval_artifact_path(run_dir, contract_hash)
    save_approval_artifact(path, approval)
    return path


def save_approval_artifact(path: Path, approval: dict[str, Any]) -> None:
    resolved = path.resolve()
    approvals_dir = resolved.parent
    if approvals_dir.name != "approvals":
        raise ValueError("approval artifact path must be inside an approvals directory")
    if resolved.suffix != ".json":
        raise ValueError("approval artifact file must be a .json file")
    stem = resolved.stem.lower()
    if not _is_hex_sha256(stem):
        raise ValueError("approval artifact filename must be a sha256 hex digest")
    if any(part == ".." for part in path.parts):
        raise ValueError("approval artifact path must not contain traversal segments")

    approvals_dir.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(approval, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_approval_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return {}


def validate_approval_artifact(
    approval: dict[str, Any],
    contract: dict[str, Any],
    patch_draft: str,
) -> list[str]:
    issues: list[str] = []

    for key in REQUIRED_APPROVAL_KEYS:
        if key not in approval:
            issues.append(f"missing required approval key: {key}")

    status = str(approval.get("approval_status", ""))
    if status not in ALLOWED_APPROVAL_STATUSES:
        issues.append(f"invalid approval_status: {status}")

    expected_hash = build_contract_fingerprint(contract, patch_draft)
    current_hash = str(approval.get("contract_hash", ""))
    stale = bool(approval.get("stale", False))

    if current_hash != expected_hash:
        issues.append("approval artifact is stale")

    if status == "approved" and stale:
        issues.append("approved artifact must not be marked stale")

    if status == "approved" and current_hash != expected_hash:
        issues.append("approved artifact hash does not match current contract")

    return issues
